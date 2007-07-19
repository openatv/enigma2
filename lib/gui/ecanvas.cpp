#include <lib/gui/ecanvas.h>

eCanvas::eCanvas(eWidget *parent): ePixmap(parent)
{
}

void eCanvas::setSize(eSize size)
{
	setPixmap(new gPixmap(size, 32)); /* TODO: do we need 8bit surfaces? */
}

void eCanvas::clear(gRGB color)
{
#if 0
	if (!m_pixmap)
		return;

	ePtr<gDC> d = new gDC(m_pixmap);
	gPainter p(d, eRect());
	p.setBackgroundColor(color);
	p.clear();

	invalidate();
#endif
}

void eCanvas::fillRect(eRect rect, gRGB color)
{
	eDebug("draw into canvas... %d %d, %d %d", rect.left(), rect.top(), rect.width(), rect.height());
#if 0
	ePtr<gDC> d = new gDC(m_pixmap);
	gPainter p(d, eRect());
	p.setForegroundColor(color);
	p.fill(rect);

	invalidate(rect);
#endif
}
