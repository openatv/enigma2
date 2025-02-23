#include <sys/klog.h>
#include <vector>
#include <csignal>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <execinfo.h>
#include <dlfcn.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/nconfig.h>
#include <lib/gdi/gmaindc.h>
#include <asm/ptrace.h>
#include <lib/base/modelinformation.h>

#include "version_info.h"

/************************************************/

/* Defined in bsod.cpp */
void retrieveLogBuffer(const char **p1, unsigned int *s1, const char **p2, unsigned int *s2);
void clearRingBuffer();

static const std::string getConfigString(const char* key, const char* defaultValue)
{
	std::string value = eConfigManager::getConfigValue(key);

	//we get at least the default value if python is still alive
	if (!value.empty())
		return value;

	return eSimpleConfig::getString(key, defaultValue);
}

/* get the kernel log aka dmesg */
static void getKlog(FILE* f)
{
	fprintf(f, "\n\ndmesg\n\n");

	ssize_t len = klogctl(10, NULL, 0); /* read ring buffer size */
	if (len == -1)
	{
		fprintf(f, "Error reading klog %d - %m\n", errno);
		return;
	}
	else if(len == 0)
	{
		return;
	}

	std::vector<char> buf(len, 0);

	len = klogctl(4, &buf[0], len); /* read and clear ring buffer */
	if (len == -1)
	{
		fprintf(f, "Error reading klog %d - %m\n", errno);
		return;
	}

	buf.resize(len);
	fprintf(f, "%s\n", &buf[0]);
}

static void stringFromFile(FILE* f, const char* context, const char* filename)
{
	std::ifstream in(filename);

	if (in.good()) {
		std::string line;
		std::getline(in, line);
		fprintf(f, "%s=%s\n", context, line.c_str());
		in.close();
	}
}

static void dumpFile(FILE* f, const char* filename)
{
	std::ifstream in(filename);
	if (in.good()) {
		do
		{
			std::string line;
			std::getline(in, line);
			fprintf(f, "%s\n", line.c_str());
		}
		while (in.good());
		in.close();
	}
}


static bool bsodhandled = false;
static bool bsodrestart =  true;
static int bsodcnt = 0;

int getBsodCounter()
{
	return bsodcnt;
}

void resetBsodCounter()
{
	bsodcnt = 0;
}

