#include <lib/gui/esubtitle.h>
#include <lib/gdi/grc.h>
#include <lib/base/estring.h>
#include <lib/base/nconfig.h>

std::map<eSubtitleWidget::subfont_t, eSubtitleWidget::eSubtitleStyle> eSubtitleWidget::subtitleStyles;

eSubtitleWidget::eSubtitleWidget(eWidget *parent)
	: eWidget(parent), m_hide_subtitles_timer(eTimer::create(eApp))
{
	setBackgroundColor(gRGB(0,0,0,255));
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	m_pango_page_ok = 0;
	CONNECT(m_hide_subtitles_timer->timeout, eSubtitleWidget::clearPage);
}

#define startX 50
void eSubtitleWidget::setPage(const eDVBTeletextSubtitlePage &p)
{
	eDVBTeletextSubtitlePage newpage = p;
	m_page = p;
	m_page.clear();
	m_page_ok = 1;
	invalidate(m_visible_region); // invalidate old visible regions
	m_visible_region.rects.clear();

	unsigned int elements = newpage.m_elements.size();
	if (elements)
	{
		int width = size().width() - startX * 2;
		std::string configvalue;
		bool original_position = (ePythonConfigQuery::getConfigValue("config.subtitles.ttx_subtitle_original_position", configvalue) >= 0 && configvalue == "True");
		bool rewrap = (ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_rewrap", configvalue) >= 0 && configvalue == "True");
		int color_mode = 0;
		if (!ePythonConfigQuery::getConfigValue("config.subtitles.ttx_subtitle_colors", configvalue))
		{
			color_mode = atoi(configvalue.c_str());
		}
		gRGB color;
		bool original_colors = false;
		switch (color_mode)
		{
			case 0: /* use original teletext colors */
				color = newpage.m_elements[0].m_color;
				original_colors = true;
				break;
			default:
			case 1: /* white */
				color = gRGB(255, 255, 255);
			break;
			case 2: /* yellow */
				color = gRGB(255, 255, 0);
			break;
		}

		if (!original_position)
		{
			int height = size().height() / 3;

			int lowerborder = 50;
			if (!ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_position", configvalue))
			{
				lowerborder = atoi(configvalue.c_str());
			}
			int line = newpage.m_elements[0].m_source_line;
			/* create a new page with just one text element */
			m_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(color, "", 0));
			for (unsigned int i = 0; i < elements; ++i)
			{
				if (!m_page.m_elements[0].m_text.empty()) m_page.m_elements[0].m_text += " ";
				if (original_colors && color != newpage.m_elements[i].m_color)
				{
					color = newpage.m_elements[i].m_color;
					m_page.m_elements[0].m_text += (std::string)color;
				}
				if (line != newpage.m_elements[i].m_source_line)
				{
					line = newpage.m_elements[i].m_source_line;
					if (!rewrap) m_page.m_elements[0].m_text += "\\n";
				}
				m_page.m_elements[0].m_text += newpage.m_elements[i].m_text;
			}
			eRect &area = m_page.m_elements[0].m_area;
			area.setLeft((size().width() - width) / 2);
			area.setTop(size().height() - height - lowerborder);
			area.setWidth(width);
			area.setHeight(height);
			m_visible_region |= area;
		}
		else
		{
			int size_per_element = (size().height() - 25) / 24;
			int line = newpage.m_elements[0].m_source_line;
			int currentelement = 0;
			m_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(color, "", line));
			for (unsigned int i = 0; i < elements; ++i)
			{
				if (!m_page.m_elements[currentelement].m_text.empty()) m_page.m_elements[currentelement].m_text += " ";
				if (original_colors && color != newpage.m_elements[i].m_color)
				{
					color = newpage.m_elements[i].m_color;
					m_page.m_elements[currentelement].m_text += (std::string)color;
				}
				if (line != newpage.m_elements[i].m_source_line)
				{
					line = newpage.m_elements[i].m_source_line;
					m_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(color, "", line));
					currentelement++;
				}
				m_page.m_elements[currentelement].m_text += newpage.m_elements[i].m_text;
			}
			for (unsigned int i = 0; i < m_page.m_elements.size(); i++)
			{
				eRect &area = m_page.m_elements[i].m_area;
				area.setLeft(startX);
				area.setTop(size_per_element * m_page.m_elements[i].m_source_line);
				area.setWidth(width);
				area.setHeight(size_per_element * 2); //teletext subtitles are double height only even lines are used
				m_visible_region |= area;
			}
		}
	}
	m_hide_subtitles_timer->start(7500, true);
	invalidate(m_visible_region); // invalidate new regions
}

