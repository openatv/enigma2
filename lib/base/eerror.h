#ifndef __E_ERROR__
#define __E_ERROR__

#include "config.h"
#include <string>
#include <map>       
#include <new>
#include <libsig_comp.h>

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
