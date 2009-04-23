#ifndef __lib_gui_subtitle_h
#define __lib_gui_subtitle_h

#include <lib/gui/ewidget.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/subtitle.h>

struct ePangoSubtitlePageElement
{
	gRGB m_color;
	std::string m_pango_line;
	eRect m_area;
	ePangoSubtitlePageElement(const gRGB &color, const std::string &text)
		: m_color(color), m_pango_line(text)
	{
	}
};

struct ePangoSubtitlePage
{
	pts_t show_pts;
	int m_timeout; /* in milliseconds */
	std::vector<ePangoSubtitlePageElement> m_elements;
	void clear() { m_elements.clear(); }
};

class eDVBTeletextSubtitlePage;
class eDVBPangoSubtitlePage;
class ePangoSubtitlePage;

class eSubtitleWidget: public eWidget, public Object
{
public:
	eSubtitleWidget(eWidget *parent);
	
	void setPage(const eDVBTeletextSubtitlePage &p);
	void setPage(const eDVBSubtitlePage &p);
	void setPage(const ePangoSubtitlePage &p);
	void clearPage();

	void setPixmap(ePtr<gPixmap> &pixmap, gRegion changed);
protected:
	int event(int event, void *data=0, void *data2=0);

private:
	int m_page_ok;
	eDVBTeletextSubtitlePage m_page;

	int m_dvb_page_ok;
	eDVBSubtitlePage m_dvb_page;

	int m_pango_page_ok;
	ePangoSubtitlePage m_pango_page;

	ePtr<eTimer> m_hide_subtitles_timer;

	gRegion m_visible_region;

	ePtr<gPixmap> m_pixmap;  // pixmap to paint on next evtPaint
};

#endif
