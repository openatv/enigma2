#include <lib/gui/esubtitle.h>
#include <lib/gdi/grc.h>
#include <lib/gdi/font.h>
#include <lib/base/estring.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/base/esettings.h>

std::map<eSubtitleWidget::subfont_t, eSubtitleWidget::eSubtitleStyle> eSubtitleWidget::subtitleStyles;

eSubtitleWidget::eSubtitleWidget(eWidget *parent)
	: eWidget(parent), m_hide_subtitles_timer(eTimer::create(eApp))
{
	eWidget::setBackgroundColor(gRGB(0, 0, 0, 255));
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
		gRGB color;
		bool original_colors = false;
		switch (eSubtitleSettings::ttx_subtitle_colors)
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

		if (!eSubtitleSettings::ttx_subtitle_original_position)
		{
			int height = size().height() / 3;

			int lowerborder = eSubtitleSettings::subtitle_position;
			int line = newpage.m_elements[0].m_source_line;
			/* create a new page with just one text element */
			m_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(color, "", 0));
			for (unsigned int i = 0; i < elements; ++i)
			{
				if (!m_page.m_elements[0].m_text.empty())
					m_page.m_elements[0].m_text += " ";
				if (original_colors && color != newpage.m_elements[i].m_color)
				{
					color = newpage.m_elements[i].m_color;
					m_page.m_elements[0].m_text += (std::string)color;
				}
				if (line != newpage.m_elements[i].m_source_line)
				{
					line = newpage.m_elements[i].m_source_line;
					if (!eSubtitleSettings::subtitle_rewrap)
						m_page.m_elements[0].m_text += "\\n";
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
				if (!m_page.m_elements[currentelement].m_text.empty())
					m_page.m_elements[currentelement].m_text += " ";
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
				area.setHeight(size_per_element * 2); // teletext subtitles are double height only even lines are used
				m_visible_region |= area;
			}
		}
	}
	m_hide_subtitles_timer->start(7500, true);
	invalidate(m_visible_region); // invalidate new regions
}

