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
	virtual void setStyle(gPainter &painter, int what) = 0;
	enum {
		styleLabel,
		styleListboxSelected,
		styleListboxNormal
	};
	
	virtual void drawFrame(gPainter &painter, const eRect &frame, int type) = 0;
	
	enum {
		frameButton,
		frameListboxEntry
	};
	virtual ~eWindowStyle() = 0;

};

class eWindowStyleSimple: public eWindowStyle
{
	DECLARE_REF(eWindowStyleSimple);
private:
	ePtr<gFont> m_fnt;
	gColor m_border_color_tl, m_border_color_br, m_title_color_back, m_title_color, m_background_color;
	
	int m_border_top, m_border_left, m_border_right, m_border_bottom;
public:
	eWindowStyleSimple();
	void handleNewSize(eWindow *wnd, const eSize &size);
	void paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title);
	void paintBackground(gPainter &painter, const ePoint &offset, const eSize &size);
	void setStyle(gPainter &painter, int what);
	void drawFrame(gPainter &painter, const eRect &frame, int what);
};

class eWindowStyleSkinned: public eWindowStyle
{
	DECLARE_REF(eWindowStyleSkinned);
public:
	eWindowStyleSkinned();
	void handleNewSize(eWindow *wnd, const eSize &size);
	void paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title);
	void paintBackground(gPainter &painter, const ePoint &offset, const eSize &size);
	void setStyle(gPainter &painter, int what);
	void drawFrame(gPainter &painter, const eRect &frame, int what);
	
	enum {
		bsWindow,
		bsButton,
#ifndef SWIG
		bsMax
#endif
	};
	
	enum {
		bpTopLeft     =     1,
		bpTop         =     2,
		bpTopRight    =     4,
		bpLeft        =     8,
		bpRight       =  0x10,
		bpBottomLeft  =  0x20,
		bpBottom      =  0x40,
		bpBottomRight =  0x80,
		bpBackground  = 0x100
	};
private:
	struct borderSet
	{
		ePtr<gPixmap> m_pixmap[9];
	};
	
	void drawBorder(gPainter &painter, const eSize &size, const struct borderSet &border, int where);
};

#endif
