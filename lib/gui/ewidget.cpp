#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>

extern void dumpRegion(const gRegion &region);

eWidget::eWidget(eWidget *parent): m_parent(parent)
{
	m_vis = 0;
	m_desktop = 0;
	
	if (parent)
		m_vis = wVisShow;
	
	if (parent)
		parent->m_childs.push_back(this);
}

void eWidget::move(ePoint pos)
{
	m_position = pos;
	
	event(evtChangedPosition);
}

void eWidget::resize(eSize size)
{
	event(evtWillChangeSize, &size);
	event(evtChangedSize);
}

void eWidget::invalidate(const gRegion &region)
{
	gRegion res = /* region & */ m_visible_with_childs;
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
	m_vis &= ~wVisShow;

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
		/* destroy all childs */
	ePtrList<eWidget>::iterator i(m_childs.begin());
	while (i != m_childs.end())
	{
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
	
	painter.resetClip(region);
	event(evtPaint, &region, &painter);
	
	painter.moveOffset(-position());
}

int eWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		static int counter = 0x18;
		gPainter &painter = *(gPainter*)data2;
//		eDebug("eWidget::evtPaint %d", counter);
//		dumpRegion(*(gRegion*)data);
		painter.setBackgroundColor(gColor(++counter));
		painter.clear();
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

