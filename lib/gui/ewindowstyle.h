#ifndef __lib_gui_ewindowstyle_h
#define __lib_gui_ewindowstyle_h

class eWindow;
class eSize;

#include <lib/base/object.h>

class eWindowStyle: public iObject
{
public:
	virtual void handleNewSize(eWindow *wnd, const eSize &size) = 0;
};

class eWindowStyleSimple: public eWindowStyle
{
	DECLARE_REF;
public:
	eWindowStyleSimple();
	void handleNewSize(eWindow *wnd, const eSize &size);
	int m_border_top, m_border_left, m_border_right, m_border_bottom;
};

#endif
