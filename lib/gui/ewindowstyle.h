#ifndef __lib_gui_ewindowstyle_h
#define __lib_gui_ewindowstyle_h

class eWindow;
class eSize;
class gFont;

#include <lib/base/object.h>

class eWindowStyle_ENUMS
{
#ifdef SWIG
	eWindowStyle_ENUMS();
	~eWindowStyle_ENUMS();
#endif
public:
	enum {
		styleLabel,
		styleListboxSelected,
		styleListboxNormal,
		styleListboxMarked,
		styleListboxMarkedAndSelected
	};

	enum {
		frameButton,
		frameListboxEntry
	};

	enum {
		fontStatic,
		fontButton,
		fontTitlebar
	};
};

SWIG_IGNORE(eWindowStyle);
class eWindowStyle: public eWindowStyle_ENUMS, public iObject
{
#ifdef SWIG
	eWindowStyle();
#endif
public:
#ifndef SWIG
	virtual void handleNewSize(eWindow *wnd, eSize &size, eSize &offset) = 0;
	virtual void paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title) = 0;
	virtual void paintBackground(gPainter &painter, const ePoint &offset, const eSize &size) = 0;
	virtual void setStyle(gPainter &painter, int what) = 0;
	virtual void drawFrame(gPainter &painter, const eRect &frame, int type) = 0;
	virtual RESULT getFont(int what, ePtr<gFont> &font) = 0;
#endif
	virtual ~eWindowStyle() = 0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eWindowStyle>, eWindowStylePtr);

SWIG_IGNORE(eWindowStyleManager);
class eWindowStyleManager: public iObject
{
	DECLARE_REF(eWindowStyleManager);
#ifdef SWIG
	eWindowStyleManager();
	~eWindowStyleManager();
#endif
public:
#ifndef SWIG
	eWindowStyleManager();
	~eWindowStyleManager();
	static SWIG_VOID(int) getInstance(ePtr<eWindowStyleManager> &SWIG_NAMED_OUTPUT(mgr)) { mgr = m_instance; if (!mgr) return -1; return 0; }
#endif
	void getStyle(int style_id, ePtr<eWindowStyle> &SWIG_OUTPUT);
	void setStyle(int style_id, eWindowStyle *style);
private:
	static eWindowStyleManager *m_instance;
	std::map<int, ePtr<eWindowStyle> > m_current_style;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<eWindowStyleManager>, eWindowStyleManager);
SWIG_EXTEND(ePtr<eWindowStyleManager>,
	static ePtr<eWindowStyleManager> getInstance()
	{
		extern ePtr<eWindowStyleManager> NewWindowStylePtr(void);
		return NewWindowStylePtr();
	}
);

#ifndef SWIG
class eWindowStyleSimple: public eWindowStyle
{
	DECLARE_REF(eWindowStyleSimple);
	ePtr<gFont> m_fnt;
	gColor m_border_color_tl, m_border_color_br, m_title_color_back, m_title_color, m_background_color;
	
	int m_border_top, m_border_left, m_border_right, m_border_bottom;
public:
	eWindowStyleSimple();
	void handleNewSize(eWindow *wnd, eSize &size, eSize &offset);
	void paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title);
	void paintBackground(gPainter &painter, const ePoint &offset, const eSize &size);
	void setStyle(gPainter &painter, int what);
	void drawFrame(gPainter &painter, const eRect &frame, int what);
	RESULT getFont(int what, ePtr<gFont> &font);
};
#endif

#endif
