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

#define CRASH_EMAILADDR "forum at www.opena.tv"
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
	std::string value = eConfigManager::getConfigValue(key.c_str());

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

	FILE *f;
	const char* crashlog_name;
	std::ostringstream os;
	std::ostringstream os_text;
	os << getConfigString("config.crash.debug_path", "/home/root/logs/");
	os << "enigma2_crash_";
	os << time(0);
	os << ".log";
	crashlog_name = os.str().c_str();
	f = fopen(crashlog_name, "wb");

	if (f == NULL)
	{
		/* No hardisk. If there is a crash log in /home/root, leave it
		 * alone because we may be in a crash loop and writing this file
		 * all night long may damage the flash. Also, usually the first
		 * crash log is the most interesting one. */
		crashlog_name = "/home/root/logs/enigma2_crash.log";
		if ((access(crashlog_name, F_OK) == 0) ||
		    ((f = fopen(crashlog_name, "wb")) == NULL))
		{
			/* Re-write the same file in /tmp/ because it's expected to
			 * be in RAM. So the first crash log will end up in /home
			 * and the last in /tmp */
			crashlog_name = "/tmp/enigma2_crash.log";
			f = fopen(crashlog_name, "wb");
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

		xml.open("openATV");

		xml.open("enigma2");
		xml.string("crashdate", tm_str);
		xml.string("compiledate", __DATE__);
		xml.string("contactemail", crash_emailaddr);
		xml.comment("Please email this crashlog to above address");

		xml.string("skin", getConfigString("config.skin.primary_skin", "Default Skin"));
		xml.string("sourcedate", enigma2_date);
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
		xml.cDataFromFile("imageversion", "/etc/image-version");
		xml.cDataFromFile("imageissue", "/etc/issue.net");
		xml.close();

		if (detailedCrash)
		{
			xml.open("software");
			xml.cDataFromCmd("enigma2software", "opkg list-installed 'enigma2*'");
			if(access("/proc/stb/info/boxtype", F_OK) != -1) {
				xml.cDataFromCmd("xtrendsoftware", "opkg list-installed 'et*'");
			}
			else if (access("/proc/stb/info/vumodel", F_OK) != -1) {
				xml.cDataFromCmd("vuplussoftware", "opkg list-installed 'vuplus*'");
			}
			else if (access("/proc/stb/info/model", F_OK) != -1) {
				xml.cDataFromCmd("dreamboxsoftware", "opkg list-installed 'dream*'");
			}
			else if (access("/proc/stb/info/azmodel", F_OK) != -1) {
				xml.cDataFromCmd("azboxboxsoftware", "opkg list-installed 'az*'");
			}
			else if (access("/proc/stb/info/gbmodel", F_OK) != -1) {
				xml.cDataFromCmd("gigabluesoftware", "opkg list-installed 'gb*'");
			}
			else if (access("/proc/stb/info/hwmodel", F_OK) != -1) {
				xml.cDataFromCmd("technomatesoftware", "opkg list-installed 'tm*'");
			}
			else if (access("/proc/stb/info/boxtype", F_OK) != -1) {
				xml.cDataFromCmd("ventonsoftware", "opkg list-installed 'ini*'");
			}
			else if (access("/proc/stb/info/boxtype", F_OK) != -1) {
				xml.cDataFromCmd("maxdigitalsoftware", "opkg list-installed 'xp*'");
			}			
			else if (access("/proc/stb/info/boxtype", F_OK) != -1) {
				xml.cDataFromCmd("odinsoftware", "opkg list-installed 'odin*'");
			}		
			else if (access("/proc/stb/info/boxtype", F_OK) != -1) {
				xml.cDataFromCmd("eboxsoftware", "opkg list-installed 'ebox*'");
			}	
			else if (access("/proc/stb/info/boxtype", F_OK) != -1) {
				xml.cDataFromCmd("medialinksoftware", "opkg list-installed 'ixuss*'");
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
	p.setBackgroundColor(gRGB(0x27408B));
	p.setForegroundColor(gRGB(0xFFFFFF));

	ePtr<gFont> font = new gFont("Regular", 20);
	p.setFont(font);
	p.clear();

	eRect usable_area = eRect(100, 70, my_dc->size().width() - 150, 100);

	os.str("");
	os.clear();
	os_text.clear();

	os_text << "We are really sorry. Your receiver encountered "
		"a software problem, and needs to be restarted.\n"
		"Please send the logfile " << crashlog_name << " to " << crash_emailaddr << ".\n"
		"Your receiver restarts in 10 seconds!\n"
		"Component: " << crash_component;
	
	os << getConfigString("config.crash.debug_text", os_text.str());

	p.renderText(usable_area, os.str().c_str(), gPainter::RT_WRAP|gPainter::RT_HALIGN_LEFT);

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
void oops(const mcontext_t &context)
{
	eDebug("PC: %08lx", (unsigned long)context.pc);
	int i;
	for (i=0; i<32; i += 4)
	{
		eDebug("%08x %08x %08x %08x",
			(int)context.gregs[i+0], (int)context.gregs[i+1],
			(int)context.gregs[i+2], (int)context.gregs[i+3]);
	}
}
#endif

void handleFatalSignal(int signum, siginfo_t *si, void *ctx)
{
#ifndef NO_OOPS_SUPPORT
	ucontext_t *uc = (ucontext_t*)ctx;
	oops(uc->uc_mcontext);
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
