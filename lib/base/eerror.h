#ifndef __E_ERROR__
#define __E_ERROR__

#include "config.h"
#include <string>
#include <map>       
#include <new>
#include <libsig_comp.h>

void eFatal(const char* fmt, ...);

class eString;

enum { lvlDebug=1, lvlWarning=2, lvlFatal=4 };

extern Signal2<void, int, const eString&> logOutput;
extern int logOutputConsole;

#ifdef ASSERT
#undef ASSERT
#endif

#ifdef DEBUG
    void eDebug(const char* fmt, ...);
    void eDebugNoNewLine(const char* fmt, ...);
    void eWarning(const char* fmt, ...);
    #define ASSERT(x) { if (!(x)) eFatal("%s:%d ASSERTION %s FAILED!", __FILE__, __LINE__, #x); }
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
