#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gui/ewindow.h>
#include <lib/gui/ewindowstyle.h>

DEFINE_REF(eWindowStyleSimple);

eWindowStyleSimple::eWindowStyleSimple()
{
	m_border_left = m_border_right = m_border_top = m_border_bottom = 10;
}

void eWindowStyleSimple::handleNewSize(eWindow *wnd, const eSize &size)
{
	eDebug("handle new size: %d x %d", size.width(), size.height());
	
	eWidget *child = wnd->child();
	
	wnd->m_clip_region = eRect(ePoint(0, 0), size);
	
	child->move(ePoint(m_border_left, m_border_top));
	child->resize(eSize(size.width() - m_border_left - m_border_right, size.height() - m_border_top - m_border_bottom));
}
