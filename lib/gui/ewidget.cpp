#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>

extern void dumpRegion(const gRegion &region);

eWidget::eWidget(eWidget* parent) : m_animation(this), m_parent(parent ? parent->child() : 0) {
	m_gradient_set = false;
	m_gradient_direction = 0;
	m_vis = 0;
	m_layer = 0;
	m_desktop = 0;
	m_z_position = 0;
	m_lowered = 0;
	m_client_offset = eSize(0, 0);
	if (m_parent)
		m_vis = wVisShow;
	if (m_parent) {
		insertIntoParent();
		m_parent->getStyle(m_style);
	}

	m_current_focus = 0;
	m_focus_owner = 0;
	m_notify_child_on_position_change = 1;
	m_cornerRadius = 0;
	m_cornerRadiusEdges = 0;
	m_have_border_color = false;
	m_border_width = 0;
	m_padding = eRect(0, 0, 0, 0);
	m_tag = 0;
	m_stack = nullptr;
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
	if (m_stack)
		m_stack->invalidateChilds();
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
	if (m_cornerRadius > 0)
	{
		const int w = size.width();
		const int h = size.height();
		// eDebug("[eWidget] resize m_cornerRadius %d / w %d / h %d / w half %d / w even %d", m_cornerRadius, w, h, w / 2, w % 2);
		if (w > -1 && w == h && (w % 2 != 0) && m_cornerRadius >= w / 2)
		{
			size = eSize(w - 1, h - 1);
			m_client_size = size;
		}
	}
	event(evtWillChangeSize, &size, &m_client_offset);
	if (old_size == m_size)
		return;
	move(position() - old_offset);
	invalidate();
	event(evtChangedSize);

	if (m_notify_child_on_position_change)
		for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
			i->event(evtParentChangedPosition); /* position/size is the same here */

	recalcClipRegionsWhenVisible();
	invalidate();
	if (m_stack)
		m_stack->invalidateChilds();
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
	if (root && root->m_desktop)
	{
		root->m_desktop->invalidate(res, this, target_layer);
	}
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

	if (root && root->m_desktop)
	{
		root->m_desktop->recalcClipRegions(root);

		gRegion abs = m_visible_with_childs;
		abs.moveBy(abspos);
		root->m_desktop->invalidate(abs, this, target_layer);
	}
	if (m_stack)
		m_stack->invalidateChilds();
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

	if (root && root->m_desktop)
	{
		gRegion abs = m_visible_with_childs;
		abs.moveBy(abspos);

		root->m_desktop->recalcClipRegions(root);
		root->m_desktop->invalidate(abs);
	}
	if (m_stack)
		m_stack->invalidateChilds();
}

void eWidget::raise()
{
	if (m_lowered <= 0)
		return;
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
	m_have_background_color = true;
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
			m_vis &= ~wVisTransparent;
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
	for (;;)
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
		if (!t->m_parent)
		{
			eLogNoNewLineStart(lvlError, "[eWidget] RecalcClipRegions for widget at (%d,%d)=>(%d,%d).", this->position().x(), this->position().y(), this->size().width(), this->size().height());
			eLogNoNewLine(lvlError, "Top level parent at (%d,%d)=>(%d,%d) has no desktop", t->position().x(), t->position().y(), t->size().width(), t->size().height());
		}
		t = t->m_parent;
	} while (t);
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
		gPainter &painter = *(gPainter *)data2;
		// eDebug("[eWidget] evtPaint");
		// dumpRegion(*(gRegion*)data);
		if (!isTransparent())
		{
			bool drawborder = (m_have_border_color && m_border_width);

			if (m_gradient_set)
				painter.setGradient(m_gradient_colors, m_gradient_direction, m_gradient_alphablend);
			if (m_have_background_color)
				painter.setBackgroundColor(m_background_color);
			const int r = getCornerRadius();
			if (r || m_gradient_set)
			{
				if (r)
					painter.setRadius(r, m_cornerRadiusEdges);
				if (r && drawborder)
				{

					if(!m_gradient_set && m_alphaBlend) // use new drawRectangle only if no gradient and alphaBlend because otherwise we have a problem with eVideoWidget
					{
						painter.setBackgroundColor(m_have_background_color ? m_background_color : gRGB(0, 0, 0));
						painter.setBorder(m_border_color, m_border_width);
						painter.drawRectangle(eRect(ePoint(0, 0), size()), m_alphaBlend);
					}
					else
					{
						painter.setBackgroundColor(m_border_color);
						painter.drawRectangle(eRect(ePoint(0, 0), size()));
						if (r)
							painter.setRadius(r, m_cornerRadiusEdges);
						painter.setBackgroundColor(m_have_background_color ? m_background_color : gRGB(0, 0, 0));
						painter.drawRectangle(eRect(m_border_width, m_border_width, size().width() - m_border_width * 2, size().height() - m_border_width * 2));
					}

					drawborder = false;
				}
				else
					painter.drawRectangle(eRect(ePoint(0, 0), size()), !m_gradient_set && m_alphaBlend);
			}
			else
			{
				if (!m_have_background_color)
				{
					ePtr<eWindowStyle> style;
					if (!getStyle(style))
						style->paintBackground(painter, ePoint(0, 0), size());
				}
				else
				{
					if(m_alphaBlend)
					{
						if(drawborder)
							painter.setBorder(m_border_color, m_border_width);
						painter.drawRectangle(eRect(ePoint(0, 0), size()), true);
						drawborder = false;
					}
					else
						painter.clear();
				}
			}
			if (drawborder)
			{
				painter.setForegroundColor(m_border_color);
				eSize s(size());
				painter.fill(eRect(0, 0, s.width(), m_border_width));
				painter.fill(eRect(0, m_border_width, m_border_width, s.height() - m_border_width));
				painter.fill(eRect(m_border_width, s.height() - m_border_width, s.width() - m_border_width, m_border_width));
				painter.fill(eRect(s.width() - m_border_width, m_border_width, m_border_width, s.height() - m_border_width));
			}
		}
		else
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
		m_size = *static_cast<eSize *>(data);
		break;
	case evtChangedSize:
		m_clip_region = gRegion(eRect(ePoint(0, 0), m_size));
		break;
	case evtParentChangedPosition:
		for (ePtrList<eWidget>::iterator i(m_childs.begin()); i != m_childs.end(); ++i)
			i->event(evtParentChangedPosition);
		break;
	case evtFocusGot:
		m_focus_owner = (eWidget *)data;
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

void eWidget::setBackgroundGradient(const gRGB &startcolor, const gRGB &midcolor, const gRGB &endcolor, uint8_t direction, bool alphablend)
{
	m_gradient_colors = {startcolor, midcolor, endcolor};
	m_gradient_direction = direction;
	m_gradient_alphablend = alphablend;
	m_gradient_set = true;
	invalidate();
}

void eWidget::setCornerRadius(int radius, uint8_t edges)
{
	m_cornerRadius = radius;
	m_cornerRadiusEdges = edges;
	invalidate();
}

int eWidget::getCornerRadius()
{
	int r = m_cornerRadius;
	if (r)
	{
		const int w = m_size.width();
		const int h = m_size.height();
		if (w && h)
		{
			int minDimension = (w < h) ? w : h;
			if (r > minDimension / 2)
			{
				r = minDimension / 2;
			}
		}
	}
	return r;
}
