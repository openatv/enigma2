#include <lib/gui/esubtitle.h>
#include <lib/gdi/grc.h>

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

void eSubtitleWidget::setPage(const eDVBTeletextSubtitlePage &p)
{
	m_page = p;
	m_page_ok = 1;
	m_hide_subtitles_timer.start(5000, true);
	invalidate();  // FIXME
}

void eSubtitleWidget::setPage(const eDVBSubtitlePage &p)
{
	m_dvb_page = p;
	invalidate(m_visible_region);  // invalidate old visible regions
	m_visible_region.rects.clear();
	for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
		m_visible_region.rects.push_back(eRect(it->m_position, it->m_pixmap->size()));
	m_dvb_page_ok = 1;
	m_hide_subtitles_timer.start(5000, true);
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
		ePtr<gFont> font = new gFont("Regular", 30);
		painter.setFont(font);
		
/*		if (!m_page_ok && !m_dvb_page_ok)
			painter.renderText(eRect(ePoint(0, 0), size()), "waiting for subtitles...", gPainter::RT_WRAP);
		else */if (m_page_ok)
		{
			int elements = m_page.m_elements.size();
			int height = size().height();
			int size_per_element = height / (elements ? elements : 1);
			for (int i=0; i<elements; ++i)
			{
				painter.setForegroundColor(gRGB(0,0,0));
				painter.renderText(eRect(2, size_per_element * i + 2, size().width(), size_per_element), m_page.m_elements[i].m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
				painter.setForegroundColor(m_page.m_elements[i].m_color);
				painter.renderText(eRect(0, size_per_element * i, size().width(), size_per_element), m_page.m_elements[i].m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
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
