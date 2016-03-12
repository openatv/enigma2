#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/ewidget.h>
#include <lib/base/ebase.h>
#include <lib/gdi/grc.h>

extern void dumpRegion(const gRegion &region);

void eWidgetDesktop::addRootWidget(eWidget *root)
{
	ASSERT(!root->m_desktop);

	int invert_sense = 0;
		/* buffered mode paints back-to-front, while immediate mode is front-to-back. */
	if (m_comp_mode == cmBuffered)
		invert_sense = 1;

	ePtrList<eWidget>::iterator insert_position = m_root.begin();

	for (;;)
	{
		if ((insert_position == m_root.end()) || (invert_sense ^ (insert_position->m_z_position < root->m_z_position)))
		{
			m_root.insert(insert_position, root);
			break;
		}
		++insert_position;
	}

	root->m_desktop = this;

		/* the creation will be postponed. */
	for (int i = 0; i < MAX_LAYER; ++i)
		root->m_comp_buffer[i] = 0;
}

void eWidgetDesktop::removeRootWidget(eWidget *root)
{
	if (m_comp_mode == cmBuffered)
	{
		for (int i = 0; i < MAX_LAYER; ++i)
			removeBufferForWidget(root, i);
	}

	m_root.remove(root);
}

int eWidgetDesktop::movedWidget(eWidget *root)
{
	if (m_comp_mode != cmBuffered)
		return -1; /* native move not supported */

	for (int i = 0; i < MAX_LAYER; ++i)
	{
		if (root->m_comp_buffer[i])
			root->m_comp_buffer[i]->m_position = root->position();
//		redrawComposition(0);
	}

	return 0; /* native move ok */
}

void eWidgetDesktop::calcWidgetClipRegion(eWidget *widget, gRegion &parent_visible)
{
		/* start with our clip region, clipped with the parent's */
	if (widget->m_vis & eWidget::wVisShow)
	{
		widget->m_visible_region = widget->m_clip_region;
		widget->m_visible_region.moveBy(widget->position());
		widget->m_visible_region &= parent_visible; // in parent space!

		if (!widget->isTransparent())
				/* remove everything this widget will contain from parent's visible list, unless widget is transparent. */
			parent_visible -= widget->m_visible_region; // will remove child regions too!

			/* now prepare for recursing to childs */
		widget->m_visible_region.moveBy(-widget->position());            // now in local space
	} else
		widget->m_visible_region = gRegion();

	widget->m_visible_with_childs = widget->m_visible_region;

			/* add childs in reverse (Z) order - we're going from front-to-bottom here. */
	ePtrList<eWidget>::iterator i(widget->m_childs.end());

	for (;;)
	{
		if (i != widget->m_childs.end())
		{
			if (i->m_vis & eWidget::wVisShow)
				calcWidgetClipRegion(*i, widget->m_visible_region);
			else
				clearVisibility(*i);
		}
		if (i == widget->m_childs.begin())
			break;
		--i;
	}
}

void eWidgetDesktop::recalcClipRegions(eWidget *root)
{
	if (m_comp_mode == cmImmediate)
	{
		gRegion background_before = m_screen.m_background_region;

		m_screen.m_background_region = gRegion(eRect(ePoint(0, 0), m_screen.m_screen_size));

		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		{
			if (!(i->m_vis & eWidget::wVisShow))
			{
				clearVisibility(i);
				continue;
			}

			gRegion visible_before = i->m_visible_with_childs;

			calcWidgetClipRegion(*i, m_screen.m_background_region);

			gRegion redraw = (i->m_visible_with_childs - visible_before) | (visible_before - i->m_visible_with_childs);

			redraw.moveBy(i->position());

			invalidate(redraw);
		}

		gRegion redraw = (background_before - m_screen.m_background_region) | (m_screen.m_background_region - background_before);
		invalidate(redraw);
	} else if (m_comp_mode == cmBuffered)
	{
		if (!(root->m_vis & eWidget::wVisShow))
		{
			clearVisibility(root);
			for (int i = 0; i < MAX_LAYER; ++i)
				removeBufferForWidget(root, i);
			return;
		}

		for (int i = 0; i < MAX_LAYER; ++i)
		{
			eWidgetDesktopCompBuffer *comp = root->m_comp_buffer[i];

					/* TODO: layers might not be required to have the screen size, for memory reasons. */
			if ((i == 0 && !comp) || (comp && (root->size() != comp->m_screen_size)))
				createBufferForWidget(root, 0);

			comp = root->m_comp_buffer[i]; /* it might have changed. */

			if (!comp)
				continue;  /* WAIT, don't we need to invalidate,whatever */

					/* CHECKME: don't we need to recalculate everything? after all, our buffer has changed and is likely to be cleared */
		 	gRegion visible_before = root->m_visible_with_childs;

			comp->m_background_region = gRegion(eRect(comp->m_position, comp->m_screen_size));

			gRegion visible_new = root->m_visible_with_childs - visible_before;
			gRegion visible_lost = visible_before - root->m_visible_with_childs;
			visible_new.moveBy(root->position());
			visible_lost.moveBy(root->position());

			invalidate(visible_new, root, i);
			invalidate(visible_lost, root, i);

			calcWidgetClipRegion(root, comp->m_background_region);
		}
	}
}