bool bsodRestart()
{
	return bsodrestart; //unused
}
void bsodFatal(const char *component)
{
	//handle python crashes	
	bool bsodpython = (eConfigManager::getConfigBoolValue("config.crash.bsodpython", false) && eConfigManager::getConfigBoolValue("config.crash.bsodpython_ready", false));
	//hide bs after x bs counts and no more write crash log	-> setting values 0-10 (always write the first and last crashlog)
	int bsodhide = eConfigManager::getConfigIntValue("config.crash.bsodhide", 5);
	//restart after x bs counts -> setting values 0-10 (0 = never restart)
	int bsodmax = eConfigManager::getConfigIntValue("config.crash.bsodmax", 5);
	//force restart after max crashes
	int bsodmaxmax = 100;

	bsodcnt++;
	if ((bsodmax && bsodcnt > bsodmax) || component || bsodcnt > bsodmaxmax)
		bsodpython = false;
	if (bsodpython && bsodcnt-1 && bsodcnt > bsodhide && (!bsodmax || bsodcnt < bsodmax) && bsodcnt < bsodmaxmax)
	{
		sleep(1);
		return;
	}
	bsodrestart = true;

	/* show no more than one bsod while shutting down/crashing */
	if (bsodhandled) {
		if (component) {
			sleep(1);
			raise(SIGKILL);
		}
		return;
	}
	bsodhandled = true;

	if (!component)
		component = "Enigma2";

	/* Retrieve current ringbuffer state */
	const char* logp1 = NULL;
	unsigned int logs1 = 0;
	const char* logp2 = NULL;
	unsigned int logs2 = 0;
	retrieveLogBuffer(&logp1, &logs1, &logp2, &logs2);
	/* We need a copy to clearRingBuffer */
	char logb1[logs1+1];
	char logb2[logs2+1];
	memcpy(logb1, logp1, logs1);
	memcpy(logb2, logp2, logs2);
	logp1 = logb1;
	logp2 = logb2;

	FILE *f;
	std::string crashlog_name;
	std::ostringstream os;
	std::ostringstream os_text;

	char dated[22];
	time_t now_time = time(0);
	struct tm loctime = {};
	localtime_r(&now_time, &loctime);
	strftime (dated, 21, "%Y%m%d-%H%M%S", &loctime);

	os << getConfigString("config.crash.debug_path", "/home/root/logs/");
	os << dated;
	os << "-enigma2-crash.log";
	crashlog_name = os.str();
	f = fopen(crashlog_name.c_str(), "wb");

	if (f == NULL)
	{
		/* No hardisk. If there is a crash log in /home/root, leave it
		 * alone because we may be in a crash loop and writing this file
		 * all night long may damage the flash. Also, usually the first
		 * crash log is the most interesting one. */
		crashlog_name = "/home/root/logs/enigma2_crash.log";
		if ((access(crashlog_name.c_str(), F_OK) == 0) ||
		    ((f = fopen(crashlog_name.c_str(), "wb")) == NULL))
		{
			/* Re-write the same file in /tmp/ because it's expected to
			 * be in RAM. So the first crash log will end up in /home
			 * and the last in /tmp */
			crashlog_name = "/tmp/enigma2_crash.log";
			f = fopen(crashlog_name.c_str(), "wb");
		}
	}

	if (f)
	{
		time_t t = time(0);
		struct tm tm = {};
		char tm_str[32];

		localtime_r(&t, &tm);
		strftime(tm_str, sizeof(tm_str), "%a %b %_d %T %Y", &tm);

		fprintf(f,
			"OpenATV Enigma2 crash log\n\n"
			"crashdate=%s\n"
			"compiledate=%s\n"
			"skin=%s\n"
			"sourcedate=%s\n"
			"branch=%s\n"
			"rev=%s\n"
			"component=%s\n\n",
			tm_str,
			__DATE__,
			getConfigString("config.skin.primary_skin", "Default Skin").c_str(),
			enigma2_date,
			enigma2_branch,
			E2REV,
			component);

		eModelInformation &modelinformation = eModelInformation::getInstance();

		const std::list<std::string> enigmainfovalues {
			"model",
			"machinebuild",
			"imageversion",
			"imagebuild"
		};

		for(std::list<std::string>::const_iterator i = enigmainfovalues.begin(); i != enigmainfovalues.end(); ++i)
		{
			fprintf(f, "%s=%s\n", i->c_str(), modelinformation.getValue(i->c_str()).c_str());
		}

		fprintf(f, "\n");
		stringFromFile(f, "kernelcmdline", "/proc/cmdline");
		fprintf(f, "\nnimsockets:\n");
		dumpFile(f, "/proc/bus/nim_sockets");

		/* dump the log ringbuffer */
		fprintf(f, "\n\n");
		if (logp1)
			fwrite(logp1, 1, logs1, f);
		if (logp2)
			fwrite(logp2, 1, logs2, f);

		/* dump the kernel log */
		getKlog(f);
		fsync(fileno(f));
		fclose(f);

		/* clear the ringbuffer */
		clearRingBuffer();
	}

	if (bsodpython && bsodcnt == 1 && !bsodhide) //write always the first crashlog
	{
		bsodrestart = false;
		bsodhandled = false;
		sleep(1);
		return;
	}
	ePtr<gMainDC> my_dc;
	gMainDC::getInstance(my_dc);

	gPainter p(my_dc);
	p.resetOffset();
	p.resetClip(eRect(ePoint(0, 0), my_dc->size()));
	p.setBackgroundColor(gRGB(0x27408B));
	p.setForegroundColor(gRGB(0xFFFFFF));
	int hd =  my_dc->size().width() == 1920;
	ePtr<gFont> font = new gFont("Regular", hd ? 30 : 20);
	p.setFont(font);
	p.clear();

	eRect usable_area = eRect(hd ? 30 : 100, hd ? 30 : 70, my_dc->size().width() - (hd ? 60 : 150), hd ? 150 : 100);

	os.str("");
	os.clear();
	os_text.clear();

	if (!bsodpython)
	{
		os_text << "Your receiver encountered a software problem, and needs to be restarted.\n"
			"Please send the logfile " << crashlog_name << " to the OpenATV forum (www.opena.tv).\n"
			"Your receiver will restart in 10 seconds.\n"
			"Component: " << component;
		os << os_text.str();
	}
	else
	{
		std::string txt;
		if (!bsodmax && bsodcnt < bsodmaxmax)
			txt = "after maximum " + std::to_string(bsodmaxmax) + " crashes";
		else if (bsodmax - bsodcnt > 0)
			txt = "if it happens " + std::to_string(bsodmax - bsodcnt) + " more time(s)";
		else
			txt = "if it happens one more time";

		os_text << "Your receiver encountered a Python software problem. There have been " << bsodcnt << " crashes so far.\n"
			"Please send the logfile " << crashlog_name << " to the OpenATV forum (www.opena.tv).\n"
			"Your receiver will restart " << txt << ".\n"
			"Component: " << component;
		os << os_text.str();
	}

	p.renderText(usable_area, os.str().c_str(), gPainter::RT_WRAP|gPainter::RT_HALIGN_LEFT);

	std::string logtail;
	int lines = 20;
	
	if (logp2)
	{
		unsigned int size = logs2;
		while (size) {
			const char* r = (const char*)memrchr(logp2, '\n', size);
			if (r) {
				size = r - logp2;
				--lines;
				if (!lines) {
					logtail = std::string(r, logs2 - size);
					break;
				} 
			}
			else {
				logtail = std::string(logp2, logs2);
				break;
			}
		}
	}

	if (lines && logp1)
	{
		unsigned int size = logs1;
		while (size) {
			const char* r = (const char*)memrchr(logp1, '\n', size);
			if (r) {
				--lines;
				size = r - logp1;
				if (!lines) {
					logtail += std::string(r, logs1 - size);
					break;
				} 
			}
			else {
				logtail += std::string(logp1, logs1);
				break;
			}
		}
	}

	if (!logtail.empty())
	{
		font = new gFont("Regular", hd ? 21 : 14);
		p.setFont(font);
		usable_area = eRect(hd ? 30 : 100, hd ? 180 : 170, my_dc->size().width() - (hd ? 60 : 180), my_dc->size().height() - (hd ? 30 : 20));
		p.renderText(usable_area, logtail, gPainter::RT_HALIGN_LEFT);
	}
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

	if (bsodpython)
	{
		bsodrestart = false;
		bsodhandled = false;
		p.setBackgroundColor(gRGB(0,0,0,0xFF));
		p.clear();
		return;
	}
	if (component) {
		/*
		 *  We need to use a signal that generate core dump.
		 */
		if (eConfigManager::getConfigBoolValue("config.crash.coredump", false)) raise(SIGTRAP);
		raise(SIGKILL);
	}
}

