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
	if (!m_pixmap)
		return;

	ePtr<gDC> d = new gDC(m_pixmap);
	gPainter p(d, eRect());
	p.resetClip(eRect(ePoint(0,0), m_pixmap->size()));
	p.setBackgroundColor(color);
	p.clear();

	invalidate();
}

void eCanvas::fillRect(eRect rect, gRGB color)
{
	if (!m_pixmap)
		return;

	ePtr<gDC> dc = new gDC(m_pixmap);

	gPainter p(dc);
	p.resetClip(eRect(ePoint(0,0), m_pixmap->size()));
	p.setForegroundColor(color);
	p.fill(rect);

	invalidate(rect);
}

void eCanvas::writeText(eRect rect, gRGB fg, gRGB bg, gFont *font, const char *string, int flags)
{
	ePtr<gDC> dc = new gDC(m_pixmap);

	gPainter p(dc);
	p.setFont(font);
	p.resetClip(eRect(ePoint(0,0), m_pixmap->size()));
	p.setForegroundColor(fg);
	p.setBackgroundColor(bg);
	p.renderText(rect, string, flags);

	invalidate(rect);
}
