#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>

extern void dumpRegion(const gRegion &region);

eWidget::eWidget(eWidget *parent): m_animation(this), m_parent(parent ? parent->child() : 0)
{
	m_vis = 0;
	m_layer = 0;
	m_desktop = 0;
	m_have_background_color = 0;
	m_z_position = 0;
	m_lowered = 0;
	m_client_offset = eSize(0, 0);
	if (m_parent)
		m_vis = wVisShow;
	if (m_parent)
	{
		insertIntoParent();
		m_parent->getStyle(m_style);
	}

	m_current_focus = 0;
	m_focus_owner = 0;
	m_notify_child_on_position_change = 1;
}

void eWidget::move(ePoint pos)
{
	pos = pos + m_client_offset;
	if (m_position == pos)
		return;

			/* ?? what about native move support? */
	invalidate();

	m_position = pos;
	event(evtChangedPosition);
	if (m_notify_child_on_position_change)
		for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
			i->event(evtParentChangedPosition);
		recalcClipRegionsWhenVisible();
		/* try native move if supported. */
	if ((m_vis & wVisShow) && ((!m_desktop) || m_desktop->movedWidget(this)))
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
	eSize old_offset = m_client_offset;
	m_client_size = size;
	m_client_offset = eSize(0, 0);
	event(evtWillChangeSize, &size, &m_client_offset);
	if (old_size == m_size)
		return;
	move(position() - old_offset);
	invalidate();
	event(evtChangedSize);

	if (m_notify_child_on_position_change)
		for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
			i->event(evtParentChangedPosition); /* position/size is the same here */

	recalcClipRegionsWhenVisible();	invalidate();
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
	int target_layer = m_layer;

	while (root && !root->m_desktop)
	{
		root = root->m_parent;
		if (!root)
		{
			/*
			 * Somewhere in out ancestry is a widget without a parent.
			 * This means we cannot find our desktop, so
			 * we won't be able to invalidate the requested region.
			 */
			return;
		}
		if (root->m_layer != -1)
			target_layer = root->m_layer;
		abspos += root->position();
	}
	res.moveBy(abspos);
//	eDebug("[eWidget] region to invalidate:");
//	dumpRegion(res);
	root->m_desktop->invalidate(res, this, target_layer);
}

void eWidget::show()
{
	if (m_vis & wVisShow)
		return;

	m_vis |= wVisShow;
//	eDebug("[eWidget] show widget %p", this);
	notifyShowHide();

		/* TODO: optimize here to only recalc what's required. possibly merge with hide. */
	eWidget *root = this;
	ePoint abspos = position();
	int target_layer = m_layer;

	while (root && !root->m_desktop)
	{
		root = root->m_parent;
		if (!root)
		{
				/* oops: our root widget does not have a desktop associated.
					probably somebody already erased the root, but tries some
					operations on a child window.
									ignore them for now. */
			/* ASSERT(root); */
			return;
		}
		if (root->m_layer != -1)
			target_layer = root->m_layer;
		abspos += root->position();
	}

	root->m_desktop->recalcClipRegions(root);

	gRegion abs = m_visible_with_childs;
	abs.moveBy(abspos);
	root->m_desktop->invalidate(abs, this, target_layer);
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
	notifyShowHide();

		/* TODO: optimize here to only recalc what's required. possibly merge with show. */
	eWidget *root = this;
	ePoint abspos = position();
	while (root && !root->m_desktop)
	{
		root = root->m_parent;
		if (!root)
			return;
		abspos += root->position();
	}
	ASSERT(root->m_desktop);

	gRegion abs = m_visible_with_childs;
	abs.moveBy(abspos);

	root->m_desktop->recalcClipRegions(root);
	root->m_desktop->invalidate(abs);
}

void eWidget::raise()
{
	if (m_lowered <= 0) return;
	m_lowered--;
	setZPosition(m_z_position + 1);
}

void eWidget::lower()
{
	m_lowered++;
	setZPosition(m_z_position - 1);
}

void eWidget::destruct()
{
	if (m_parent)
		m_parent->m_childs.remove(this);
	delete this;
}

void eWidget::setBackgroundColor(const gRGB &col)
{
	m_background_color = col;
	m_have_background_color = 1;
}

void eWidget::clearBackgroundColor()
{
	m_have_background_color = 0;
}

