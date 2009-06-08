#ifndef __lib_gui_subtitle_h
#define __lib_gui_subtitle_h

#include <lib/gui/ewidget.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/subtitle.h>

struct ePangoSubtitlePageElement
{
	gRGB m_color;
	bool m_have_color;
	std::string m_pango_line;
	eRect m_area;
	ePangoSubtitlePageElement(const gRGB &color, const std::string &text)
		: m_color(color), m_have_color(true), m_pango_line(text)
	{
	}
	ePangoSubtitlePageElement(const std::string &text)
		: m_have_color(false), m_pango_line(text)
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
	void setPixmap(ePtr<gPixmap> &pixmap, gRegion changed, eRect dest = eRect(0, 0, 720, 576));

	typedef enum { Subtitle_TTX, Subtitle_Regular, Subtitle_Bold, Subtitle_Italic, Subtitle_MAX } subfont_t;
	struct eSubtitleStyle
	{
		subfont_t face;
		int have_foreground_color, have_shadow_color;
		gRGB foreground_color, shadow_color;
		ePoint shadow_offset;
		ePtr<gFont> font;
	};

	static void setFontStyle(subfont_t face, gFont *font, int autoColor, const gRGB &col, const gRGB &shadowCol, const ePoint &shadowOffset);

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

	static eSubtitleStyle subtitleStyles[Subtitle_MAX];

	ePtr<gPixmap> m_pixmap;  // pixmap to paint on next evtPaint
	eRect m_pixmap_dest;
};

#endif
