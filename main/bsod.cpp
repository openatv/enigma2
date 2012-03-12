#include <csignal>
#include <fstream>
#include <sstream>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/nconfig.h>
#include <lib/gdi/gmaindc.h>

#if defined(__MIPSEL__)
#include <asm/ptrace.h>
#else
#warning "no oops support!"
#define NO_OOPS_SUPPORT
#endif

#include "xmlgenerator.h"
#include "version_info.h"

/************************************************/

#define CRASH_EMAILADDR "forum at www.openpli.org"
#define INFOFILE "/maintainer.info"

#define RINGBUFFER_SIZE 16384
static char ringbuffer[RINGBUFFER_SIZE];
static unsigned int ringbuffer_head;

static void addToLogbuffer(const char *data, unsigned int len)
{
	while (len)
	{
		unsigned int remaining = RINGBUFFER_SIZE - ringbuffer_head;

		if (remaining > len)
			remaining = len;

		memcpy(ringbuffer + ringbuffer_head, data, remaining);
		len -= remaining;
		data += remaining;
		ringbuffer_head += remaining;
		ASSERT(ringbuffer_head <= RINGBUFFER_SIZE);
		if (ringbuffer_head == RINGBUFFER_SIZE)
			ringbuffer_head = 0;
	}
}

static const std::string getLogBuffer()
{
	unsigned int begin = ringbuffer_head;
	while (ringbuffer[begin] == 0)
	{
		++begin;
		if (begin == RINGBUFFER_SIZE)
			begin = 0;
		if (begin == ringbuffer_head)
			return "";
	}

	if (begin < ringbuffer_head)
		return std::string(ringbuffer + begin, ringbuffer_head - begin);
	else
		return std::string(ringbuffer + begin, RINGBUFFER_SIZE - begin) + std::string(ringbuffer, ringbuffer_head);
}

static void addToLogbuffer(int level, const std::string &log)
{
	addToLogbuffer(log.c_str(), log.size());
}

static const std::string getConfigString(const std::string &key, const std::string &defaultValue)
{
	std::string value;

	ePythonConfigQuery::getConfigValue(key.c_str(), value);
	//we get at least the default value if python is still alive
	if (!value.empty())
		return value;

	value = defaultValue;

	// get value from enigma2 settings file
	std::ifstream in(eEnv::resolve("${sysconfdir}/enigma2/settings").c_str());
	if (in.good()) {
		do {
			std::string line;
			std::getline(in, line);
			size_t size = key.size();
			if (!key.compare(0, size, line) && line[size] == '=') {
				value = line.substr(size + 1);
				break;
			}
		} while (in.good());
		in.close();
	}

	return value;
}

static bool getConfigBool(const std::string &key, bool defaultValue)
{
	std::string value = getConfigString(key, defaultValue ? "true" : "false");
	const char *cvalue = value.c_str();

	if (!strcasecmp(cvalue, "true"))
		return true;
	if (!strcasecmp(cvalue, "false"))
		return false;

	return defaultValue;
}

static bool bsodhandled = false;

