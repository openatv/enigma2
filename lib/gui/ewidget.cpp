#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>

extern void dumpRegion(const gRegion &region);

eWidget::eWidget(eWidget *parent): m_parent(parent ? parent->child() : 0)
{
	m_vis = 0;
	m_desktop = 0;
	
	if (m_parent)
		m_vis = wVisShow;
		
	if (m_parent)
	{
		m_parent->m_childs.push_back(this);
		m_parent->getStyle(m_style);
	}
}

void eWidget::move(ePoint pos)
{
	if (m_position == pos)
		return;
	
	m_position = pos;
	
		/* we invalidate before and after the move to
		   cause a correct redraw. The area which is
		   included both before and after isn't redrawn
		   twice because a invalidate doesn't immediately
		   redraws the region. */
	invalidate();
	event(evtChangedPosition);
	recalcClipRegionsWhenVisible();	
	invalidate();
}

void eWidget::resize(eSize size)
{
		/* same strategy as with move: we first check if
		   the size changed at all, and if it did, we
		   invalidate both the old and new area. 
		   TODO: check if either the old or new area
		   fits into the other completely, and invalidate
		   only once. */
	eSize old_size = m_size;
	event(evtWillChangeSize, &size);
	if (old_size == m_size)
		return;

	invalidate();
	event(evtChangedSize);
	recalcClipRegionsWhenVisible();	
	invalidate();
}

void eWidget::invalidate(const gRegion &region)
{
		/* we determine the area to redraw, and re-position this
		   area to the absolute position, and then call the
		   desktop's invalidate() with that, which adds this
		   area into the dirty region. */
	gRegion res = m_visible_with_childs;
	if (region.valid())
		res &= region;

	if (res.empty())
		return;
	
	eWidget *root = this;
	ePoint abspos = position();
	while (root && !root->m_desktop)
	{
		root = root->m_parent;
		assert(root);
		abspos += root->position();
	}
	
	res.moveBy(abspos);
//	eDebug("region to invalidate:");
//	dumpRegion(res);
	root->m_desktop->invalidate(res);
}

void eWidget::show()
{
	if (m_vis & wVisShow)
		return;
	
	m_vis |=  wVisShow;

		/* TODO: optimize here to only recalc what's required. possibly merge with hide. */
	eWidget *root = this;
	ePoint abspos = position();
	while (root && !root->m_desktop)
	{
		root = root->m_parent;
		assert(root);
		abspos += root->position();
	}

	root->m_desktop->recalcClipRegions();

	gRegion abs = m_visible_with_childs;
	abs.moveBy(abspos);
	root->m_desktop->invalidate(abs);
}

void eWidget::hide()
{
		/* TODO: when hiding an upper level widget, widgets get hidden but keep the */
		/* wVisShow flag (because when the widget is shown again, the widgets must */
		/* become visible again. */
	if (!(m_vis & wVisShow))
		return;
	m_vis &= ~wVisShow;
	
		/* this is a workaround to the above problem. when we are in the delete phase, 
		   don't hide childs. */
	if (!(m_parent || m_desktop))
		return;

		/* TODO: optimize here to only recalc what's required. possibly merge with show. */
	eWidget *root = this;
	ePoint abspos = position();
	while (root && !root->m_desktop)
	{
		root = root->m_parent;
		abspos += root->position();
	}
	assert(root->m_desktop);

	gRegion abs = m_visible_with_childs;
	abs.moveBy(abspos);

	root->m_desktop->recalcClipRegions();
	root->m_desktop->invalidate(abs);
}

void eWidget::destruct()
{
	if (m_parent)
		m_parent->m_childs.remove(this);
	delete this;
}

eWidget::~eWidget()
{
	hide();
	
	if (m_parent)
		m_parent->m_childs.remove(this);

	m_parent = 0;

		/* destroy all childs */
	ePtrList<eWidget>::iterator i(m_childs.begin());
	while (i != m_childs.end())
	{
		(*i)->m_parent = 0;
		delete *i;
		i = m_childs.erase(i);
	}
}

void eWidget::doPaint(gPainter &painter, const gRegion &r)
{
	if (m_visible_with_childs.empty())
		return;
	
	gRegion region = r;
			/* we were in parent's space, now we are in local space */
	region.moveBy(-position());
	
	painter.moveOffset(position());
		/* walk all childs */
	for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
		i->doPaint(painter, region);
	
		/* check if there's anything for us to paint */
	region &= m_visible_region;
	
	if (!region.empty())
	{
		painter.resetClip(region);
		event(evtPaint, &region, &painter);
	}
	
	painter.moveOffset(-position());
}

void eWidget::recalcClipRegionsWhenVisible()
{
	eWidget *t = this;
	do
	{
		if (!(t->m_vis & wVisShow))
			break;
		if (t->m_desktop)
		{
			t->m_desktop->recalcClipRegions();
			break;
		}
		t = t->m_parent;
		assert(t);
	} while(1);
}

int eWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		gPainter &painter = *(gPainter*)data2;
		
//		eDebug("eWidget::evtPaint");
//		dumpRegion(*(gRegion*)data);
		ePtr<eWindowStyle> style;
		if (!getStyle(style))
			style->paintBackground(painter, ePoint(0, 0), size());
		break;
	}
	case evtKey:
		break;
	case evtWillChangeSize:
		m_size = *static_cast<eSize*>(data);
		break;
	case evtChangedSize:
	{
		m_clip_region = gRegion(eRect(ePoint(0, 0),  m_size));
		break;
	}
	default:
		return -1;
	}
	return 0;
}

