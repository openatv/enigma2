#ifndef __lib_gui_ewindowstyle_h
#define __lib_gui_ewindowstyle_h

class eWindow;
class eSize;
class gFont;

#include <lib/base/object.h>

class eWindowStyle: public iObject
{
public:
	virtual void handleNewSize(eWindow *wnd, const eSize &size) = 0;
	virtual void paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title) = 0;
	virtual void paintBackground(gPainter &painter, const ePoint &offset, const eSize &size) = 0;
	virtual void setForegroundStyle(gPainter &painter) = 0;
	virtual void drawButtonFrame(gPainter &painter, const eRect &frame) = 0;
	virtual ~eWindowStyle() = 0;
};

class eWindowStyleSimple: public eWindowStyle
{
	DECLARE_REF;
private:
	ePtr<gFont> m_fnt;
	gColor m_border_color_tl, m_border_color_br, m_title_color_back, m_title_color, m_background_color;
	
	int m_border_top, m_border_left, m_border_right, m_border_bottom;
public:
	eWindowStyleSimple();
	void handleNewSize(eWindow *wnd, const eSize &size);
	void paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title);
	void paintBackground(gPainter &painter, const ePoint &offset, const eSize &size);
	void setForegroundStyle(gPainter &painter);
	void drawButtonFrame(gPainter &painter, const eRect &frame);
};

#endif
