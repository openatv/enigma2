#ifndef __lib_gui_ewindow_h
#define __lib_gui_ewindow_h

#include <lib/gui/ewidget.h>
#include <lib/gui/ewindowstyle.h>

class eWidgetDesktop;

class eWindow: public eWidget
{
	friend class eWindowStyle;
public:
	eWindow(eWidgetDesktop *desktop);
	void setTitle(const std::string &string);
	eWidget *child() { return m_child; }
protected:
	enum eWindowEvents
	{
		evtTitleChanged = evtUserWidget,
	};
	int event(int event, void *data=0, void *data2=0);
private:
	std::string m_title;
	eWidget *m_child;
	ePtr<eWindowStyle> m_style;
};

#endif
