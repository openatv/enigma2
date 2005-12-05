#ifndef __png_h
#define __png_h

#include <lib/gdi/gpixmap.h>

SWIG_VOID(int) loadPNG(ePtr<gPixmap> &SWIG_OUTPUT, const char *filename);
int savePNG(const char *filename, gPixmap *pixmap);

#endif
