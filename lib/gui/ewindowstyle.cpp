#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewindowstyle.h>


eWindowStyle::~eWindowStyle() {}

DEFINE_REF(eWindowStyleSimple);

eWindowStyleSimple::eWindowStyleSimple()
{
	m_border_left = m_border_right = m_border_bottom = 1;
	m_border_top = 30;

	m_fnt = new gFont("Arial", 25);
	
	m_border_color_tl = gColor(0x14);
	m_border_color_br = gColor(0x1c);
	m_title_color_back = gColor(0x20);
	m_title_color = gColor(0x2f);
	m_background_color = gColor(0x18);
}

void eWindowStyleSimple::handleNewSize(eWindow *wnd, const eSize &size)
{
	eDebug("handle new size: %d x %d", size.width(), size.height());
	
	eWidget *child = wnd->child();
	
	wnd->m_clip_region = eRect(ePoint(0, 0), size);
	
	child->move(ePoint(m_border_left, m_border_top));
	child->resize(eSize(size.width() - m_border_left - m_border_right, size.height() - m_border_top - m_border_bottom));
}

void eWindowStyleSimple::paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title)
{
	painter.setBackgroundColor(m_title_color_back);
	painter.setForegroundColor(m_title_color);
	painter.clear();
	painter.setFont(m_fnt);
	painter.renderText(eRect(1, 1, wnd->size().width() - 2, m_border_top - 2), title);

	eRect frame(ePoint(0, 0), wnd->size());
	painter.setForegroundColor(m_border_color_tl);
	painter.line(frame.topLeft1(), frame.topRight1());
	painter.line(frame.topRight1(), frame.bottomRight1());
	painter.setForegroundColor(m_border_color_br);
	painter.line(frame.bottomRight1(), frame.bottomLeft1());
	painter.line(frame.bottomLeft1(), frame.topLeft1());
}

void eWindowStyleSimple::paintBackground(gPainter &painter, const ePoint &offset, const eSize &size)
{
	painter.setBackgroundColor(m_background_color);
	painter.clear();
}

void eWindowStyleSimple::setForegroundStyle(gPainter &painter)
{
	painter.setForegroundColor(gColor(0x1F));
}

void eWindowStyleSimple::drawButtonFrame(gPainter &painter, const eRect &frame)
{
	painter.setForegroundColor(m_border_color_tl);
	painter.line(frame.topLeft1(), frame.topRight1());
	painter.line(frame.topRight1(), frame.bottomRight1());
	painter.setForegroundColor(m_border_color_br);
	painter.line(frame.bottomRight1(), frame.bottomLeft1());
	painter.line(frame.bottomLeft1(), frame.topLeft1());
}
