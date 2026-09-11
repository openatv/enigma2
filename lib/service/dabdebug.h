#ifndef __lib_service_dabdebug_h
#define __lib_service_dabdebug_h

#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>

inline bool eDABDebugEnabled()
{
	/* The setting is intentionally latched for the lifetime of Enigma2.  The
	 * Logs setup marks it as requiring a GUI restart, just like the other
	 * native subsystem debug switches. */
	static const bool enabled = eSimpleConfig::getBool("config.crash.debugDAB", false);
	return enabled;
}

#define eDABDebug(...) \
	do { \
		if (eDABDebugEnabled()) \
			eDebug(__VA_ARGS__); \
	} while (0)

#endif
