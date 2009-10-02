#include <string.h>
#include <signal.h>
#include <asm/ptrace.h>

#include <lib/base/eerror.h>
#include <lib/base/smartptr.h>
#include <lib/base/nconfig.h>
#include <lib/gdi/grc.h>
#include <lib/gdi/gfbdc.h>
#ifdef WITH_SDL
#include <lib/gdi/sdl.h>
#endif

#include "version.h"

/************************************************/

#define CRASH_EMAILADDR "crashlog@dream-multimedia-tv.de"
#define STDBUFFER_SIZE 512
#define RINGBUFFER_SIZE 16384
static char ringbuffer[RINGBUFFER_SIZE];
static int ringbuffer_head;

static void addToLogbuffer(const char *data, int len)
{
	while (len)
	{
		int remaining = RINGBUFFER_SIZE - ringbuffer_head;
	
		if (remaining > len)
			remaining = len;
	
		memcpy(ringbuffer + ringbuffer_head, data, remaining);
		len -= remaining;
		data += remaining;
		ringbuffer_head += remaining;
		if (ringbuffer_head >= RINGBUFFER_SIZE)
			ringbuffer_head = 0;
	}
}

static std::string getLogBuffer()
{
	int begin = ringbuffer_head;
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
	{
		return std::string(ringbuffer + begin, RINGBUFFER_SIZE - begin) + std::string(ringbuffer, ringbuffer_head);
	}
}

static void addToLogbuffer(int level, const std::string &log)
{
	addToLogbuffer(log.c_str(), log.size());
}

static std::string getConfigFileValue(const char *entry)
{
	std::string configfile = "/etc/enigma2/settings";
	std::string configvalue;
	if (entry)
	{
		ePythonConfigQuery::getConfigValue(entry, configvalue);
		if (configvalue != "") //we get at least the default value if python is still alive
		{
			return configvalue;
		}
		else // get Value from enigma2 settings file
		{
			FILE *f = fopen(configfile.c_str(), "r");
			if (!f)
			{
				return "Error";
			}
			while (1)
			{
				char line[1024];
				if (!fgets(line, 1024, f))
					break;
				if (!strncmp(line, entry, strlen(entry) ))
				{
					if (strlen(line) && line[strlen(line)-1] == '\r')
						line[strlen(line)-1] = 0;
					if (strlen(line) && line[strlen(line)-1] == '\n')
						line[strlen(line)-1] = 0;
					std::string tmp = line;
					int posEqual = tmp.find("=", 0);
					configvalue = tmp.substr(posEqual+1);
				}
			}
			fclose(f);
			return configvalue;
		}
	}
}

static std::string getFileContent(const char *file)
{
	std::string filecontent;

	if (file)
	{
		FILE *f = fopen(file, "r");
		if (!f)
		{
			return "Error";
		}
		while (1)
		{
			char line[1024];
			if (!fgets(line, 1024, f))
				break;
			filecontent += line;
		}
		fclose(f);
	}
	return filecontent;
}

static std::string execCommand(char* cmd) {
	FILE* pipe = popen(cmd, "r");
	if (!pipe)
		return "Error";
	char buffer[STDBUFFER_SIZE];
	std::string result = "";
	while(!feof(pipe))
	{
		if(!fgets(buffer,STDBUFFER_SIZE, pipe))
			break;
		result += buffer;
	}
	pclose(pipe);
	return result;
}

extern std::string execCommand();
extern std::string getConfigFileValue();
extern std::string getFileContent();
extern std::string getLogBuffer();

#define INFOFILE "/maintainer.info"

