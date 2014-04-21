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
	void drawLine(int x0, int y0, int x1, int y1, gRGB color);
	void writeText(eRect where, gRGB fg, gRGB bg, gFont *font, const char *string, int flags);
	void drawRotatedLine(int ox, int oy, int x0, int y0, int x1, int y1, float angle, bool cw, gRGB color);
};

#endif