void eWidgetDesktop::invalidateWidgetLayer(const gRegion &region, const eWidget *widget, int layer)
{
	if (m_comp_mode == cmImmediate)
	{
		invalidate(region);
		return;
	}
	eWidgetDesktopCompBuffer *comp = widget->m_comp_buffer[layer];
	if (comp)
		comp->m_dirty_region |= region;
}

void eWidgetDesktop::invalidateWidget(const gRegion &region, const eWidget *widget, int layer)
{
	if (m_comp_mode == cmImmediate)
	{
		invalidate(region);
		return;
	}

	if (!(widget->m_vis & eWidget::wVisShow))
		return;

	gRegion mregion = region;
	if (layer == -1)
		for (int layer = 0; layer < MAX_LAYER; ++layer)
			invalidateWidgetLayer(mregion, widget, layer);
	else
		invalidateWidgetLayer(mregion, widget, layer);
}

void eWidgetDesktop::invalidate(const gRegion &region, const eWidget *widget, int layer)
{
	if (region.empty())
		return;

	if (m_timer && !m_require_redraw)
		m_timer->start(0, 1); // start singleshot redraw timer

	m_require_redraw = 1;

	if (m_comp_mode == cmImmediate)
	{
			/* in immediate mode, we don't care for widget and layer, we use the topmost. */
		m_screen.m_dirty_region |= region;
	} else
	{
		if (!widget)
			for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
				invalidateWidget(region, i);
		else
			invalidateWidget(region, widget, layer);
	}
}

void eWidgetDesktop::setBackgroundColor(eWidgetDesktopCompBuffer *comp, gRGB col)
{
	comp->m_background_color = col;

		/* if there's something visible from the background, redraw it with the new color. */
	if (comp->m_dc && comp->m_background_region.valid() && !comp->m_background_region.empty())
	{
			/* todo: split out "setBackgroundColor / clear"... maybe? */
		gPainter painter(comp->m_dc);
		painter.resetClip(comp->m_background_region);
		painter.setBackgroundColor(comp->m_background_color);
		painter.clear();
	}
}

void eWidgetDesktop::setBackgroundColor(gRGB col)
{
	setBackgroundColor(&m_screen, col);

	if (m_comp_mode == cmBuffered)
		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		{
			for (int l = 0; l < MAX_LAYER; ++l)
				if (i->m_comp_buffer[l])
					setBackgroundColor(i->m_comp_buffer[l], l ? gRGB(0, 0, 0, 0) : col); /* all layers above 0 will have a transparent background */
		}
}

void eWidgetDesktop::setPalette(gPixmap &pm)
{
//	if (m_comp_mode == cmImmediate)
	{
		ASSERT(m_screen.m_dc);
		gPainter painter(m_screen.m_dc);
		painter.setPalette(&pm);
	}

	if (m_comp_mode == cmBuffered)
	{
		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		{
			for (int l = 0; l < MAX_LAYER; ++l)
			{
				if (!i->m_comp_buffer[l])
					continue;
				ASSERT(i->m_comp_buffer[l]->m_dc);
				gPainter painter(i->m_comp_buffer[l]->m_dc);
				painter.setPalette(&pm);
			}
		}
	}
}