void bsodFatal(const char *component)
{
	char logfile[128];
	sprintf(logfile, "/media/hdd/enigma2_crash_%u.log", (unsigned int)time(0));
	FILE *f = fopen(logfile, "wb");
	
	std::string lines = getLogBuffer();
	
		/* find python-tracebacks, and extract "  File "-strings */
	size_t start = 0;
	
	char crash_emailaddr[256] = CRASH_EMAILADDR;
	char crash_component[256] = "enigma2";

	if (component)
		snprintf(crash_component, 256, component);
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
			if (end - start >= (256 - strlen(INFOFILE)))
				continue;
			char filename[256];
			snprintf(filename, 256, "%s%s", lines.substr(start, end - start).c_str(), INFOFILE);
			FILE *cf = fopen(filename, "r");
			if (cf)
			{
				fgets(crash_emailaddr, sizeof crash_emailaddr, cf);
				if (*crash_emailaddr && crash_emailaddr[strlen(crash_emailaddr)-1] == '\n')
					crash_emailaddr[strlen(crash_emailaddr)-1] = 0;

				fgets(crash_component, sizeof crash_component, cf);
				if (*crash_component && crash_component[strlen(crash_component)-1] == '\n')
					crash_component[strlen(crash_component)-1] = 0;
				fclose(cf);
			}
		}
	}

	if (f)
	{
		time_t t = time(0);
		char crashtime[STDBUFFER_SIZE];
		sprintf(crashtime, "%s",ctime(&t));
		if (strlen(crashtime) && crashtime[strlen(crashtime)-1] == '\n')
				crashtime[strlen(crashtime)-1] = 0;
		fprintf(f, "<?xml version=\"1.0\" encoding=\"iso-8859-1\" ?>\n<opendreambox>\n");
		fprintf(f, "\t<enigma2>\n");
		fprintf(f, "\t\t<crashdate>%s</crashdate>\n", crashtime);
#ifdef ENIGMA2_CHECKOUT_TAG
		fprintf(f, "\t\t<checkouttag>" ENIGMA2_CHECKOUT_TAG "</checkouttag>\n");
#else
		fprintf(f, "\t\t<compiledate>" __DATE__ "</compiledate>\n");
#endif
#ifdef ENIGMA2_CHECKOUT_ROOT
		fprintf(f, "\t\t<checkoutroot>" ENIGMA2_CHECKOUT_ROOT "</checkoutroot>\n");
#endif
		fprintf(f, "\t\t<contactemail>%s</contactemail>\n", crash_emailaddr);
		fprintf(f, "\t\t<!-- Please email this crashlog to above address -->\n");
		fprintf(f, "\t</enigma2>\n");

		fprintf(f, "\t<image>\n");
		std::string model = getFileContent("/proc/stb/info/model");
		if (model != "Error")
		{
			char modelname[STDBUFFER_SIZE];
			sprintf(modelname, "%s",model.c_str());
			if (strlen(modelname) && modelname[strlen(modelname)-1] == '\n')
				modelname[strlen(modelname)-1] = 0;
			fprintf(f, "\t\t<dreamboxmodel>%s</dreamboxmodel>\n", modelname);
		}
		std::string kernel = getFileContent("/proc/cmdline");
		if (kernel != "Error")
		{
			char kernelcmd[STDBUFFER_SIZE];
			sprintf(kernelcmd, "%s",kernel.c_str());
			if (strlen(kernelcmd) && kernelcmd[strlen(kernelcmd)-1] == '\n')
				kernelcmd[strlen(kernelcmd)-1] = 0;
			fprintf(f, "\t\t<kernelcmdline>%s</kernelcmdline>\n", kernelcmd);
		}
		std::string sendAnonCrashlog = getConfigFileValue("config.plugins.crashlogautosubmit.sendAnonCrashlog");
		if (sendAnonCrashlog == "False" || sendAnonCrashlog == "false") // defaults to true... default anonymized crashlogs
		{
			std::string ca = getFileContent("/proc/stb/info/ca");
			if (ca != "Error")
			{
				char dreamboxca[STDBUFFER_SIZE];
				sprintf(dreamboxca, "%s",ca.c_str());
				if (strlen(dreamboxca) && dreamboxca[strlen(dreamboxca)-1] == '\n')
					dreamboxca[strlen(dreamboxca)-1] = 0;
				fprintf(f, "\t\t<dreamboxca>\n\t\t<![CDATA[\n%s\n\t\t]]>\n\t\t</dreamboxca>\n", dreamboxca);
			}
			std::string settings = getFileContent("/etc/enigma2/settings");
			if (settings != "Error")
			{
				fprintf(f, "\t\t<enigma2settings>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</enigma2settings>\n", settings.c_str());
			}
		}
		std::string addNetwork = getConfigFileValue("config.plugins.crashlogautosubmit.addNetwork");
		if (addNetwork == "True" || addNetwork == "true")
		{
			std::string nwinterfaces = getFileContent("/etc/network/interfaces");
			if (nwinterfaces != "Error")
			{
				fprintf(f, "\t\t<networkinterfaces>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</networkinterfaces>\n", nwinterfaces.c_str());
			}
			std::string dns = getFileContent("/etc/resolv.conf");
			if (dns != "Error")
			{
				fprintf(f, "\t\t<dns>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</dns>\n", dns.c_str());
			}
			std::string defaultgw = getFileContent("/etc/default_gw");
			if (defaultgw != "Error")
			{
				char gateway[STDBUFFER_SIZE];
				sprintf(gateway, "%s",defaultgw.c_str());
				if (strlen(gateway) && gateway[strlen(gateway)-1] == '\n')
					gateway[strlen(gateway)-1] = 0;
				fprintf(f, "\t\t<defaultgateway>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</defaultgateway>\n", gateway);
			}
		}
		std::string addWlan = getConfigFileValue("config.plugins.crashlogautosubmit.addWlan");
		if (addWlan == "True" || addWlan == "true")
		{
			std::string wpasupplicant = getFileContent("/etc/wpa_supplicant.conf");
			if (wpasupplicant != "Error")
			{
				fprintf(f, "\t\t<wpasupplicant>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</wpasupplicant>\n", wpasupplicant.c_str());
			}
		}
		std::string imageversion = getFileContent("/etc/image-version");
		if (imageversion != "Error")
		{
			fprintf(f, "\t\t<imageversion>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</imageversion>\n", imageversion.c_str());
		}
		std::string imageissue = getFileContent("/etc/issue.net");
		if (imageissue != "Error")
		{
			fprintf(f, "\t\t<imageissue>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</imageissue>\n", imageissue.c_str());
		}
		fprintf(f, "\t</image>\n");

		fprintf(f, "\t<software>\n");
		std::string installedplugins = execCommand("ipkg list_installed | grep enigma2");
		fprintf(f, "\t\t<enigma2software>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</enigma2software>\n", installedplugins.c_str());
		std::string dreambox = execCommand("ipkg list_installed | grep dream");
		fprintf(f, "\t\t<dreamboxsoftware>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</dreamboxsoftware>\n", dreambox.c_str());
		std::string gstreamer = execCommand("ipkg list_installed | grep gst");
		fprintf(f, "\t\t<gstreamersoftware>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</gstreamersoftware>\n", gstreamer.c_str());
		fprintf(f, "\t</software>\n");

		fprintf(f, "\t<crashlogs>\n");
		std::string buffer = getLogBuffer();
		fprintf(f, "\t\t<enigma2crashlog>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</enigma2crashlog>\n", buffer.c_str());
		std::string pythonmd5 = execCommand("find /usr/lib/enigma2/python/ -name \"*.py\" | xargs md5sum");
		fprintf(f, "\t\t<pythonMD5sum>\n\t\t<![CDATA[\n%s\t\t]]>\n\t\t</pythonMD5sum>\n", pythonmd5.c_str());
		fprintf(f, "\t</crashlogs>\n");

		fprintf(f, "\n</opendreambox>\n");
		fclose(f);
		
	}
	
