#include <string.h>
#include <signal.h>
#include <asm/ptrace.h>

#include <lib/base/eerror.h>
#include <lib/base/smartptr.h>
#include <lib/gdi/grc.h>
#include <lib/gdi/gfbdc.h>
#ifdef WITH_SDL
#include <lib/gdi/sdl.h>
#endif

#include "version.h"

/************************************************/

#define CRASH_EMAILADDR "crashlog@dream-multimedia-tv.de"

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


extern std::string getLogBuffer();

void bsodFatal()
{
	char logfile[128];
	sprintf(logfile, "/media/hdd/enigma2_crash_%u.log", (unsigned int)time(0));
	FILE *f = fopen(logfile, "wb");
	
	std::string lines = getLogBuffer();

	if (f)
	{
		time_t t = time(0);
		fprintf(f, "enigma2 crashed on %s", ctime(&t));
#ifdef ENIGMA2_CHECKOUT_TAG
		fprintf(f, "enigma2 CVS TAG: " ENIGMA2_CHECKOUT_TAG "\n");
#else
		fprintf(f, "enigma2 compiled on " __DATE__ "\n");
#endif
#ifdef ENIGMA2_CHECKOUT_ROOT
		fprintf(f, "enigma2 checked out from " ENIGMA2_CHECKOUT_ROOT "\n");
#endif
		fprintf(f, "please email this file to " CRASH_EMAILADDR "\n");
		std::string buffer = getLogBuffer();
		fwrite(buffer.c_str(), buffer.size(), 1, f);
		fclose(f);
		
		char cmd[256];
		sprintf(cmd, "find /usr/lib/enigma2/python/ -name \"*.py\" | xargs md5sum >> %s", logfile);
		system(cmd);
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
	
		p.renderText(usable_area, 
			"We are really sorry. Something happened "
			"which should not have happened, and "
			"resulted in a crash. If you want to help "
			"us in improving this situation, please send "
			"the logfile created in /hdd/ to " CRASH_EMAILADDR "."
			"Your receiver restarts in 10 seconds !", gPainter::RT_WRAP|gPainter::RT_HALIGN_LEFT);
	
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
	eDebug("PC: %08lx, vaddr: %08lx", (unsigned long)context.pc, (unsigned long)context.badvaddr);
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
	eDebug("KILLED BY signal %d", signum);
#ifndef NO_OOPS_SUPPORT
	oops(uc->uc_mcontext, signum == SIGSEGV || signum == SIGABRT);
#endif
	eDebug("-------");
	bsodFatal();
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