void eSubtitleWidget::setPage(const eDVBSubtitlePage &p)
{
	eDebug("[eSubtitleWidget] setPage");
	m_dvb_page = p;
	invalidate(m_visible_region); // invalidate old visible regions
	m_visible_region.rects.clear();
	int line = 0;
	for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
	{
		if (eSubtitleSettings::dvb_subtitles_original_position)
		{
			int lines = m_dvb_page.m_regions.size();
			int lowerborder = eSubtitleSettings::subtitle_position;
			if (lowerborder >= 0)
			{
				if (eSubtitleSettings::dvb_subtitles_original_position == 1)
					it->m_position = ePoint(it->m_position.x(), p.m_display_size.height() - (lines - line) * it->m_pixmap->size().height() - lowerborder);
				else
					it->m_position = ePoint(it->m_position.x(), it->m_position.y() + 55 - lowerborder);
			}
			line++;
		}
		eDebug("[eSubtitleWidget] add %d %d %d %d", it->m_position.x(), it->m_position.y(), it->m_pixmap->size().width(), it->m_pixmap->size().height());
		eDebug("[eSubtitleWidget] disp width %d, disp height %d", p.m_display_size.width(), p.m_display_size.height());
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
	int elements, element, startY, width, height, size_per_element;

	m_pango_page = p;
	m_pango_page_ok = 1;
	invalidate(m_visible_region); // invalidate old visible regions
	m_visible_region.rects.clear();
	int lowerborder = eSubtitleSettings::subtitle_position;

	elements = m_pango_page.m_elements.size();

	if (eSubtitleSettings::subtitle_rewrap || eSubtitleSettings::colorise_dialogs)
	{
		size_t ix, colorise_dialogs_current = 0;
		std::vector<std::string> colorise_dialogs_colours;
		std::string replacement;
		bool alignment_center = eSubtitleSettings::subtitle_alignment_flag == gPainter::RT_HALIGN_CENTER;

		if (eSubtitleSettings::colorise_dialogs)
		{
			colorise_dialogs_colours.push_back((std::string)gRGB(0xff, 0xff, 0x00)); // yellow
			colorise_dialogs_colours.push_back((std::string)gRGB(0x00, 0xff, 0xff)); // cyan
			colorise_dialogs_colours.push_back((std::string)gRGB(0xff, 0x00, 0xff)); // magenta
			colorise_dialogs_colours.push_back((std::string)gRGB(0x00, 0xff, 0x00)); // green
			colorise_dialogs_colours.push_back((std::string)gRGB(0xff, 0xaa, 0xaa)); // light red
			colorise_dialogs_colours.push_back((std::string)gRGB(0xaa, 0xaa, 0xff)); // light blue
		}

		for (element = 0; element < elements; element++)
		{
			std::string &line = m_pango_page.m_elements[element].m_pango_line;

			for (ix = 0; ix < line.length(); ix++)
			{
				if (eSubtitleSettings::subtitle_rewrap && !line.compare(ix, 1, "\n"))
					line.replace(ix, 1, " ");

				if (eSubtitleSettings::colorise_dialogs && !line.compare(ix, 2, "- "))
				{
					/* workaround for rendering fault when colouring is enabled, rewrap is off and alignment is center */
					replacement = std::string((!eSubtitleSettings::subtitle_rewrap && alignment_center) ? "  " : "") + colorise_dialogs_colours.at(colorise_dialogs_current);

					line.replace(ix, 2, replacement);
					colorise_dialogs_current++;

					if (colorise_dialogs_current >= colorise_dialogs_colours.size())
						colorise_dialogs_current = 0;
				}
			}
		}
	}

	if (elements > 1)
		startY = size().height() / 2;
	else
		startY = size().height() / 3 * 2;

	width = size().width() - startX * 2;
	height = size().height() - startY;

	if (elements != 0)
		size_per_element = height / elements;
	else
		size_per_element = height;

	for (element = 0; element < elements; element++)
	{
		eRect &area = m_pango_page.m_elements[element].m_area;
		area.setLeft(startX);
		area.setTop(size_per_element * element + startY - lowerborder);
		area.setWidth(width);
		area.setHeight(size_per_element);
		m_visible_region |= area;
	}

	m_hide_subtitles_timer->start(m_pango_page.m_timeout, true);
	invalidate(m_visible_region); // invalidate new regions
}

void eSubtitleWidget::setPage(const eVobSubtitlePage &p)
{
	eRect r = eRect(0, 0, 720, 576);
	ePtr<gPixmap> pixmap = p.m_pixmap;
	setPixmap(pixmap, r, r);
	m_hide_subtitles_timer->start(p.m_timeout, true);
}

void eSubtitleWidget::clearPage()
{
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	m_pango_page_ok = 0;
	m_pixmap = 0;
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
		gPainter &painter = *(gPainter *)data2;

		getStyle(style);
		eWidget::event(event, data, data2);
		int borderwidth = eSubtitleSettings::subtitle_borderwidth * getDesktop(0)->size().width() / 1280;
		int fontsize = eSubtitleSettings::subtitle_fontsize * getDesktop(0)->size().width() / 1280;
		int bcktrans = eSubtitleSettings::subtitles_backtrans;

		if (m_pixmap)
		{
			eRect r = m_pixmap_dest;
			r.scale(size().width(), 720, size().height(), 576);
			painter.blitScale(m_pixmap, r);
		}
		else if (m_page_ok)
		{
			unsigned int elements = m_page.m_elements.size();

			subtitleStyles[Subtitle_TTX].font->pointSize = fontsize;

			painter.setFont(subtitleStyles[Subtitle_TTX].font);
			for (unsigned int i = 0; i < elements; ++i)
			{
				eDVBTeletextSubtitlePageElement &element = m_page.m_elements[i];
				if (!element.m_text.empty())
				{
					eRect &area = element.m_area;
					if (bcktrans != 255)
					{
						ePtr<eTextPara> para = new eTextPara(area);
						para->setFont(subtitleStyles[Subtitle_TTX].font);
						para->renderString(element.m_text.c_str(), RS_WRAP);
						eRect bbox = para->getBoundBox();
						int bboxWidth = bbox.width();
						if (eSubtitleSettings::subtitle_alignment_flag == gPainter::RT_HALIGN_RIGHT)
							bbox.setLeft(area.left() + area.width() - bboxWidth - borderwidth);
						else if (eSubtitleSettings::subtitle_alignment_flag == gPainter::RT_HALIGN_LEFT)
							bbox.setLeft(area.left() - borderwidth);
						else
							bbox.setLeft(area.left() + area.width() / 2 - bboxWidth / 2 - borderwidth);
						bbox.setWidth(bboxWidth + borderwidth * 2);
						if (eSubtitleSettings::ttx_subtitle_original_position)
							bbox.setHeight(area.height());
						else
						{
							int bboxTop = area.top() + area.height() - bbox.height() - 2 * borderwidth;
							int bboxHeight = bbox.height() + borderwidth * 2;
							bbox.setTop(bboxTop);
							bbox.setHeight(bboxHeight);
							area.setTop(area.top() - borderwidth);
						}
						painter.setForegroundColor(gRGB(0, 0, 0, bcktrans));
						painter.fill(bbox);
						borderwidth = 0;
					}
					if (!subtitleStyles[Subtitle_TTX].have_foreground_color)
						painter.setForegroundColor(element.m_color);
					else
						painter.setForegroundColor(subtitleStyles[Subtitle_TTX].foreground_color);
					painter.renderText(area, element.m_text, gPainter::RT_WRAP | gPainter::RT_VALIGN_BOTTOM | eSubtitleSettings::subtitle_alignment_flag, subtitleStyles[Subtitle_TTX].border_color, borderwidth);
				}
			}
		}
		else if (m_pango_page_ok)
		{
			int elements = m_pango_page.m_elements.size();
			subfont_t face;

			for (int i = 0; i < elements; ++i)
			{
				face = Subtitle_Regular;
				ePangoSubtitlePageElement &element = m_pango_page.m_elements[i];
				std::string text = element.m_pango_line;

				if (eSubtitleSettings::pango_subtitle_removehi)
					removeHearingImpaired(text);

				text = replace_all(text, "&apos;", "'");
				text = replace_all(text, "&quot;", "\"");
				text = replace_all(text, "&amp;", "&");
				text = replace_all(text, "&lt;", "<");
				text = replace_all(text, "&gt;", ">");

				if (eSubtitleSettings::pango_subtitle_fontswitch)
				{
					if (text.find("<i>") != std::string::npos || text.find("</i>") != std::string::npos)
						if (text.find("<b>") != std::string::npos || text.find("</b>") != std::string::npos)
							face = Subtitle_MAX;
						else
							face = Subtitle_Italic;
					else if (text.find("<b>") != std::string::npos || text.find("</b>") != std::string::npos)
						face = Subtitle_Bold;
				}
				int subtitleColors = eSubtitleSettings::pango_subtitle_colors;
				if (!subtitleColors)
				{
					text = replace_all(text, "<i>", gRGB(255, 255, 0));
					text = replace_all(text, "<b>", gRGB(0, 255, 255));
					text = replace_all(text, "<u>", (std::string)gRGB(0, 255, 0));
					text = replace_all(text, "</i>", (std::string)gRGB(255, 255, 255));
					text = replace_all(text, "</b>", (std::string)gRGB(255, 255, 255));
					text = replace_all(text, "</u>", (std::string)gRGB(255, 255, 255));
				}
				else
				{
					if (subtitleColors == 2)
						text = (std::string)gRGB(255, 255, 0) + text;
					text = replace_all(text, "</u>", "");
					text = replace_all(text, "</i>", "");
					text = replace_all(text, "</b>", "");
					text = replace_all(text, "<u>", "");
					text = replace_all(text, "<i>", "");
					text = replace_all(text, "<b>", "");
				}
				text = replace_all(text, "</font>", "");
				size_t subtitleFont = 0;
				while ((subtitleFont = text.find("<font ", subtitleFont)) != std::string::npos)
				{
					size_t end = text.find('>', subtitleFont);
					text.erase(subtitleFont, end - subtitleFont + 1);
				}
				subtitleStyles[face].font->pointSize = fontsize;
				painter.setFont(subtitleStyles[face].font);
				eRect &area = element.m_area;
				if (bcktrans != 255)
				{
					ePtr<eTextPara> para = new eTextPara(area);
					para->setFont(subtitleStyles[face].font);
					para->renderString(text.c_str(), RS_WRAP);
					eRect bbox = para->getBoundBox();
					int bboxWidth = bbox.width();
					if (eSubtitleSettings::subtitle_alignment_flag == gPainter::RT_HALIGN_RIGHT)
						bbox.setLeft(area.left() + area.width() - bboxWidth - borderwidth);
					else if (eSubtitleSettings::subtitle_alignment_flag == gPainter::RT_HALIGN_LEFT)
						bbox.setLeft(area.left() - borderwidth);
					else
						bbox.setLeft(area.left() + area.width() / 2 - bboxWidth / 2 - borderwidth);
					bbox.setWidth(bboxWidth + borderwidth * 2);
					int bboxTop = area.top() + area.height() - bbox.height() - 2 * borderwidth;
					int bboxHeight = bbox.height() + borderwidth * 2;
					bbox.setTop(bboxTop);
					bbox.setHeight(bboxHeight);
					area.setTop(area.top() - borderwidth);
					painter.setForegroundColor(gRGB(0, 0, 0, bcktrans));
					painter.fill(bbox);
					borderwidth = 0;
				}
				if (!subtitleStyles[face].have_foreground_color && element.m_have_color)
					painter.setForegroundColor(element.m_color);
				else
					painter.setForegroundColor(subtitleStyles[face].foreground_color);
				painter.renderText(area, text, gPainter::RT_WRAP | gPainter::RT_VALIGN_BOTTOM | eSubtitleSettings::subtitle_alignment_flag, subtitleStyles[face].border_color, borderwidth);
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

void eSubtitleWidget::removeHearingImpaired(std::string &str)
{
	// remove texts in round brackets
	while (true)
	{
		std::string::size_type loc = str.find('(');
		if (loc == std::string::npos)
			break;
		std::string::size_type enp = str.find(')');
		if (enp == std::string::npos)
			break;
		str.erase(loc, enp - loc + 1);
	}

	// remove texts in square brackets
	while (true)
	{
		std::string::size_type loc = str.find('[');
		if (loc == std::string::npos)
			break;
		std::string::size_type enp = str.find(']');
		if (enp == std::string::npos)
			break;
		str.erase(loc, enp - loc + 1);
	}

	// cleanup: remove empty lines (consisting of spaces and hyphens only)
	std::string::size_type line_start = 0;
	bool empty_line = true;
	for (std::string::size_type p = 0; p < str.length(); p++)
	{
		unsigned char ch = str[p];

		if (ch != ' ' && ch != '-' && ch != '\n')
			empty_line = false;

		if (ch == '\n' || p == str.length() - 1)
		{
			if (empty_line)
			{
				// remove line
				str.erase(line_start, p - line_start + 1);
				p = line_start - 1;
			}
			line_start = p + 1;
			empty_line = true;
		}
	}

	// cleanup: remove trailing line breaks
	while (str[str.length() - 1] == '\n')
		str.erase(str.length() - 1, 1);
}
