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

int logOutputConsole = 1;
int debugLvl = lvlDebug;

static pthread_mutex_t DebugLock = PTHREAD_ADAPTIVE_MUTEX_INITIALIZER_NP;
#define RINGBUFFER_SIZE 16384
static char ringbuffer[RINGBUFFER_SIZE];
static unsigned int ringbuffer_head;
static void logOutput(const char *data, unsigned int len)
{
	singleLock s(DebugLock);
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

void retrieveLogBuffer(const char **p1, unsigned int *s1, const char **p2, unsigned int *s2)
{
	unsigned int begin = ringbuffer_head;
	while (ringbuffer[begin] == 0)
	{
		++begin;
		if (begin == RINGBUFFER_SIZE)
			begin = 0;
		if (begin == ringbuffer_head)
			return;
	}

	if (begin < ringbuffer_head)
	{
		*p1 = ringbuffer + begin;
		*s1 = ringbuffer_head - begin;
		*p2 = NULL;
		*s2 = NULL;
	}
	else
	{
		*p1 = ringbuffer + begin;
		*s1 = RINGBUFFER_SIZE - begin;
		*p2 = ringbuffer;
		*s2 = ringbuffer_head;
	}
}


extern void bsodFatal(const char *component);

void eDebugImpl(int flags, const char* fmt, ...)
{
	char buf[1024];
	int pos = 0;

	if (! (flags & _DBGFLG_NOTIME)) {
		struct timespec tp;
		clock_gettime(CLOCK_MONOTONIC, &tp);
		pos = snprintf(buf, sizeof(buf), "<%6lu.%03lu> ", tp.tv_sec, tp.tv_nsec/1000000);
	}

	va_list ap;
	va_start(ap, fmt);
	pos += vsnprintf(buf + pos, sizeof(buf) - pos, fmt, ap);
	va_end(ap);

	if (!(flags & _DBGFLG_NONEWLINE)) {
		/* buf will still be null-terminated here, so it is always safe
		 * to do this. The remainder of this function does not rely
		 * on buf being null terminated. */
		buf[pos++] = '\n';
	}

	logOutput(buf, pos);

	if (logOutputConsole)
		::write(2, buf, pos);

	if (flags & _DBGFLG_FATAL)
		bsodFatal("enigma2");
}

void ePythonOutput(const char *string)
{
#ifdef DEBUG
	// Only show message when the debug level is at least "warning"
	if (debugLvl >= lvlWarning)
		eDebugImpl(_DBGFLG_NONEWLINE, "%s", string);
#endif
}
