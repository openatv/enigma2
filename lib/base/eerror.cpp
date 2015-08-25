#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/base/elock.h>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <time.h>

#include <string>

#ifdef MEMLEAK_CHECK
AllocList *allocList;
pthread_mutex_t memLock =
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;

void DumpUnfreed()
{
	AllocList::iterator i;
	unsigned int totalSize = 0;

	if(!allocList)
		return;

	CFile f("/tmp/enigma2_mem.out", "w");
	if (!f)
		return;
	size_t len = 1024;
	char *buffer = (char*)malloc(1024);
	for(i = allocList->begin(); i != allocList->end(); i++)
	{
		unsigned int tmp;
		fprintf(f, "%s\tLINE %d\tADDRESS %p\t%d unfreed\ttype %d (btcount %d)\n",
			i->second.file, i->second.line, (void*)i->second.address, i->second.size, i->second.type, i->second.btcount);
		totalSize += i->second.size;

		char **bt_string = backtrace_symbols( i->second.backtrace, i->second.btcount );
		for ( tmp=0; tmp < i->second.btcount; tmp++ )
		{
			if ( bt_string[tmp] )
			{
				char *beg = strchr(bt_string[tmp], '(');
				if ( beg )
				{
					std::string tmp1(beg+1);
					int pos1=tmp1.find('+'), pos2=tmp1.find(')');
					if ( pos1 != std::string::npos && pos2 != std::string::npos )
					{
						std::string tmp2(tmp1.substr(pos1,(pos2-pos1)));
						tmp1.erase(pos1);
						if (tmp1.length())
						{
							int state;
							abi::__cxa_demangle(tmp1.c_str(), buffer, &len, &state);
							if (!state)
								fprintf(f, "%d %s%s\n", tmp, buffer,tmp2.c_str());
							else
								fprintf(f, "%d %s\n", tmp, bt_string[tmp]);
						}
					}
				}
				else
					fprintf(f, "%d %s\n", tmp, bt_string[tmp]);
			}
		}
		free(bt_string);
		if (i->second.btcount)
			fprintf(f, "\n");
	}
	free(buffer);

	fprintf(f, "-----------------------------------------------------------\n");
	fprintf(f, "Total Unfreed: %d bytes\n", totalSize);
	fflush(f);
};
#endif

Signal2<void, int, const std::string&> logOutput;
int logOutputConsole=1;

static pthread_mutex_t DebugLock =
	PTHREAD_ADAPTIVE_MUTEX_INITIALIZER_NP;

char *printtime(char buffer[], int size)
{
	struct tm loctime ;
	struct timeval tim;
	gettimeofday(&tim, NULL);
	localtime_r(&tim.tv_sec, &loctime);
	snprintf(buffer, size, "%02d:%02d:%02d.%03ld", loctime.tm_hour, loctime.tm_min, loctime.tm_sec, tim.tv_usec / 1000L);
	return buffer;
}

extern void bsodFatal(const char *component);

void _eFatal(const char *file, int line, const char *function, const char* fmt, ...)
{
	char buf[1024];
	char timebuffer[32];
	printtime(timebuffer, sizeof(timebuffer));
	snprintf(buf, sizeof(buf), "\e[31;1m%s \e[32;1m%s:%d \e[33;1m%s\e[30;1m ", timebuffer, file, line, function);
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf + strlen(buf), sizeof(buf) - strlen(buf), fmt, ap);
	va_end(ap);

	{
		singleLock s(DebugLock);
		logOutput(lvlFatal, std::string(buf) + "\n");
		fprintf(stderr, "FATAL: %s\n", buf);
	}
	bsodFatal("enigma2");
}

#ifdef DEBUG
void _eDebug(const char *file, int line, const char *function, const char* fmt, ...)
{
	char buf[1024];
	char timebuffer[32];
	printtime(timebuffer, sizeof(timebuffer));
	snprintf(buf, sizeof(buf), "\e[31;1m%s \e[32;1m%s:%d \e[33;1m%s\e[30;1m ", timebuffer, file, line, function);
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf + strlen(buf), sizeof(buf) - strlen(buf), fmt, ap);
	va_end(ap);
	singleLock s(DebugLock);
	logOutput(lvlDebug, std::string(buf) + "\n");
	if (logOutputConsole)
		fprintf(stderr, "%s\n", buf);
}

void _eDebugNoNewLineStart(const char *file, int line, const char *function, const char* fmt, ...)
{
	char buf[1024];
	char timebuffer[32];
	printtime(timebuffer, sizeof(timebuffer));
	snprintf(buf, sizeof(buf), "\e[31;1m%s \e[32;1m%s:%d \e[33;1m%s\e[30;1m ", timebuffer, file, line, function);
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf + strlen(buf), sizeof(buf) - strlen(buf), fmt, ap);
	va_end(ap);
	singleLock s(DebugLock);
	logOutput(lvlDebug, std::string(buf));
	if (logOutputConsole)
		fprintf(stderr, "%s", buf);
}

void eDebugNoNewLine(const char* fmt, ...)
{
	char buf[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	singleLock s(DebugLock);
	logOutput(lvlDebug, std::string(buf));
	if (logOutputConsole)
		fprintf(stderr, "%s", buf);
}

void eDebugNoNewLineEnd(const char* fmt, ...)
{
	char buf[1024];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	singleLock s(DebugLock);
	logOutput(lvlDebug, std::string(buf));
	if (logOutputConsole)
		fprintf(stderr, "%s\n", buf);
}

void _eWarning(const char *file, int line, const char *function, const char* fmt, ...)
{
	char buf[1024];
	char timebuffer[32];
	printtime(timebuffer, sizeof(timebuffer));
	snprintf(buf, sizeof(buf), "\e[31;1m%s \e[32;1m%s:%d \e[33;1m%s\e[30;1m ", timebuffer, file, line, function);
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf + strlen(buf), sizeof(buf) - strlen(buf), fmt, ap);
	va_end(ap);
	singleLock s(DebugLock);
	logOutput(lvlWarning, std::string(buf) + "\n");
	if (logOutputConsole)
		fprintf(stderr, "%s\n", buf);
}
#endif // DEBUG


void ePythonOutput(const char *file, int line, const char *function, const char *string)
{
#ifdef DEBUG
	char buf[1024];
	char timebuffer[32];
	printtime(timebuffer, sizeof(timebuffer));
	snprintf(buf, sizeof(buf), "\e[31;1m%s \e[34;1m%s:%d \e[33;1m%s\e[30;1m %s", timebuffer, file, line, function, string);
	singleLock s(DebugLock);
	logOutput(lvlWarning, string);
	if (logOutputConsole)
		fwrite(buf, 1, strlen(buf), stderr);
#endif
}

void eWriteCrashdump()
{
		/* implement me */
}
