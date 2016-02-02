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

#define CHECKFORMAT __attribute__ ((__format__(__printf__, 3, 4)))

extern Signal2<void, int, const std::string&> logOutput;
extern int logOutputConsole;

/*
 *  Default loglevel and log filter tag.
 *  Maybe reset by setting ENIGMA_DEBUG_LVL and ENIGMA_DEBUG_TAG environmnet
 *  variables. main() will check the environemnt to set the values.
 */
extern int debugLvl;
extern char *debugTag;

void CHECKFORMAT eDebugLow(int lvl, int flags, const char*, ...);
void CHECKFORMAT eDebugLow(const char* tag, int flags, const char*, ...);
enum { lvlDebug=4, lvlWarning=2, lvlFatal=0 };

#define DEFAULT_DEBUG_LVL  4

#define _DBGFLG_NONEWLINE  1
#define _DBGFLG_NOTIME     2
#define _DBGFLG_FATAL      4
#define eFatal(...)			eDebugLow(lvlFatal, _DBGFLG_FATAL, __VA_ARGS__)

#ifdef DEBUG

# define eLog(lvl, ...)			eDebugLow(lvl,        0,                 ##__VA_ARGS__)
# define eLogNoNewLineStart(lvl, ...)	eDebugLow(lvl,        _DBGFLG_NONEWLINE, ##__VA_ARGS__)
# define eLogNoNewLine(lvl, ...)	eDebugLow(lvl,        _DBGFLG_NOTIME | _DBGFLG_NONEWLINE, ##__VA_ARGS__)

# define eWarning(...)			eDebugLow(lvlWarning, 0,                   __VA_ARGS__)

# define eDebug(...)			eDebugLow(lvlDebug,   0,                   __VA_ARGS__)
# define eDebugNoNewLineStart(...)	eDebugLow(lvlDebug,   _DBGFLG_NONEWLINE,   __VA_ARGS__)
# define eDebugNoNewLine(...)		eDebugLow(lvlDebug,   _DBGFLG_NOTIME | _DBGFLG_NONEWLINE, __VA_ARGS__)

# define ASSERT(x) { if (!(x)) eFatal("%s:%d ASSERTION %s FAILED!", __FILE__, __LINE__, #x); }

#else  // DEBUG

# define eLog(...)			;
# define eLogNoNewLineStart(...)	;
# define eLogNoNewLine(...)		;

# define eWarning(...)			;

# define eDebug(...)			;
# define eDebugNoNewLineStart(...)	;
# define eDebugNoNewLine(...)		;

# define ASSERT(x)			;

#endif

void eWriteCrashdump();

#endif // SWIG

void ePythonOutput(const char *);

#endif // __E_ERROR__
