#ifndef __E_ERROR__
#define __E_ERROR__

#include "config.h"
#include <string>
#include <map>       
#include <new>
#include <libsig_comp.h>

// to use memleak check change the following in configure.ac
// * add -rdynamic to LD_FLAGS
// * add -DMEMLEAK_CHECK to CPP_FLAGS

#ifdef MEMLEAK_CHECK
#define BACKTRACE_DEPTH 5
// when you have c++filt and corresponding libs on your platform
// then add -DHAVE_CPP_FILT to CPP_FLAGS in configure.ac
#include <map>
#include <lib/base/elock.h>
#include <execinfo.h>
#include <string>
#include <new>
#endif // MEMLEAK_CHECK

#ifndef NULL
#define NULL 0
#endif

void eFatal(const char* fmt, ...);

enum { lvlDebug=1, lvlWarning=2, lvlFatal=4 };

#ifndef SWIG
extern Signal2<void, int, const std::string&> logOutput;
extern int logOutputConsole;
#endif

#ifdef ASSERT
#undef ASSERT
#endif

#ifdef DEBUG
    void eDebug(const char* fmt, ...);
    void eDebugNoNewLine(const char* fmt, ...);
    void eWarning(const char* fmt, ...);
#ifndef SWIG
    #define ASSERT(x) { if (!(x)) eFatal("%s:%d ASSERTION %s FAILED!", __FILE__, __LINE__, #x); }
#endif

#ifdef MEMLEAK_CHECK
typedef struct
{
	unsigned int address;
	unsigned int size;
	char *file;
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
	info.file = strdup(fname);
	info.line = lnum;
	info.size = asize;
	info.type = type;
	info.btcount = backtrace( info.backtrace, BACKTRACE_DEPTH );
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
		{
			free(i->second.file);
			allocList->erase(i);
		}
	}
};

inline void * operator new(unsigned int size, const char *file, int line)
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

inline void * operator new[](unsigned int size, const char *file, int line)
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

inline void DumpUnfreed()
{
	AllocList::iterator i;
	unsigned int totalSize = 0;

	if(!allocList)
		return;

	for(i = allocList->begin(); i != allocList->end(); i++)
	{
		unsigned int tmp;
		printf("%s\tLINE %d\tADDRESS %p\t%d unfreed\ttype %d\n",
			i->second.file, i->second.line, (void*)i->second.address, i->second.size, i->second.type);
		totalSize += i->second.size;
		char **bt_string = backtrace_symbols( i->second.backtrace, i->second.btcount );
		for ( tmp=0; tmp < i->second.btcount; tmp++ )
		{
			if ( bt_string[tmp] )
			{
#ifdef HAVE_CPP_FILT
				char *beg = strchr(bt_string[tmp], '(');
				if ( beg )
				{
					std::string tmp1(beg+1);
					int pos1=tmp1.find('+'), pos2=tmp1.find(')');
					std::string tmp2(tmp1.substr(pos1,(pos2-pos1)-1));
					std::string cmd="c++filt ";
					cmd+=tmp1.substr(0,pos1);
					FILE *f = popen(cmd.c_str(), "r");
					char buf[256];
					if (f)
					{
						size_t rd = fread(buf, 1, 255, f);
						if ( rd > 0 )
						{
							buf[rd-1]=0;
							printf("%s %s\n", buf, tmp2.c_str() );
						}
						else
							printf("%s\n", tmp1.substr(0,pos1).c_str());
						fclose(f);
					}
				}
				else
#endif // HAVE_CPP_FILT
					printf("%s\n", bt_string[tmp]);
			}
		}
		free(bt_string);
		printf("\n");
	}

	printf("-----------------------------------------------------------\n");
	printf("Total Unfreed: %d bytes\n", totalSize);
	fflush(stdout);
};
#define new new(__FILE__, __LINE__)

#endif // MEMLEAK_CHECK


#else
    inline void eDebug(const char* fmt, ...)
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

#endif // __E_ERROR__
