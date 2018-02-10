#ifndef __lib_gui_subtitle_h
#define __lib_gui_subtitle_h

#include <map>
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
	pts_t m_show_pts;
	int m_timeout; /* in milliseconds */
	std::vector<ePangoSubtitlePageElement> m_elements;
	void clear() { m_elements.clear(); }
};

struct eVobSubtitlePage
{
	pts_t m_show_pts;
	int m_timeout; /* in milliseconds */
	ePtr<gPixmap> m_pixmap;
};

struct eDVBTeletextSubtitlePage;
struct eDVBSubtitlePage;

class eSubtitleWidget: public eWidget, public iSubtitleUser, public sigc::trackable
{
public:
	eSubtitleWidget(eWidget *parent);

	void setPage(const eDVBTeletextSubtitlePage &p);
	void setPage(const eDVBSubtitlePage &p);
	void setPage(const ePangoSubtitlePage &p);
	void clearPage();
	void setPixmap(ePtr<gPixmap> &pixmap, gRegion changed, eRect dest = eRect(0, 0, 720, 576));
	void destroy() { delete this; }

	typedef enum { Subtitle_TTX, Subtitle_Regular, Subtitle_Bold, Subtitle_Italic, Subtitle_MAX } subfont_t;
	struct eSubtitleStyle
	{
		subfont_t face;
		int have_foreground_color;
		gRGB foreground_color, border_color;
		int  border_width;
		ePtr<gFont> font;
	};

	static void setFontStyle(subfont_t face, gFont *font, int autoColor, const gRGB &col, const gRGB &borderCol, int borderWidth);

protected:
	int event(int event, void *data=0, void *data2=0);
	void removeHearingImpaired(std::string& str);
private:
	int m_page_ok;
	eDVBTeletextSubtitlePage m_page;

	int m_dvb_page_ok;
	eDVBSubtitlePage m_dvb_page;

	int m_pango_page_ok;
	ePangoSubtitlePage m_pango_page;

	ePtr<eTimer> m_hide_subtitles_timer;

	gRegion m_visible_region;

	static std::map<subfont_t, eSubtitleStyle> subtitleStyles;

	ePtr<gPixmap> m_pixmap;  // pixmap to paint on next evtPaint
	eRect m_pixmap_dest;
};

#endif
