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
}

void eSubtitleWidget::addPage(const eDVBTeletextSubtitlePage &p)
{
	eDebug("ADD Subtitle Page!!");
	m_pages.clear();
	m_pages.push_back(p);
	checkTiming();
}

void eSubtitleWidget::checkTiming()
{
	activatePage();
}

void eSubtitleWidget::activatePage()
{
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
		
		std::list<eDVBTeletextSubtitlePage>::iterator pi = m_pages.begin();
		if (pi == m_pages.end())
			painter.renderText(eRect(ePoint(0, 0), size()), "waiting for subtitles...", gPainter::RT_WRAP);
		else
		{
			const eDVBTeletextSubtitlePage &page = *pi;
			int elements = page.m_elements.size();
			int height = size().height();
			int size_per_element = height / (elements ? elements : 1);
			for (int i=0; i<elements; ++i)
			{
				painter.setForegroundColor(gRGB(0,0,0));
				painter.renderText(eRect(2, size_per_element * i + 2, size().width(), size_per_element), page.m_elements[i].m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
				painter.setForegroundColor(page.m_elements[i].m_color);
				painter.renderText(eRect(0, size_per_element * i, size().width(), size_per_element), page.m_elements[i].m_text, gPainter::RT_WRAP|gPainter::RT_VALIGN_CENTER|gPainter::RT_HALIGN_CENTER);
			}
		}
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}
