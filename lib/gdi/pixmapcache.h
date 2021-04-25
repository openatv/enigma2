#ifndef __pixmapcache_h
#define __pixmapcache_h

#include <lib/gdi/gpixmap.h>

#ifndef SWIG

class PixmapCache
{
private:
	static uint MaximumSize;
public:
	static void PixmapDisposed(gPixmap *pixmap);
	static gPixmap* Get(const char *filename);
	static void Set(const char *filename, gPixmap *pixmap);
};

#endif

#endif