void bsodFatal(const char *component)
{
	/* show no more than one bsod while shutting down/crashing */
	if (bsodhandled) return;
	bsodhandled = true;

	std::ostringstream os;
	os << "/media/hdd/enigma2_crash_";
	os << time(0);
	os << ".log";

	FILE *f = fopen(os.str().c_str(), "wb");
	
	std::string lines = getLogBuffer();
	
		/* find python-tracebacks, and extract "  File "-strings */
	size_t start = 0;
	
	std::string crash_emailaddr = CRASH_EMAILADDR;
	std::string crash_component = "enigma2";

	if (component)
		crash_component = component;
	else
	{
		while ((start = lines.find("\n  File \"", start)) != std::string::npos)
		{
			start += 9;
			size_t end = lines.find("\"", start);
			if (end == std::string::npos)
				break;
			end = lines.rfind("/", end);
				/* skip a potential prefix to the path */
			unsigned int path_prefix = lines.find("/usr/", start);
			if (path_prefix != std::string::npos && path_prefix < end)
				start = path_prefix;

			if (end == std::string::npos)
				break;

			std::string filename(lines.substr(start, end - start) + INFOFILE);
			std::ifstream in(filename.c_str());
			if (in.good()) {
				std::getline(in, crash_emailaddr) && std::getline(in, crash_component);
				in.close();
			}
		}
	}

	if (f)
	{
		time_t t = time(0);
		struct tm tm;
		char tm_str[32];

		bool detailedCrash = getConfigBool("config.crash.details", true);

		localtime_r(&t, &tm);
		strftime(tm_str, sizeof(tm_str), "%a %b %_d %T %Y", &tm);

		XmlGenerator xml(f);

		xml.open("openpli");

		xml.open("enigma2");
		xml.string("crashdate", tm_str);
		xml.string("compiledate", __DATE__);
		xml.string("contactemail", crash_emailaddr);
		xml.comment("Please email this crashlog to above address");

		xml.string("skin", getConfigString("config.skin.primary_skin", "Default Skin"));
		xml.string("sourcedate", enigma2_date);
		xml.string("branch", enigma2_branch);
		xml.string("rev", enigma2_rev);
		xml.string("version", PACKAGE_VERSION);
		xml.close();

		xml.open("image");
		if(access("/proc/stb/info/boxtype", F_OK) != -1) {
			xml.stringFromFile("stbmodel", "/proc/stb/info/boxtype");
		}
		else if (access("/proc/stb/info/vumodel", F_OK) != -1) {
			xml.stringFromFile("stbmodel", "/proc/stb/info/vumodel");
		}
		else if (access("/proc/stb/info/model", F_OK) != -1) {
			xml.stringFromFile("stbmodel", "/proc/stb/info/model");
		}
		xml.cDataFromCmd("kernelversion", "uname -a");
		xml.stringFromFile("kernelcmdline", "/proc/cmdline");
		xml.stringFromFile("nimsockets", "/proc/bus/nim_sockets");
		if (!getConfigBool("config.plugins.crashlogautosubmit.sendAnonCrashlog", true)) {
			xml.cDataFromFile("stbca", "/proc/stb/info/ca");
			xml.cDataFromFile("enigma2settings", eEnv::resolve("${sysconfdir}/enigma2/settings"), ".password=");
		}
		if (getConfigBool("config.plugins.crashlogautosubmit.addNetwork", false)) {
			xml.cDataFromFile("networkinterfaces", "/etc/network/interfaces");
			xml.cDataFromFile("dns", "/etc/resolv.conf");
			xml.cDataFromFile("defaultgateway", "/etc/default_gw");
		}
		if (getConfigBool("config.plugins.crashlogautosubmit.addWlan", false))
			xml.cDataFromFile("wpasupplicant", "/etc/wpa_supplicant.conf");
		xml.cDataFromFile("imageversion", "/etc/image-version");
		xml.cDataFromFile("imageissue", "/etc/issue.net");
		xml.close();

		if (detailedCrash)
		{
			xml.open("software");
			xml.cDataFromCmd("enigma2software", "opkg list-installed 'enigma2*'");
			if(access("/proc/stb/info/boxtype", F_OK) != -1) {
				xml.cDataFromCmd("xtrendsoftware", "opkg list-installed 'et-*'");
			}
			else if (access("/proc/stb/info/vumodel", F_OK) != -1) {
				xml.cDataFromCmd("vuplussoftware", "opkg list-installed 'vuplus*'");
			}
			else if (access("/proc/stb/info/model", F_OK) != -1) {
				xml.cDataFromCmd("dreamboxsoftware", "opkg list-installed 'dream*'");
			}
			xml.cDataFromCmd("gstreamersoftware", "opkg list-installed 'gst*'");
			xml.close();
		}

		xml.open("crashlogs");
		xml.cDataFromString("enigma2crashlog", getLogBuffer());
		xml.close();

		xml.close();

		fclose(f);
	}

	ePtr<gMainDC> my_dc;
	gMainDC::getInstance(my_dc);
	
	gPainter p(my_dc);
	p.resetOffset();
	p.resetClip(eRect(ePoint(0, 0), my_dc->size()));
	p.setBackgroundColor(gRGB(0x008000));
	p.setForegroundColor(gRGB(0xFFFFFF));

	ePtr<gFont> font = new gFont("Regular", 20);
	p.setFont(font);
	p.clear();

	eRect usable_area = eRect(100, 70, my_dc->size().width() - 150, 100);
	
	std::string text("We are really sorry. Your STB encountered "
		"a software problem, and needs to be restarted. "
		"Please send the logfile created in /hdd/ to " + crash_emailaddr + ".\n"
		"Your STB restarts in 10 seconds!\n"
		"Component: " + crash_component);

	p.renderText(usable_area, text.c_str(), gPainter::RT_WRAP|gPainter::RT_HALIGN_LEFT);

	usable_area = eRect(100, 170, my_dc->size().width() - 180, my_dc->size().height() - 20);

	int i;

	start = std::string::npos + 1;
	for (i=0; i<20; ++i)
	{
		start = lines.rfind('\n', start - 1);
		if (start == std::string::npos)
		{
			start = 0;
			break;
		}
	}

	font = new gFont("Regular", 14);
	p.setFont(font);

	p.renderText(usable_area, 
		lines.substr(start), gPainter::RT_HALIGN_LEFT);
	sleep(10);

	/*
	 * When 'component' is NULL, we are called because of a python exception.
	 * In that case, we'd prefer to to a clean shutdown of the C++ objects,
	 * and this should be safe, because the crash did not occur in the
	 * C++ part.
	 * However, when we got here for some other reason, a segfault probably,
	 * we prefer to stop immediately instead of performing a clean shutdown.
	 * We'd risk destroying things with every additional instruction we're
	 * executing here.
	 */
	if (component) raise(SIGKILL);
}