#ifdef WITH_SDL
	ePtr<gSDLDC> my_dc;
	gSDLDC::getInstance(my_dc);
#else
	ePtr<gFBDC> my_dc;
	gFBDC::getInstance(my_dc);
#endif
	
	{
		gPainter p(my_dc);
		p.resetOffset();
		p.resetClip(eRect(ePoint(0, 0), my_dc->size()));
#ifdef ENIGMA2_CHECKOUT_TAG
		if (ENIGMA2_CHECKOUT_TAG[0] == 'T') /* tagged checkout (release) */
			p.setBackgroundColor(gRGB(0x0000C0));
		else if (ENIGMA2_CHECKOUT_TAG[0] == 'D') /* dated checkout (daily experimental build) */
		{
			srand(time(0));
			int r = rand();
			unsigned int col = 0;
			if (r & 1)
				col |= 0x800000;
			if (r & 2)
				col |= 0x008000;
			if (r & 4)
				col |= 0x0000c0;
			p.setBackgroundColor(gRGB(col));
		}
#else
			p.setBackgroundColor(gRGB(0x008000));
#endif

		p.setForegroundColor(gRGB(0xFFFFFF));
	
		ePtr<gFont> font = new gFont("Regular", 20);
		p.setFont(font);
		p.clear();
	
		eRect usable_area = eRect(100, 70, my_dc->size().width() - 150, 100);
		
		char text[512];
		snprintf(text, 512, "We are really sorry. Your Dreambox encountered "
			"a software problem, and needs to be restarted. "
			"Please send the logfile created in /hdd/ to %s.\n"
			"Your Dreambox restarts in 10 seconds!\n"
			"Component: %s",
			crash_emailaddr, crash_component);
	
		p.renderText(usable_area, text, gPainter::RT_WRAP|gPainter::RT_HALIGN_LEFT);
	
		usable_area = eRect(100, 170, my_dc->size().width() - 180, my_dc->size().height() - 20);
	
		int i;
	
		size_t start = std::string::npos + 1;
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
	}

	raise(SIGKILL);
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
#else
#warning "no oops support!"
#define NO_OOPS_SUPPORT
#endif

void handleFatalSignal(int signum, siginfo_t *si, void *ctx)
{
	ucontext_t *uc = (ucontext_t*)ctx;

#ifndef NO_OOPS_SUPPORT
	oops(uc->uc_mcontext, signum == SIGSEGV || signum == SIGABRT);
#endif
	eDebug("-------");
	bsodFatal("enigma2, signal");
}

void bsodCatchSignals()
{
	struct sigaction act;
	act.sa_handler = SIG_DFL;
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
