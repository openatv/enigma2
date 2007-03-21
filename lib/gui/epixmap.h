#ifndef __lib_gui_epximap_h
#define __lib_gui_epixmap_h

#include <lib/gui/ewidget.h>

class ePixmap: public eWidget
{
	bool m_alphatest;
public:
	ePixmap(eWidget *parent);
	
	void setPixmap(gPixmap *pixmap);
	void setPixmap(ePtr<gPixmap> &pixmap);
	void setPixmapFromFile(const char *filename);
	void setAlphatest(bool alphatest);
protected:
	ePtr<gPixmap> m_pixmap;
	int event(int event, void *data=0, void *data2=0);
	void checkSize();
private:
	enum eLabelEvent
	{
		evtChangedPixmap = evtUserWidget,
	};
};

#endif
