#include <lib/gui/esubtitle.h>
#include <lib/gdi/grc.h>
#include <lib/base/estring.h>

	/*
		ok, here's much room for improvements.
	
		first, the placing of the individual elements is sub-optimal.
		then maybe a colored background would be an option.
		....
 	*/	

eSubtitleWidget::eSubtitleWidget(eWidget *parent)
	: eWidget(parent), m_hide_subtitles_timer(eApp)
{
	setBackgroundColor(gRGB(0,0,0,255));
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	CONNECT(m_hide_subtitles_timer.timeout, eSubtitleWidget::clearPage);
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
	m_hide_subtitles_timer.start(7500, true);
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
		m_visible_region.rects.push_back(eRect(it->m_position, it->m_pixmap->size()));
	}
	m_dvb_page_ok = 1;
	m_hide_subtitles_timer.start(7500, true);
	invalidate(m_visible_region);  // invalidate new regions
}

void eSubtitleWidget::clearPage()
{
	eDebug("subtitle timeout... hide");
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	invalidate(m_visible_region);
	m_visible_region.rects.clear();
}

void eSubtitleWidget::setPixmap(ePtr<gPixmap> &pixmap, gRegion changed)
{
	m_pixmap = pixmap;
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
			painter.blit(m_pixmap, ePoint(0,0));
		else if (m_page_ok)
		{
			int elements = m_page.m_elements.size();
			ePtr<gFont> font = new gFont("Regular", 38);
			painter.setFont(font);
			for (int i=0; i<elements; ++i)
			{
				eDVBTeletextSubtitlePageElement &element = m_page.m_elements[i];
				eRect &area = element.m_area;
				eRect shadow = area;
				shadow.moveBy(3,3);
				painter.setForegroundColor(gRGB(0,0,0));
				painter.renderText(shadow, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
				painter.setForegroundColor(element.m_color);
				painter.renderText(area, element.m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
			}
		}
		else if (m_dvb_page_ok)
		{
			for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
				painter.blit(it->m_pixmap, it->m_position);
		}
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}
