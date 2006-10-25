#include <lib/gui/esubtitle.h>
#include <lib/gdi/grc.h>

	/*
		ok, here's much room for improvements.
	
		first, the placing of the individual elements is sub-optimal.
		then maybe a colored background would be an option.
		....
 	*/	

eSubtitleWidget::eSubtitleWidget(eWidget *parent)
	: eWidget(parent)
{
	setBackgroundColor(gRGB(0,0,0,255));
	m_page_ok = 0;
	m_dvb_page_ok = 0;
}

void eSubtitleWidget::setPage(const eDVBTeletextSubtitlePage &p)
{
	m_page = p;
	m_page_ok = 1;
	invalidate();
}

void eSubtitleWidget::setPage(const eDVBSubtitlePage &p)
{
	m_dvb_page = p;
	m_dvb_page_ok = 1;
	invalidate();
}

void eSubtitleWidget::clearPage()
{
	m_page_ok = 0;
	m_dvb_page_ok = 0;
	invalidate();
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
			painter.setOffset(ePoint(0,0));
//			if (!m_dvb_page.m_regions.size())
//				eDebug("clear screen");
			for (std::list<eDVBSubtitleRegion>::iterator it(m_dvb_page.m_regions.begin()); it != m_dvb_page.m_regions.end(); ++it)
			{
				painter.resetClip(eRect(it->m_position, it->m_pixmap->size()));
				painter.blit(it->m_pixmap, it->m_position);
			}
		}
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}
