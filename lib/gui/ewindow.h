#ifndef __lib_gui_ewindow_h
#define __lib_gui_ewindow_h

#include <lib/gui/ewidget.h>
#include <lib/gui/ewindowstyle.h>

class eWidgetDesktop;

class eWindow: public eWidget
{
	friend class eWindowStyle;
public:
	eWindow(eWidgetDesktop *desktop, int z = 0);
	~eWindow();
	void setTitle(const std::string &string);
	std::string getTitle() const;
	eWidget *child() { return m_child; }
	void show();
	void hide();

	enum {
		wfNoBorder = 1
	};

	void setBackgroundColor(const gRGB &col);

	void setFlag(int flags);
	void clearFlag(int flags);
	void setAnimationMode(int mode);
protected:
	enum eWindowEvents
	{
		evtTitleChanged = evtUserWidget,
	};
	int event(int event, void *data=0, void *data2=0);
private:
	std::string m_title;
	eWidget *m_child;
	int m_flags;
	eWidgetDesktop *m_desktop;
	int m_animation_mode;
	static int m_has_animation_mode;
};

#endif
