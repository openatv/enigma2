#ifndef __png_h
#define __png_h

#include <lib/gdi/gpixmap.h>

#ifndef SWIG
struct GifFile
{
	char *file;
	unsigned char *pic_buffer;
	gRGB *palette;
	int palette_size;
	int ox;
	int oy;

	GifFile(const char *mfile):
		file(strdup(mfile)),
		pic_buffer(NULL),
		palette(NULL),
		palette_size(0),
		ox(0),
		oy(0)
	{
	}

	~GifFile()
	{
		if (pic_buffer != NULL)	delete pic_buffer;
		if (palette != NULL) delete palette;
		free(file);
	}

};
#endif

SWIG_VOID(int) loadPNG(ePtr<gPixmap> &SWIG_OUTPUT, const char *filename, int accel = 0, int cached = 1);
SWIG_VOID(int) loadJPG(ePtr<gPixmap> &SWIG_OUTPUT, const char *filename, int cached = 0);
SWIG_VOID(int) loadJPG(ePtr<gPixmap> &SWIG_OUTPUT, const char *filename, ePtr<gPixmap> alpha, int cached = 0);
SWIG_VOID(int) loadSVG(ePtr<gPixmap> &SWIG_OUTPUT, const char *filename, int cached = 1, int width = 0, int height = 0, float scale = 0);

SWIG_VOID(int) loadGIF(ePtr<gPixmap> &SWIG_OUTPUT, const char *filename, int accel = 0,int cached = 0);

int loadImage(ePtr<gPixmap> &result, const char *filename, int accel = 0, int width = 0, int height = 0);
int savePNG(const char *filename, gPixmap *pixmap);

#endif