void eSubtitleWidget::setPage(const eDVBSubtitlePage &p)
{
	eDebug("setPage");
	m_dvb_page = p;
	invalidate(m_visible_region); // invalidate old visible regions
	m_visible_region.rects.clear();
	int line = 0;
	int original_position = 0;
	std::string configvalue;
	if (!ePythonConfigQuery::getConfigValue("config.subtitles.dvb_subtitles_original_position", configvalue))
		original_position = atoi(configvalue.c_str());
	for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
	{
		if (original_position)
		{
			int lines = m_dvb_page.m_regions.size();
			if (!ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_position", configvalue))
			{
				int lowerborder = atoi(configvalue.c_str());
				if (original_position == 1)
					it->m_position=ePoint(it->m_position.x(), p.m_display_size.height() - (lines - line) * it->m_pixmap->size().height() - lowerborder);
				else
					it->m_position=ePoint(it->m_position.x(), it->m_position.y() + 55 - lowerborder);
			}
			line++;
		}
		eDebug("add %d %d %d %d", it->m_position.x(), it->m_position.y(), it->m_pixmap->size().width(), it->m_pixmap->size().height());
		eDebug("disp width %d, disp height %d", p.m_display_size.width(), p.m_display_size.height());
		eRect r = eRect(it->m_position, it->m_pixmap->size());
		r.scale(size().width(), p.m_display_size.width(), size().height(), p.m_display_size.height());
		m_visible_region |= r;
	}
	m_dvb_page_ok = 1;
	m_hide_subtitles_timer->start(7500, true);
	invalidate(m_visible_region); // invalidate new regions
}

void eSubtitleWidget::setPage(const ePangoSubtitlePage &p)
{
	m_pango_page = p;
	m_pango_page_ok = 1;
	invalidate(m_visible_region); // invalidate old visible regions
	m_visible_region.rects.clear();

	int elements = m_pango_page.m_elements.size();
	if (elements)
	{
		int startY = elements > 1
			? size().height() / 2
			: size().height() / 3 * 2;
		int width = size().width() - startX * 2;
		int height = size().height() - startY;
		int size_per_element = height / (elements ? elements : 1);
		for (int i=0; i<elements; ++i)
		{
			eRect &area = m_pango_page.m_elements[i].m_area;
			area.setLeft(startX);
			int lowerborder=50;
			std::string subtitle_position;
			if (!ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_position", subtitle_position))
			{
				lowerborder = atoi(subtitle_position.c_str());
			}
			area.setTop(size_per_element * i + startY - lowerborder);
			area.setWidth(width);
			area.setHeight(size_per_element);
			m_visible_region |= area;
		}
	}
	int timeout_ms = m_pango_page.m_timeout;
	m_hide_subtitles_timer->start(timeout_ms, true);
	invalidate(m_visible_region); // invalidate new regions
}

void eSubtitleWidget::clearPage()
{
	eDebug("subtitle timeout... hide");
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	m_pango_page_ok = 0;
	invalidate(m_visible_region);
	m_visible_region.rects.clear();
}

void eSubtitleWidget::setPixmap(ePtr<gPixmap> &pixmap, gRegion changed, eRect pixmap_dest)
{
	m_pixmap = pixmap;
	m_pixmap_dest = pixmap_dest; /* this is in a virtual 720x576 cage */
	
		/* incoming "changed" regions are relative to the physical pixmap area, so they have to be scaled to the virtual pixmap area, then to the screen */
	changed.scale(m_pixmap_dest.width(), 720, m_pixmap_dest.height(), 576);
	changed.moveBy(ePoint(m_pixmap_dest.x(), m_pixmap_dest.y()));

	if (pixmap->size().width() && pixmap->size().height())
		changed.scale(size().width(), pixmap->size().width(), size().height(), pixmap->size().height());
	
	invalidate(changed);
}

int eSubtitleWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		gPainter &painter = *(gPainter*)data2;

		getStyle(style);
		eWidget::event(event, data, data2);

		std::string configvalue;

		int rt_halignment_flag;
		if (ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_alignment", configvalue))
			configvalue = "center";
		if (configvalue == "center")
			rt_halignment_flag = gPainter::RT_HALIGN_CENTER;
		else if (configvalue == "left")
			rt_halignment_flag = gPainter::RT_HALIGN_LEFT;
		else
			rt_halignment_flag = gPainter::RT_HALIGN_RIGHT;

		int borderwidth = 2;
		if (!ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_borderwidth", configvalue))
		{
			borderwidth = atoi(configvalue.c_str());
		}

		int fontsize = 34;
		if (!ePythonConfigQuery::getConfigValue("config.subtitles.subtitle_fontsize", configvalue))
		{
			fontsize = atoi(configvalue.c_str());
		}

		if (m_pixmap)
		{
			eRect r = m_pixmap_dest;
			r.scale(size().width(), 720, size().height(), 576);
			painter.blitScale(m_pixmap, r);
		}
		else if (m_page_ok)
		{
			unsigned int elements = m_page.m_elements.size();

			subtitleStyles[Subtitle_TTX].font->pointSize=fontsize;

			painter.setFont(subtitleStyles[Subtitle_TTX].font);
			for (unsigned int i = 0; i < elements; ++i)
			{
				eDVBTeletextSubtitlePageElement &element = m_page.m_elements[i];
				if (!element.m_text.empty())
				{
					eRect &area = element.m_area;
					if (!subtitleStyles[Subtitle_TTX].have_foreground_color)
						painter.setForegroundColor(element.m_color);
					else
						painter.setForegroundColor(subtitleStyles[Subtitle_TTX].foreground_color);
					painter.renderText(area, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_BOTTOM|rt_halignment_flag, subtitleStyles[Subtitle_TTX].border_color, borderwidth);
				}
			}
		}
		else if (m_pango_page_ok)
		{
			int elements = m_pango_page.m_elements.size();
			subfont_t face;

			for (int i=0; i<elements; ++i)
			{
				face = Subtitle_Regular;
				ePangoSubtitlePageElement &element = m_pango_page.m_elements[i];
				std::string text = element.m_pango_line;
				text = replace_all(text, "&apos;", "'");
				text = replace_all(text, "&quot;", "\"");
				text = replace_all(text, "&amp;", "&");
				text = replace_all(text, "&lt", "<");
				text = replace_all(text, "&gt", ">");

				bool yellow_color = (ePythonConfigQuery::getConfigValue("config.subtitles.pango_subtitles_yellow", configvalue) >= 0 && configvalue == "True");
				if (yellow_color)
					text = (std::string) gRGB(255,255,0) + text;
				text = replace_all(text, "<i>", yellow_color ? "" : (std::string) gRGB(0,255,255));
				text = replace_all(text, "<b>", yellow_color ? "" : (std::string) gRGB(255,255,0));
				text = replace_all(text, "</i>", yellow_color ? "" : (std::string) gRGB(255,255,255));
				text = replace_all(text, "</b>", yellow_color ? "" : (std::string) gRGB(255,255,255));

				subtitleStyles[face].font->pointSize=fontsize;
				painter.setFont(subtitleStyles[face].font);

				eRect &area = element.m_area;
				if ( !subtitleStyles[face].have_foreground_color && element.m_have_color )
					painter.setForegroundColor(element.m_color);
				else
					painter.setForegroundColor(subtitleStyles[face].foreground_color);
				painter.renderText(area, text, gPainter::RT_WRAP|gPainter::RT_VALIGN_BOTTOM|rt_halignment_flag, subtitleStyles[face].border_color, borderwidth);
			}
		}
		else if (m_dvb_page_ok)
		{
			for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
			{
				eRect r = eRect(it->m_position, it->m_pixmap->size());
				r.scale(size().width(), m_dvb_page.m_display_size.width(), size().height(), m_dvb_page.m_display_size.height());
				painter.blitScale(it->m_pixmap, r);
			}
		}
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}

void eSubtitleWidget::setFontStyle(subfont_t face, gFont *font, int haveColor, const gRGB &col, const gRGB &borderCol, int borderWidth)
{
	subtitleStyles[face].font = font;
	subtitleStyles[face].have_foreground_color = haveColor;
	subtitleStyles[face].foreground_color = col;
	subtitleStyles[face].border_color = borderCol;
	subtitleStyles[face].border_width = borderWidth;
}
