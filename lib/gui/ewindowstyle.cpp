#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewindowstyle.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

eWindowStyle::~eWindowStyle() {}

DEFINE_REF(eWindowStyleManager);

ePtr<eWindowStyleManager> NewWindowStylePtr(void)
{
	ePtr<eWindowStyleManager> ptr;
	eWindowStyleManager::getInstance(ptr);
	return ptr;
}

eWindowStyleManager::eWindowStyleManager()
{
	m_instance = this;
}

eWindowStyleManager::~eWindowStyleManager()
{
	m_instance = 0;
}

void eWindowStyleManager::getStyle(int style_id, ePtr<eWindowStyle> &style)
{
	std::map<int, ePtr<eWindowStyle> >::iterator it = m_current_style.find(style_id);
	if (it != m_current_style.end())
		style = it->second;
	else
		eDebug("[eWindowStyleManager] getStyle(style_id=%d): NOT FOUND", style_id);
}

void eWindowStyleManager::setStyle(int style_id, eWindowStyle *style)
{
	m_current_style[style_id] = style;
}

eWindowStyleManager *eWindowStyleManager::m_instance;

DEFINE_REF(eWindowStyleSimple);

eWindowStyleSimple::eWindowStyleSimple()
{
	m_border_left = m_border_right = m_border_bottom = 2;
	m_border_top = 30;

	m_fnt = new gFont("Regular", 25);

	m_border_color_tl = gColor(0x1f);
	m_border_color_br = gColor(0x14);
	m_title_color_back = gColor(0x20);
	m_title_color = gColor(0x2f);
	m_background_color = gColor(0x19);
}

void eWindowStyleSimple::handleNewSize(eWindow *wnd, eSize &size, eSize &offset)
{
//	eDebug("[eWindowStyleSimple] handle new size: %d x %d", size.width(), size.height());

	eWidget *child = wnd->child();

	wnd->m_clip_region = eRect(ePoint(0, 0), size);

	child->move(ePoint(m_border_left, m_border_top));
	child->resize(eSize(size.width() - m_border_left - m_border_right, size.height() - m_border_top - m_border_bottom));
}

void eWindowStyleSimple::paintWindowDecoration(eWindow *wnd, gPainter &painter, const std::string &title)
{
	painter.setForegroundColor(m_title_color_back);
	painter.fill(eRect(2, 2, wnd->size().width() - 4, m_border_top - 4));
	painter.setBackgroundColor(m_title_color_back);
	painter.setForegroundColor(m_title_color);
	painter.setFont(m_fnt);
	painter.renderText(eRect(3, 3, wnd->size().width() - 6, m_border_top - 6), title);

	eRect frame(ePoint(0, 0), wnd->size());

	painter.setForegroundColor(m_background_color);
	painter.line(frame.topLeft1(), frame.topRight1());
	painter.line(frame.topLeft1(), frame.bottomLeft1());
	painter.setForegroundColor(m_border_color_tl);
	painter.line(frame.topLeft1()+eSize(1,1), frame.topRight1()+eSize(0,1));
	painter.line(frame.topLeft1()+eSize(1,1), frame.bottomLeft1()+eSize(1,0));

	painter.setForegroundColor(m_border_color_br);
	painter.line(frame.bottomLeft()+eSize(1,-1), frame.bottomRight()+eSize(0,-1));
	painter.line(frame.topRight1()+eSize(-1,1), frame.bottomRight1()+eSize(-1, 0));
	painter.line(frame.bottomLeft()+eSize(1,-2), frame.bottomRight()+eSize(0,-2));
	painter.line(frame.topRight1()+eSize(-0,1), frame.bottomRight1()+eSize(-0, 0));
}

void eWindowStyleSimple::paintBackground(gPainter &painter, const ePoint &offset, const eSize &size)
{
	painter.setBackgroundColor(m_background_color);
	painter.clear();
}

void eWindowStyleSimple::setStyle(gPainter &painter, int what)
{
	switch (what)
	{
	case styleLabel:
		painter.setForegroundColor(gColor(0x1F));
		break;
	case styleListboxSelected:
		painter.setForegroundColor(gColor(0x1F));
		painter.setBackgroundColor(gColor(0x1A));
		break;
	case styleListboxNormal:
		painter.setForegroundColor(gColor(0x1C));
		painter.setBackgroundColor(m_background_color);
		break;
	case styleListboxMarked:
		painter.setForegroundColor(gColor(0x2F));
		painter.setBackgroundColor(gColor(0x2A));
		break;
	case styleListboxMarkedAndSelected:
		painter.setForegroundColor(gColor(0x3F));
		painter.setBackgroundColor(gColor(0x3A));
		break;
	}
}

void eWindowStyleSimple::drawFrame(gPainter &painter, const eRect &frame, int what)
{
	gColor c1, c2;
	switch (what)
	{
	case frameButton:
		c1 = m_border_color_tl;
		c2 = m_border_color_br;
		break;
	case frameListboxEntry:
		c1 = m_border_color_br;
		c2 = m_border_color_tl;
		break;
	}

	painter.setForegroundColor(c2);
	painter.line(frame.topLeft1(), frame.topRight1());
	painter.line(frame.topRight1(), frame.bottomRight1());
	painter.setForegroundColor(c1);
	painter.line(frame.bottomRight1(), frame.bottomLeft1());
	painter.line(frame.bottomLeft1(), frame.topLeft1());
}

RESULT eWindowStyleSimple::getFont(int what, ePtr<gFont> &fnt)
{
	fnt = 0;
	switch (what)
	{
	case fontStatic:
		fnt = new gFont("Regular", 12);
		break;
	case fontButton:
		fnt = new gFont("Regular", 20);
		break;
	case fontTitlebar:
		fnt = new gFont("Regular", 25);
		break;
	default:
		return -1;
	}
	return 0;
}

eAutoInitPtr<eWindowStyleManager> init_eWindowStyleManager(eAutoInitNumbers::skin, "eWindowStyleManager");
