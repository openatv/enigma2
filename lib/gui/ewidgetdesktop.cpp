#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/ewidget.h>
#include <lib/base/ebase.h>

void eWidgetDesktop::addRootWidget(eWidget *root, int top)
{
	assert(!root->m_desktop);
	if (!top)
		m_root.push_back(root);
	else
		m_root.push_front(root);
	root->m_desktop = this;
}

void eWidgetDesktop::removeRootWidget(eWidget *root)
{
	m_root.remove(root);
}

void eWidgetDesktop::calcWidgetClipRegion(eWidget *widget, gRegion &parent_visible)
{
		/* start with our clip region, clipped with the parent's */
	if (widget->m_vis & eWidget::wVisShow)
	{
		widget->m_visible_region = widget->m_clip_region;
		widget->m_visible_region.moveBy(widget->position());
		widget->m_visible_region &= parent_visible; // in parent space!
			/* TODO: check transparency here! */
			/* remove everything this widget will contain from parent's visible list */
		parent_visible -= widget->m_visible_region; // will remove child regions too!

			/* now prepare for recursing to childs */
		widget->m_visible_region.moveBy(-widget->position());            // now in local space
	} else
		widget->m_visible_region = gRegion();

	widget->m_visible_with_childs = widget->m_visible_region;
	
	for (ePtrList<eWidget>::iterator i(widget->m_childs.begin()); i != widget->m_childs.end(); ++i)
		calcWidgetClipRegion(*i, widget->m_visible_region);
}

void eWidgetDesktop::recalcClipRegions()
{
	m_background_region = gRegion(eRect(ePoint(0, 0), m_screen_size));
	
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		calcWidgetClipRegion(*i, m_background_region);
}

void eWidgetDesktop::invalidate(const gRegion &region)
{
	if (m_timer && m_dirty_region.empty())
		m_timer->start(0, 1); // start singleshot redraw timer
	m_dirty_region |= region;
}

void eWidgetDesktop::setBackgroundColor(gRGB col)
{
	m_background_color = col;
	
		/* if there's something visible from the background, redraw it with the new color. */
	if (m_dc && m_background_region.valid() && !m_background_region.empty())
	{
			/* todo: split out "setBackgroundColor / clear"... maybe? */
		gPainter painter(m_dc);
		painter.resetClip(m_background_region);
		painter.setBackgroundColor(m_background_color);
		painter.clear();
	}
}

void eWidgetDesktop::setPalette(gPixmap &pm)
{
	ASSERT(m_dc);
	gPainter painter(m_dc);
	painter.setPalette(&pm);
}

void eWidgetDesktop::paint()
{
	gPainter painter(m_dc);
		/* walk all root windows. */
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		i->doPaint(painter, m_dirty_region);
	m_dirty_region &= m_background_region;
	
	painter.resetClip(m_dirty_region);
	painter.setBackgroundColor(m_background_color);
	painter.clear();
	
	painter.flush();
	
	m_dirty_region = gRegion();
}

void eWidgetDesktop::setDC(gDC *dc)
{
	m_dc = dc;
}

void eWidgetDesktop::setRedrawTask(eMainloop &ml)
{
	if (m_mainloop)
	{
		delete m_timer;
		m_timer = 0;
		m_mainloop = 0;
	}
	m_mainloop = &ml;
	m_timer = new eTimer(m_mainloop);
	CONNECT(m_timer->timeout, eWidgetDesktop::paint);
	
	if (!m_dirty_region.empty())
		m_timer->start(0, 1);
}

void eWidgetDesktop::makeCompatiblePixmap(gPixmap &pm)
{
	eDebug("widgetDesktop: make compatible pixmap of %p\n", &pm);
	if (!m_dc)
	{
		eWarning("eWidgetDesktop: no DC to make pixmap compatible with!");
		return;
	}
	eDebug("painter..");
	gPainter painter(m_dc);
	eDebug("merge!");
	painter.mergePalette(&pm);
	eDebug("gone!");
}

eWidgetDesktop::eWidgetDesktop(eSize size): m_screen_size(size), m_mainloop(0), m_timer(0)
{
}

eWidgetDesktop::~eWidgetDesktop()
{
}

