#ifndef __png_h
#define __png_h

#include <lib/gdi/gpixmap.h>

int loadPNG(ePtr<gPixmap> &pixmap, const char *filename);
int savePNG(const char *filename, gPixmap *pixmap);

#endif
