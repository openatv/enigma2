#ifndef __png_h
#define __png_h

#include "grc.h"

gImage *loadPNG(const char *filename);
int savePNG(const char *filename, gPixmap *pixmap);

#endif
