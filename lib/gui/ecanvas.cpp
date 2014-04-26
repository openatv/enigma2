#include <lib/gui/ecanvas.h>
#include <math.h>

eCanvas::eCanvas(eWidget *parent): ePixmap(parent)
{
}

void eCanvas::setSize(eSize size)
{
	/* Set accelNever to prevent hardware blitting to happen, which
	 * appears to yield very strange effects. */
	setPixmap(new gPixmap(size, 32, gPixmap::accelNever));
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

void eCanvas::drawLine(int x0, int y0, int x1, int y1, gRGB color)
{
	if (!m_pixmap)
		return;

	ePtr<gDC> dc = new gDC(m_pixmap);

	gPainter p(dc);
	p.resetClip(eRect(ePoint(0,0), m_pixmap->size()));
	p.setForegroundColor(color);
	p.line(ePoint(x0, y0), ePoint(x1, y1));

	invalidate(eRect(x0, y0, x1, y1).normalize());
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

void eCanvas::drawRotatedLine(int ox, int oy, int x0, int y0, int x1, int y1, float angle, bool cw, gRGB color)
{
	if (!m_pixmap)
		return;

	float a;
	int x_0, y_0, x_1, y_1, c;
	c = cw ? 1 : -1;
	a = angle * 0.017453292519943295769;

	x_0 = ox - (-x0 * cos(a) + y0 * sin(a) * c);
	y_0 = oy - (-x0 * sin(a) * c - y0 * cos(a));
	x_1 = ox - (-x1 * cos(a) + y1 * sin(a) * c);
	y_1 = oy - (-x1 * sin(a) * c - y1 * cos(a));

	eCanvas::drawLine(x_0, y_0, x_1, y_1, color);
}
