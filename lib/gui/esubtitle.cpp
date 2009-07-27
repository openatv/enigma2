#include <lib/gui/esubtitle.h>
#include <lib/gdi/grc.h>
#include <lib/base/estring.h>

	/*
		ok, here's much room for improvements.
	
		first, the placing of the individual elements is sub-optimal.
		then maybe a colored background would be an option.
		....
 	*/	

eSubtitleWidget::eSubtitleStyle eSubtitleWidget::subtitleStyles[Subtitle_MAX];

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
	m_page = p;
	m_page_ok = 1;
	invalidate(m_visible_region);  // invalidate old visible regions
	m_visible_region.rects.clear();

	int elements = m_page.m_elements.size();
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
			eRect &area = m_page.m_elements[i].m_area;
			area.setLeft(startX);
			area.setTop(size_per_element * i + startY);
			area.setWidth(width);
			area.setHeight(size_per_element);
			m_visible_region.rects.push_back(area);
		}
	}
	m_hide_subtitles_timer->start(7500, true);
	invalidate(m_visible_region);  // invalidate new regions
}

void eSubtitleWidget::setPage(const eDVBSubtitlePage &p)
{
	eDebug("setPage");
	m_dvb_page = p;
	invalidate(m_visible_region);  // invalidate old visible regions
	m_visible_region.rects.clear();
	for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
	{
		eDebug("add %d %d %d %d", it->m_position.x(), it->m_position.y(), it->m_pixmap->size().width(), it->m_pixmap->size().height());
		eDebug("disp width %d, disp height %d", p.m_display_size.width(), p.m_display_size.height());
		eRect r = eRect(it->m_position, it->m_pixmap->size());
		r.scale(size().width(), p.m_display_size.width(), size().height(), p.m_display_size.height());
		m_visible_region.rects.push_back(r);
	}
	m_dvb_page_ok = 1;
	m_hide_subtitles_timer->start(7500, true);
	invalidate(m_visible_region);  // invalidate new regions
}

void eSubtitleWidget::setPage(const ePangoSubtitlePage &p)
{
	m_pango_page = p;
	m_pango_page_ok = 1;
	invalidate(m_visible_region);  // invalidate old visible regions
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
			area.setTop(size_per_element * i + startY);
			area.setWidth(width);
			area.setHeight(size_per_element);
			m_visible_region.rects.push_back(area);
		}
	}
	int timeout_ms = m_pango_page.m_timeout;
	m_hide_subtitles_timer->start(timeout_ms, true);
	invalidate(m_visible_region);  // invalidate new regions
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

		if (m_pixmap)
		{
			eRect r = m_pixmap_dest;
			r.scale(size().width(), 720, size().height(), 576);
			painter.blitScale(m_pixmap, r);
		} else if (m_page_ok)
		{
			int elements = m_page.m_elements.size();
			painter.setFont(subtitleStyles[Subtitle_TTX].font);
			for (int i=0; i<elements; ++i)
			{
				eDVBTeletextSubtitlePageElement &element = m_page.m_elements[i];
				eRect &area = element.m_area;
				eRect shadow = area;
				shadow.moveBy(subtitleStyles[Subtitle_TTX].shadow_offset);
				painter.setForegroundColor(subtitleStyles[Subtitle_TTX].shadow_color);
				painter.renderText(shadow, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
				if ( !subtitleStyles[Subtitle_TTX].have_foreground_color )
					painter.setForegroundColor(element.m_color);
				else
					painter.setForegroundColor(subtitleStyles[Subtitle_TTX].foreground_color);
				painter.renderText(area, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
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
				std::string::size_type loc = text.find("<", 0 );
				if ( loc != std::string::npos )
				{
					switch (char(text.at(1)))
					{
					case 'i':
						face = Subtitle_Italic;
						break;
					case 'b':
						face = Subtitle_Bold;
						break;
					}
					text = text.substr(3, text.length()-7);
				}
				text = replace_all(text, "&apos;", "'");
				text = replace_all(text, "&quot;", "\"");
				text = replace_all(text, "&amp;", "&");
				painter.setFont(subtitleStyles[face].font);
				eRect &area = element.m_area;
				eRect shadow = area;
				shadow.moveBy(subtitleStyles[face].shadow_offset);
				painter.setForegroundColor(subtitleStyles[face].shadow_color);
				painter.renderText(shadow, text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
				if ( !subtitleStyles[face].have_foreground_color && element.m_have_color )
					painter.setForegroundColor(element.m_color);
				else
					painter.setForegroundColor(subtitleStyles[face].foreground_color);
				painter.renderText(area, text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
			}
		}
		else if (m_dvb_page_ok)
		{
			for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
			{
				eRect r = eRect(it->m_position, it->m_pixmap->size());
				r.scale(size().width(), m_dvb_page.m_display_size.width(), size().height(),  m_dvb_page.m_display_size.height());
				painter.blitScale(it->m_pixmap, r);
			}
		}
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}

void eSubtitleWidget::setFontStyle(subfont_t face, gFont *font, int haveColor, const gRGB &col, const gRGB &shadowCol, const ePoint &shadowOffset)
{
	subtitleStyles[face].font = font;
	subtitleStyles[face].have_foreground_color = haveColor;
	subtitleStyles[face].foreground_color = col;
	subtitleStyles[face].shadow_color = shadowCol;
	subtitleStyles[face].shadow_offset = shadowOffset;
}

