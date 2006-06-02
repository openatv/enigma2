#ifndef __lib_gui_subtitle_h
#define __lib_gui_subtitle_h

#include <lib/gui/ewidget.h>
#include <lib/dvb/teletext.h>

class eDVBTeletextSubtitlePage;

class eSubtitleWidget: public eWidget
{
public:
	eSubtitleWidget(eWidget *parent);
	
	void addPage(const eDVBTeletextSubtitlePage &p);
	void checkTiming();
	void activatePage();

protected:
	int event(int event, void *data=0, void *data2=0);

private:
	std::list<eDVBTeletextSubtitlePage> m_pages;
};

#endif
