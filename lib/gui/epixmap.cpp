#include <lib/gui/epixmap.h>
#include <lib/gdi/epng.h>
#include <lib/gui/ewidgetdesktop.h>

ePixmap::ePixmap(eWidget *parent)
        :eWidget(parent), m_alphatest(false), m_scale(false), m_have_border_color(false), m_border_width(0)
{
}

void ePixmap::setAlphatest(int alphatest)
{
	m_alphatest = alphatest;
	setTransparent(alphatest);
}

void ePixmap::setScale(int scale)
{
	if (m_scale != scale)
	{
		m_scale = scale;
		invalidate();
	}
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

void ePixmap::setBorderWidth(int pixel)
{
	m_border_width=pixel;
	invalidate();
}

void ePixmap::setBorderColor(const gRGB &color)
{
	m_border_color=color;
	m_have_border_color=true;
	invalidate();
}

void ePixmap::checkSize()
{
	/* when we have no pixmap, or a pixmap of different size, we need
	   to enable transparency in any case. */
	if (m_pixmap && m_pixmap->size() == size() && !m_alphatest)
		setTransparent(0);
	else
		setTransparent(1);
		/* fall trough. */
}

int ePixmap::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;

		eSize s(size());
		getStyle(style);

//	we don't clear the background before because of performance reasons.
//	when the pixmap is too small to fit the whole widget area, the widget is
//	transparent anyway, so the background is already painted.
//		eWidget::event(event, data, data2);

		gPainter &painter = *(gPainter*)data2;
		if (m_pixmap)
		{
			int flags = 0;
			if (m_alphatest == 0)
				flags = 0;
			else if (m_alphatest == 1)
				flags = gPainter::BT_ALPHATEST;
			else if (m_alphatest == 2)
				flags = gPainter::BT_ALPHABLEND;
			if (m_scale)
				painter.blitScale(m_pixmap, eRect(ePoint(0, 0), size()), eRect(), flags);
			else
				painter.blit(m_pixmap, ePoint(0, 0), eRect(), flags);
		}

		if (m_have_border_color)
			painter.setForegroundColor(m_border_color);

		if (m_border_width) {
			painter.fill(eRect(0, 0, s.width(), m_border_width));
			painter.fill(eRect(0, m_border_width, m_border_width, s.height()-m_border_width));
			painter.fill(eRect(m_border_width, s.height()-m_border_width, s.width()-m_border_width, m_border_width));
			painter.fill(eRect(s.width()-m_border_width, m_border_width, m_border_width, s.height()-m_border_width));
		}

		return 0;
	}
	case evtChangedPixmap:
		checkSize();
		invalidate();
		return 0;
	case evtChangedSize:
		checkSize();
			/* fall trough. */
	default:
		return eWidget::event(event, data, data2);
	}
}
