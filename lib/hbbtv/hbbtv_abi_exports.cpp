/*
 * Dream HbbTV ABI export anchors.
 *
 * libenigma2hbbtv.so from DreamOS is loaded by the browser/NPAPI path with
 * unresolved C++ symbols against Enigma2.  Some of those symbols are RTTI
 * objects, for example:
 *
 *   _ZTI25iStaticServiceInformation
 *   typeinfo for iStaticServiceInformation
 *
 * If the Enigma2 executable does not emit and dynamically export those weak
 * RTTI objects, dlopen(libenigma2hbbtv.so) fails although the backend itself
 * is present and Python-visible.
 *
 * This file intentionally ODR-uses relevant interface types.  Because
 * libenigma_hbbtv.a is linked into enigma2 via --whole-archive, this object
 * is kept in the final executable.  With -rdynamic/--export-dynamic these RTTI
 * objects become visible to dlopen() consumers.
 */

#include <typeinfo>
#include <cstdarg>
#include <cstdio>

#include <lib/base/eerror.h>
#include <lib/service/iservice.h>
#include <lib/hbbtv/hbbtv.h>
#include <lib/hbbtv/oipfapplication.h>

/* OpenATV provides eFatal as a macro. Dream binary plugins need a function. */
#ifdef eFatal
#undef eFatal
#endif


#define HBBTV_ABI_EXPORT __attribute__((visibility("default"), used))

extern "C" {

HBBTV_ABI_EXPORT const void *openatv_hbbtv_abi_typeinfo_iStaticServiceInformation =
	&typeid(iStaticServiceInformation);

HBBTV_ABI_EXPORT const void *openatv_hbbtv_abi_typeinfo_iServiceInformation =
	&typeid(iServiceInformation);

HBBTV_ABI_EXPORT const void *openatv_hbbtv_abi_typeinfo_iPlayableService =
	&typeid(iPlayableService);

HBBTV_ABI_EXPORT const void *openatv_hbbtv_abi_typeinfo_iPauseableService =
	&typeid(iPauseableService);

HBBTV_ABI_EXPORT const void *openatv_hbbtv_abi_typeinfo_iSeekableService =
	&typeid(iSeekableService);

HBBTV_ABI_EXPORT const void *openatv_hbbtv_abi_typeinfo_eHbbtv =
	&typeid(eHbbtv);

HBBTV_ABI_EXPORT const void *openatv_hbbtv_abi_typeinfo_eOipfApplication =
	&typeid(eOipfApplication);

HBBTV_ABI_EXPORT void openatv_hbbtv_abi_export_anchor()
{
	/* Intentionally empty.  The exported RTTI references above are the anchor. */
}

}


/*
 * DreamOS ABI shim.
 *
 * Symbol expected by libenigma2hbbtv.so:
 *
 *   _Z6eFatalPKcz
 *   eFatal(char const*, ...)
 *
 * Keep C++ linkage intentionally. extern "C" would create the wrong symbol.
 */
HBBTV_ABI_EXPORT void eFatal(const char *fmt, ...)
{
	char buffer[2048];

	va_list args;
	va_start(args, fmt);
	vsnprintf(buffer, sizeof(buffer), fmt ? fmt : "", args);
	va_end(args);

	buffer[sizeof(buffer) - 1] = 0;
	eDebugImpl(_DBGFLG_FATAL, "%s", buffer);
}