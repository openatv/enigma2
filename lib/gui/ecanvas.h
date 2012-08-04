#ifndef __lib_gui_ecanvas_h
#define __lib_gui_ecanvas_h

#include <lib/gui/epixmap.h>

class eCanvas: public ePixmap
{
public:
	eCanvas(eWidget *parent);

	void setSize(eSize size);

	void clear(gRGB color);
	void fillRect(eRect rect, gRGB color);
	void writeText(eRect where, gRGB fg, gRGB bg, gFont *font, const char *string, int flags);
};

#endif