#if defined(__MIPSEL__)
void oops(const mcontext_t &context, int dumpcode)
{
	eDebug("PC: %08lx", (unsigned long)context.pc);
	int i;
	for (i=0; i<32; ++i)
	{
		eDebugNoNewLine(" %08x", (int)context.gregs[i]);
		if ((i&3) == 3)
			eDebug("");
	}
		/* this is temporary debug stuff. */
	if (dumpcode && ((unsigned long)context.pc) > 0x10000) /* not a zero pointer */
	{
		eDebug("As a final action, i will try to dump a bit of code.");
		eDebug("I just hope that this won't crash.");
		int i;
		eDebugNoNewLine("%08lx:", (unsigned long)context.pc);
		for (i=0; i<0x20; ++i)
			eDebugNoNewLine(" %02x", ((unsigned char*)context.pc)[i]);
		eDebug(" (end)");
	}
}
#endif

void handleFatalSignal(int signum, siginfo_t *si, void *ctx)
{
#ifndef NO_OOPS_SUPPORT
	ucontext_t *uc = (ucontext_t*)ctx;

	oops(uc->uc_mcontext, signum == SIGSEGV || signum == SIGABRT);
#endif
	eDebug("-------");
	bsodFatal("enigma2, signal");
}

void bsodCatchSignals()
{
	struct sigaction act;
	act.sa_sigaction = handleFatalSignal;
	act.sa_flags = SA_RESTART | SA_SIGINFO;
	if (sigemptyset(&act.sa_mask) == -1)
		perror("sigemptyset");
	
		/* start handling segfaults etc. */
	sigaction(SIGSEGV, &act, 0);
	sigaction(SIGILL, &act, 0);
	sigaction(SIGBUS, &act, 0);
	sigaction(SIGABRT, &act, 0);
}

void bsodLogInit()
{
	logOutput.connect(addToLogbuffer);
}