void oops(const mcontext_t &context)
{
#if defined(__MIPSEL__)
	eLog(lvlFatal, "PC: %08lx", (unsigned long)context.pc);
	int i;
	for (i=0; i<32; i += 4)
	{
		eLog(lvlFatal, "    %08x %08x %08x %08x",
			(int)context.gregs[i+0], (int)context.gregs[i+1],
			(int)context.gregs[i+2], (int)context.gregs[i+3]);
	}
#elif defined(__arm__)
	eLog(lvlFatal, "PC: %08lx", (unsigned long)context.arm_pc);
	eLog(lvlFatal, "Fault Address: %08lx", (unsigned long)context.fault_address);
	eLog(lvlFatal, "Error Code:: %lu", (unsigned long)context.error_code);
#else
	eLog(lvlFatal, "FIXME: no oops support!");
#endif
}

/* Use own backtrace print procedure because backtrace_symbols_fd
 * only writes to files. backtrace_symbols cannot be used because
 * it's not async-signal-safe and so must not be used in signal
 * handlers.
 */
void print_backtrace()
{
	void *array[15];
	size_t size;
	size_t cnt;

	size = backtrace(array, 15);
	eLog(lvlFatal, "Backtrace:");
	for (cnt = 1; cnt < size; ++cnt)
	{
		Dl_info info;

		if (dladdr(array[cnt], &info)
			&& info.dli_fname != NULL && info.dli_fname[0] != '\0')
		{
			eLog(lvlFatal, "%s(%s) [0x%lX]", info.dli_fname, info.dli_sname != NULL ? info.dli_sname : "n/a", (unsigned long int) array[cnt]);
		}
	}
}

void handleFatalSignal(int signum, siginfo_t *si, void *ctx)
{
	ucontext_t *uc = (ucontext_t*)ctx;
	oops(uc->uc_mcontext);
	print_backtrace();
	eLog(lvlFatal, "-------FATAL SIGNAL");
	bsodFatal("enigma2, signal");
}

void bsodCatchSignals()
{
	struct sigaction act = {};
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