void eWidgetDesktop::paintBackground(eWidgetDesktopCompBuffer *comp)
{
	if (!comp)
		return;

	comp->m_dirty_region &= comp->m_background_region;

	gPainter painter(comp->m_dc);

	painter.resetClip(comp->m_dirty_region);
	painter.setBackgroundColor(comp->m_background_color);
	painter.clear();

	comp->m_dirty_region = gRegion();
}


void eWidgetDesktop::paintLayer(eWidget *widget, int layer)
{
	eWidgetDesktopCompBuffer *comp = (m_comp_mode == cmImmediate) ? &m_screen : widget->m_comp_buffer[layer];
	if (m_comp_mode == cmImmediate)
		ASSERT(layer == 0);
	if (!comp)
		return;
	gPainter painter(comp->m_dc);
	painter.moveOffset(-comp->m_position);
	widget->doPaint(painter, comp->m_dirty_region, layer);
	painter.resetOffset();
}

void eWidgetDesktop::paint()
{
	m_require_redraw = 0;

		/* walk all root windows. */
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
	{

		if (!(i->m_vis & eWidget::wVisShow))
			continue;

		if (m_comp_mode == cmImmediate)
			paintLayer(i, 0);
		else
			for (int l = 0; l < MAX_LAYER; ++l)
			{
				paintLayer(i, l);
				paintBackground(i->m_comp_buffer[l]);
			}
	}

	if (m_comp_mode == cmImmediate)
		paintBackground(&m_screen);

	if (m_comp_mode == cmBuffered)
	{
//		redrawComposition(0);
	} else
	{
		gPainter painter(m_screen.m_dc);
		painter.flush();
	}
}

void eWidgetDesktop::setDC(gDC *dc)
{
	m_screen.m_dc = dc;
	if (m_comp_mode == cmBuffered)
		redrawComposition(1);
}

void eWidgetDesktop::setRedrawTask(eMainloop &ml)
{
	if (m_mainloop)
	{
		m_timer = 0;
		m_mainloop = 0;
	}
	m_mainloop = &ml;
	m_timer = eTimer::create(m_mainloop);
	CONNECT(m_timer->timeout, eWidgetDesktop::paint);

	if (m_require_redraw)
		m_timer->start(0, 1);
}

void eWidgetDesktop::makeCompatiblePixmap(ePtr<gPixmap> &pm)
{
	makeCompatiblePixmap(*(pm.operator->()));
}

void eWidgetDesktop::makeCompatiblePixmap(gPixmap &pm)
{
	if (m_comp_mode != cmImmediate)
		return;

//	eDebug("[widgetDesktop] make compatible pixmap of %p", &pm);
	if (!m_screen.m_dc)
	{
		eWarning("[eWidgetDesktop] no DC to make pixmap compatible with!");
		return;
	}

	ePtr<gPixmap> target_pixmap;
	m_screen.m_dc->getPixmap(target_pixmap);

	if (!target_pixmap) {
		eDebug("[eWidgetDesktop] no target pixmap! assuming bpp > 8 for accelerated graphics.");
		return;
	}

	if (target_pixmap->surface && target_pixmap->surface->bpp > 8)
		return;

	ePtr<gDC> pixmap_dc = new gDC(&pm);
	gPainter pixmap_painter(pixmap_dc);

	pixmap_painter.mergePalette(target_pixmap);
}

void eWidgetDesktop::setCompositionMode(int mode)
{
	m_comp_mode = mode;

	if (mode == cmBuffered)
		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
			createBufferForWidget(*i, 0);
	else
		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
			for (int l = 0; l < MAX_LAYER; ++l)
				removeBufferForWidget(*i, l);
}

eWidgetDesktop::eWidgetDesktop(eSize size):
	m_mainloop(0),
	m_require_redraw(0),
	m_style_id(0),
	m_margins(0,0,0,0)
{
	m_screen.m_dirty_region = gRegion(eRect(ePoint(0, 0), size));
	m_screen.m_screen_size = size;

	CONNECT(gRC::getInstance()->notify, eWidgetDesktop::notify);
	setCompositionMode(cmImmediate);
}

