#ifndef __lib_gui_epximap_h
#define __lib_gui_epixmap_h

#include <lib/gui/ewidget.h>

class ePixmap: public eWidget
{
public:
	ePixmap(eWidget *parent);
	
	void setPixmap(gPixmap *pixmap);
protected:
	ePtr<gPixmap> m_pixmap;
	int event(int event, void *data=0, void *data2=0);
private:
	enum eLabelEvent
	{
		evtChangedPixmap = evtUserWidget,
	};
};

#endif
