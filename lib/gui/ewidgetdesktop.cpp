#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/ewidget.h>

void eWidgetDesktop::addRootWidget(eWidget *root, int top)
{
	assert(!root->m_desktop);
	if (!top)
		m_root.push_back(root);
	else
		m_root.push_front(root);
	root->m_desktop = this;
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
	gRegion screen = gRegion(eRect(ePoint(0, 0), m_screen_size));
	
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		calcWidgetClipRegion(*i, screen);
//	dumpRegion(screen);
}

void eWidgetDesktop::invalidate(const gRegion &region)
{
	m_dirty_region |= region;
}

void eWidgetDesktop::paint()
{
	gPainter painter(m_dc);
		/* walk all root windows. */
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		i->doPaint(painter, m_dirty_region);
	m_dirty_region = gRegion();
}

void eWidgetDesktop::setDC(gDC *dc)
{
	m_dc = dc;
}

eWidgetDesktop::eWidgetDesktop(eSize size): m_screen_size(size)
{
}

eWidgetDesktop::~eWidgetDesktop()
{
}