eWidgetDesktop::~eWidgetDesktop()
{
		/* tell registered root windows that they no longer have a desktop. */
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); )
	{
		i->m_desktop = 0;
		i = m_root.erase(i);
	}
		/* destroy all buffers */
	setCompositionMode(-1);
}

void eWidgetDesktop::createBufferForWidget(eWidget *widget, int layer)
{
	removeBufferForWidget(widget, layer);

	eWidgetDesktopCompBuffer *comp = widget->m_comp_buffer[layer] = new eWidgetDesktopCompBuffer;

	eDebug("[eWidgetDesktop] create buffer for widget layer %d, %d x %d\n", layer, widget->size().width(), widget->size().height());

	eRect bbox = eRect(widget->position(), widget->size());
	comp->m_position = bbox.topLeft();
	comp->m_dirty_region = gRegion(eRect(ePoint(0, 0), bbox.size()));
	comp->m_screen_size = bbox.size();
		/* TODO: configurable bit depth. */

		/* clone palette. FIXME. */
	ePtr<gPixmap> pm = new gPixmap(comp->m_screen_size, 32, 1), pm_screen;
	pm->surface->clut.data = new gRGB[256];
	pm->surface->clut.colors = 256;
	pm->surface->clut.start = 0;

	m_screen.m_dc->getPixmap(pm_screen);

	memcpy(pm->surface->clut.data, pm_screen->surface->clut.data, 256 * sizeof(gRGB));

	comp->m_dc = new gDC(pm);
}

void eWidgetDesktop::removeBufferForWidget(eWidget *widget, int layer)
{
	if (widget->m_comp_buffer[layer])
	{
		delete widget->m_comp_buffer[layer];
		widget->m_comp_buffer[layer] = 0;
	}
}

void eWidgetDesktop::redrawComposition(int notified)
{
	if (m_comp_mode != cmBuffered)
		return;

	ASSERT(m_screen.m_dc);

	gPainter p(m_screen.m_dc);
	p.resetClip(eRect(ePoint(0, 0), m_screen.m_screen_size));
	p.setBackgroundColor(m_screen.m_background_color);
	p.clear();

	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
	{
		if (!i->isVisible())
			continue;
		for (int layer = 0; layer < MAX_LAYER; ++layer)
		{
			ePtr<gPixmap> pm;
			if (!i->m_comp_buffer[layer])
				continue;
			i->m_comp_buffer[layer]->m_dc->getPixmap(pm);
			p.blit(pm, i->m_comp_buffer[layer]->m_position, eRect(), gPixmap::blitAlphaBlend);
		}
	}

		// flip activates on next vsync.
	p.flip();
	p.waitVSync();

	if (notified)
		p.notify();

	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		if (i->m_animation.m_active)
			i->m_animation.tick(1);
}

void eWidgetDesktop::notify()
{
	redrawComposition(1);
}

void eWidgetDesktop::clearVisibility(eWidget *widget)
{
	widget->m_visible_with_childs = gRegion();
	for (ePtrList<eWidget>::iterator i(widget->m_childs.begin()); i != widget->m_childs.end(); ++i)
		clearVisibility(*i);
}

void eWidgetDesktop::resize(eSize size)
{
	m_screen.m_dirty_region = gRegion(eRect(ePoint(0, 0), size));
	m_screen.m_screen_size = size;
#ifdef USE_LIBVUGLES2
	gPainter painter(m_screen.m_dc);
	painter.setView(size);
#endif
}

void eWidgetDesktop::sendShow(ePoint point, eSize size)
{
	if(m_style_id!=0)
		return;

	gPainter painter(m_screen.m_dc);
	painter.sendShow(point, size);
}

void eWidgetDesktop::sendHide(ePoint point, eSize size)
{
	if(m_style_id!=0)
		return;

	gPainter painter(m_screen.m_dc);
	painter.sendHide(point, size);
}

eRect eWidgetDesktop::bounds() const
{
	const eSize size = m_screen.m_screen_size;
	return eRect(
			m_margins.left(),
			m_margins.top(),
			size.width() - m_margins.left() - m_margins.right(), // width
			size.height() - m_margins.top() - m_margins.bottom() // height
		);
}
