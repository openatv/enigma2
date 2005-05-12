#include <lib/base/eerror.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <string>

// #include <lib/gui/emessage.h>

#ifdef MEMLEAK_CHECK
AllocList *allocList;
pthread_mutex_t memLock =
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;
#else
	#include <lib/base/elock.h>
#endif

int infatal=0;

Signal2<void, int, const std::string&> logOutput;
int logOutputConsole=1;

void eFatal(const char* fmt, ...)
{
	char buf[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, 1024, fmt, ap);
	va_end(ap);
	logOutput(lvlFatal, buf);
	fprintf(stderr, "%s\n",buf );
#if 0
	if (!infatal)
	{
		infatal=1;
		eMessageBox msg(buf, "FATAL ERROR", eMessageBox::iconError|eMessageBox::btOK);
		msg.show();
		msg.exec();
	}
#endif

	_exit(0);
}

#ifdef DEBUG
void eDebug(const char* fmt, ...)
{
	char buf[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, 1024, fmt, ap);
	va_end(ap);
	logOutput(lvlDebug, std::string(buf) + "\n");
	if (logOutputConsole)
		fprintf(stderr, "%s\n", buf);
}

void eDebugNoNewLine(const char* fmt, ...)
{
	char buf[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, 1024, fmt, ap);
	va_end(ap);
	logOutput(lvlDebug, buf);
	if (logOutputConsole)
		fprintf(stderr, "%s", buf);
}

void eWarning(const char* fmt, ...)
{
	char buf[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, 1024, fmt, ap);
	va_end(ap);
	logOutput(lvlWarning, std::string(buf) + "\n");
	if (logOutputConsole)
		fprintf(stderr, "%s\n", buf);
}
#endif // DEBUG
