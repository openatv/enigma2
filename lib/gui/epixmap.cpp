#include <lib/gui/epixmap.h>
#include <lib/gdi/epng.h>
#include <lib/gui/ewidgetdesktop.h>

ePixmap::ePixmap(eWidget *parent)
	:eWidget(parent), m_alphatest(false)
{
}

void ePixmap::setAlphatest(bool alphatest)
{
	m_alphatest = alphatest;
	setTransparent(alphatest);
}

void ePixmap::setPixmap(gPixmap *pixmap)
{
	m_pixmap = pixmap;
	event(evtChangedPixmap);
}

void ePixmap::setPixmap(ePtr<gPixmap> &pixmap)
{
	m_pixmap = pixmap;
	event(evtChangedPixmap);
}

void ePixmap::setPixmapFromFile(const char *filename)
{
	loadPNG(m_pixmap, filename);
	
	if (!m_pixmap)
	{
		eDebug("ePixmap::setPixmapFromFile: loadPNG failed");
		return;
	}
	
		// TODO: This only works for desktop 0
	getDesktop(0)->makeCompatiblePixmap(*m_pixmap);
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
		
//		eWidget::event(event, data, data2);
		
		gPainter &painter = *(gPainter*)data2;
		if (m_pixmap)
			painter.blit(m_pixmap, ePoint(0, 0), eRect(), m_alphatest?gPainter::BT_ALPHATEST:0);
		
		return 0;
	}
	case evtChangedPixmap:
		invalidate();
		return 0;
	default:
		return eWidget::event(event, data, data2);
	}
}
