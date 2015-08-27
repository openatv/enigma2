#ifndef __E_ERROR__
#define __E_ERROR__

#include <string>
#include <map>
#include <new>
#include <libsig_comp.h>

// to use memleak check change the following in configure.ac
// * add -DMEMLEAK_CHECK and -rdynamic to CPP_FLAGS

#ifdef MEMLEAK_CHECK
#define BACKTRACE_DEPTH 5
#include <map>
#include <lib/base/elock.h>
#include <execinfo.h>
#include <string>
#include <new>
#include <cxxabi.h>
typedef struct
{
	unsigned int address;
	unsigned int size;
	const char *file;
	void *backtrace[BACKTRACE_DEPTH];
	unsigned char btcount;
	unsigned short line;
	unsigned char type;
} ALLOC_INFO;

typedef std::map<unsigned int, ALLOC_INFO> AllocList;

extern AllocList *allocList;
extern pthread_mutex_t memLock;

static inline void AddTrack(unsigned int addr,  unsigned int asize,  const char *fname, unsigned int lnum, unsigned int type)
{
	ALLOC_INFO info;

	if(!allocList)
		allocList = new(AllocList);

	info.address = addr;
	info.file = fname;
	info.line = lnum;
	info.size = asize;
	info.type = type;
	info.btcount = 0; //backtrace( info.backtrace, BACKTRACE_DEPTH );
	singleLock s(memLock);
	(*allocList)[addr]=info;
};

static inline void RemoveTrack(unsigned int addr, unsigned int type)
{
	if(!allocList)
		return;
	AllocList::iterator i;
	singleLock s(memLock);
	i = allocList->find(addr);
	if ( i != allocList->end() )
	{
		if ( i->second.type != type )
			i->second.type=3;
		else
			allocList->erase(i);
	}
};

inline void * operator new(size_t size, const char *file, int line)
{
	void *ptr = (void *)malloc(size);
	AddTrack((unsigned int)ptr, size, file, line, 1);
	return(ptr);
};

inline void operator delete(void *p)
{
	RemoveTrack((unsigned int)p,1);
	free(p);
};

inline void * operator new[](size_t size, const char *file, int line)
{
	void *ptr = (void *)malloc(size);
	AddTrack((unsigned int)ptr, size, file, line, 2);
	return(ptr);
};

inline void operator delete[](void *p)
{
	RemoveTrack((unsigned int)p, 2);
	free(p);
};

void DumpUnfreed();
#define new new(__FILE__, __LINE__)

#endif // MEMLEAK_CHECK

#ifndef NULL
#define NULL 0
#endif

#ifdef ASSERT
#undef ASSERT
#endif

#ifndef SWIG

#define CHECKFORMAT __attribute__ ((__format__(__printf__, 1, 2)))

extern Signal2<void, int, const std::string&> logOutput;
extern int logOutputConsole;
extern int logOutputColors;

void _eFatal(const char *file, int line, const char *function, const char* fmt, ...);
#define eFatal(args ...) _eFatal(__FILE__, __LINE__, __FUNCTION__, args)
enum { lvlDebug=1, lvlWarning=2, lvlFatal=4 };

#ifdef DEBUG
	void _eDebug(const char *file, int line, const char *function, const char* fmt, ...);
#define eDebug(args ...) _eDebug(__FILE__, __LINE__, __FUNCTION__, args)
	void _eDebugNoNewLineStart(const char *file, int line, const char *function, const char* fmt, ...);
#define eDebugNoNewLineStart(args ...) _eDebugNoNewLineStart(__FILE__, __LINE__, __FUNCTION__, args)
	void CHECKFORMAT eDebugNoNewLine(const char*, ...);
	void CHECKFORMAT eDebugNoNewLineEnd(const char*, ...);
	void _eWarning(const char *file, int line, const char *function, const char* fmt, ...);
#define eWarning(args ...) _eWarning(__FILE__, __LINE__, __FUNCTION__, args)
	#define ASSERT(x) { if (!(x)) eFatal("%s:%d ASSERTION %s FAILED!", __FILE__, __LINE__, #x); }
#else  // DEBUG
	inline void eDebug(const char* fmt, ...)
	{
	}

	inline void eDebugNoNewLineStart(const char* fmt, ...)
	{
	}

	inline void eDebugNoNewLine(const char* fmt, ...)
	{
	}

	inline void eWarning(const char* fmt, ...)
	{
	}
	#define ASSERT(x) do { } while (0)
#endif //DEBUG

void eWriteCrashdump();

#endif // SWIG

void ePythonOutput(const char *file, int line, const char *function, const char *string);

#endif // __E_ERROR__
