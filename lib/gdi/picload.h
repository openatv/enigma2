#ifndef __picload_h__
#define __picload_h__

#include "Python.h"
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/epng.h>

SWIG_VOID(int) loadPic(ePtr<gPixmap> &SWIG_OUTPUT, std::string filename, int x, int y, int aspect, int resize_mode=0, int rotate=0, int background=0, std::string cachefile="");
PyObject *getExif(const char *filename);

#endif // __picload_h__
