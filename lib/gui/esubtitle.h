#ifndef __lib_gui_subtitle_h
#define __lib_gui_subtitle_h

#include <lib/gui/ewidget.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/subtitle.h>

class eDVBTeletextSubtitlePage;

class eSubtitleWidget: public eWidget
{
public:
	eSubtitleWidget(eWidget *parent);
	
	void setPage(const eDVBTeletextSubtitlePage &p);
	void setPage(const eDVBSubtitlePage &p);
	void clearPage();
	
protected:
	int event(int event, void *data=0, void *data2=0);

private:
	int m_page_ok;
	eDVBTeletextSubtitlePage m_page;

	int m_dvb_page_ok;
	eDVBSubtitlePage m_dvb_page;
};

#endif
