#include <lib/gui/epixmap.h>
#include <lib/gdi/epng.h>
#include <lib/gui/ewidgetdesktop.h>

ePixmap::ePixmap(eWidget *parent): eWidget(parent)
{
}

void ePixmap::setPixmap(gPixmap *pixmap)
{
	m_pixmap = pixmap;
	event(evtChangedPixmap);
}

void ePixmap::setPixmapFromFile(const char *filename)
{
	loadPNG(m_pixmap, filename);
	
		// TODO
	getDesktop()->makeCompatiblePixmap(*m_pixmap);
	event(evtChangedPixmap);
}

int ePixmap::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		
		getStyle(style);
		
		eWidget::event(event, data, data2);
		
		gPainter &painter = *(gPainter*)data2;
		if (m_pixmap)
			painter.blit(m_pixmap, ePoint(0, 0));
		
		return 0;
	}
	case evtChangedPixmap:
		invalidate();
		return 0;
	default:
		return eWidget::event(event, data, data2);
	}
}
