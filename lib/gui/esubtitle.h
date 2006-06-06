#ifndef __lib_gui_subtitle_h
#define __lib_gui_subtitle_h

#include <lib/gui/ewidget.h>
#include <lib/dvb/teletext.h>

class eDVBTeletextSubtitlePage;

class eSubtitleWidget: public eWidget
{
public:
	eSubtitleWidget(eWidget *parent);
	
	void setPage(const eDVBTeletextSubtitlePage &p);
	void clearPage();
	
protected:
	int event(int event, void *data=0, void *data2=0);

private:
	int m_page_ok;
	eDVBTeletextSubtitlePage m_page;
};

#endif
