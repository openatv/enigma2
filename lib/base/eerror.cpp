#include <lib/base/eerror.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <lib/base/estring.h>

// #include <lib/gui/emessage.h>

int infatal=0;

Signal2<void, int, const eString&> logOutput;
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
	logOutput(lvlDebug, eString(buf) + "\n");
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
	logOutput(lvlWarning, eString(buf) + "\n");
	if (logOutputConsole)
		fprintf(stderr, "%s\n", buf);
}
#endif // DEBUG