void eWidget::setZPosition(int z)
{
	m_z_position = z;
	if (!m_parent)
		return;
	m_parent->m_childs.remove(this);
	insertIntoParent(); /* now at the new Z position */
}

void eWidget::setTransparent(int transp)
{
	if (isTransparent() != transp)
	{
		if (transp)
			m_vis |= wVisTransparent;
		else
			m_vis &=~wVisTransparent;
		recalcClipRegionsWhenVisible();
	}
}

ePoint eWidget::getAbsolutePosition()
{
	eWidget *root = this;
	ePoint abspos = position();

	while (root && !root->m_desktop)
	{
		root = root->m_parent;
		if (!root)
		{
			/*
			 * Somewhere in out ancestry is a widget without a parent.
			 * This means we cannot find our desktop, so
			 * we won't be able to get our absolute position.
			 */
			break;
		}
		abspos += root->position();
	}

	return abspos;
}

void eWidget::mayKillFocus()
{
	setFocus(0);
		/* when we have the focus, remove it first. */
	if (m_focus_owner)
		m_focus_owner->setFocus(0);
}

eWidget::~eWidget()
{
	hide();
	if (m_parent)
		m_parent->m_childs.remove(this);

	m_parent = 0;

		/* tell all childs that the parent is not anymore existing */
	ePtrList<eWidget>::iterator i(m_childs.begin());
	while (i != m_childs.end())
	{
		(*i)->parentRemoved();
		i = m_childs.erase(i);
	}
}

void eWidget::insertIntoParent()
{
	ePtrList<eWidget>::iterator i = m_parent->m_childs.begin();
	for(;;)
	{
		if ((i == m_parent->m_childs.end()) || (i->m_z_position > m_z_position))
		{
			m_parent->m_childs.insert(i, this);
			return;
		}
		++i;
	}
}

void eWidget::doPaint(gPainter &painter, const gRegion &r, int layer)
{
	if (m_visible_with_childs.empty())
		return;
	gRegion region = r, childs = r;
			/* we were in parent's space, now we are in local space */
	region.moveBy(-position());
	painter.moveOffset(position());
		/* check if there's anything for us to paint */
	if (layer == m_layer)
	{
		region &= m_visible_region;
		if (!region.empty())
		{
			painter.resetClip(region);
			event(evtPaint, &region, &painter);
		}
	}

	childs.moveBy(-position());
		/* walk all childs */
	for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
		i->doPaint(painter, childs, layer);
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
			t->m_desktop->recalcClipRegions(t);
			break;
		}
		t = t->m_parent;
		ASSERT(t);
	} while(1);
}

void eWidget::parentRemoved()
{
	m_parent = 0;
}

int eWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		gPainter &painter = *(gPainter*)data2;
	//		eDebug("[eWidget] evtPaint");
//		dumpRegion(*(gRegion*)data);
		if (!isTransparent())
		{
			if (!m_have_background_color)
			{
				ePtr<eWindowStyle> style;
				if (!getStyle(style))
					style->paintBackground(painter, ePoint(0, 0), size());
			} else
			{
				painter.setBackgroundColor(m_background_color);
				painter.clear();
			}
		} else
		{
			eWidget *w = this;
			while (w && !w->m_have_background_color)
				w = w->m_parent;

			if (w)
				painter.setBackgroundColor(w->m_background_color);
		}
		break;
	}
	case evtKey:
		break;
	case evtWillChangeSize:
		m_size = *static_cast<eSize*>(data);
		break;
	case evtChangedSize:
		m_clip_region = gRegion(eRect(ePoint(0, 0),  m_size));
		break;
	case evtParentChangedPosition:
		for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
			i->event(evtParentChangedPosition);
		break;
	case evtFocusGot:
		m_focus_owner = (eWidget*)data;
		break;
	case evtFocusLost:
		m_focus_owner = 0;
		break;
	default:
		return -1;
	}
	return 0;
}

void eWidget::setFocus(eWidget *focus)
{
	if (m_current_focus)
		m_current_focus->event(evtFocusLost, this);
	m_current_focus = focus;

	if (m_current_focus)
		m_current_focus->event(evtFocusGot, this);
}

void eWidget::notifyShowHide()
{
	event(evtParentVisibilityChanged);
	for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
		i->notifyShowHide();
}
