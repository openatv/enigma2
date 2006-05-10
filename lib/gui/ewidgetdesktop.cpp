#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/ewidget.h>
#include <lib/base/ebase.h>
#include <lib/gdi/grc.h>

extern void dumpRegion(const gRegion &region);

void eWidgetDesktop::addRootWidget(eWidget *root)
{
	assert(!root->m_desktop);
	
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
	root->m_comp_buffer = 0;
}

void eWidgetDesktop::removeRootWidget(eWidget *root)
{
	if (m_comp_mode == cmBuffered)
		removeBufferForWidget(root);

	m_root.remove(root);
}

int eWidgetDesktop::movedWidget(eWidget *root)
{
	if ((m_comp_mode == cmBuffered) && (root->m_comp_buffer))
	{
		root->m_comp_buffer->m_position = root->position();
//		redrawComposition(0);
		return 0;
	}
	
	return -1;
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
		if (!root->m_vis & eWidget::wVisShow)
		{
			clearVisibility(root);
			removeBufferForWidget(root);
			return;
		}
		if ((!root->m_comp_buffer) || (root->size() != root->m_comp_buffer->m_screen_size))
			createBufferForWidget(root);

		eWidgetDesktopCompBuffer *comp = root->m_comp_buffer;

	 	gRegion visible_before = root->m_visible_with_childs;
	 	 
		comp->m_background_region = gRegion(eRect(comp->m_position, comp->m_screen_size));
		
		gRegion visible_new = root->m_visible_with_childs - visible_before;
		gRegion visible_lost = visible_before - root->m_visible_with_childs;
		visible_new.moveBy(root->position());
		visible_lost.moveBy(root->position());
		
			/* this sucks, obviously. */
		invalidate(visible_new);
		invalidate(visible_lost);
		
		calcWidgetClipRegion(root, comp->m_background_region);
	}
}

void eWidgetDesktop::invalidate(const gRegion &region)
{
	if (region.empty())
		return;
	
	if (m_timer && !m_require_redraw)
		m_timer->start(0, 1); // start singleshot redraw timer
	
	m_require_redraw = 1;
	
	if (m_comp_mode == cmImmediate)
		m_screen.m_dirty_region |= region;
	else
		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		{
			if (!(i->m_vis & eWidget::wVisShow))
				continue;
			
			eWidgetDesktopCompBuffer *comp = i->m_comp_buffer;
			
			gRegion mregion = region;
			comp->m_dirty_region |= mregion;
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
			setBackgroundColor(i->m_comp_buffer, col);
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
			ASSERT(i->m_comp_buffer->m_dc);
			gPainter painter(i->m_comp_buffer->m_dc);
			painter.setPalette(&pm);
		}
	}
}

void eWidgetDesktop::paintBackground(eWidgetDesktopCompBuffer *comp)
{
	comp->m_dirty_region &= comp->m_background_region;
	
	gPainter painter(comp->m_dc);
	
	painter.resetClip(comp->m_dirty_region);
	painter.setBackgroundColor(comp->m_background_color);
	painter.clear();
	painter.flush();
	
	comp->m_dirty_region = gRegion();
}

void eWidgetDesktop::paint()
{
	m_require_redraw = 0;
	
		/* walk all root windows. */
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
	{
		eWidgetDesktopCompBuffer *comp = (m_comp_mode == cmImmediate) ? &m_screen : i->m_comp_buffer;
		
		if (!(i->m_vis & eWidget::wVisShow))
			continue;
		
		{
			gPainter painter(comp->m_dc);
			painter.moveOffset(-comp->m_position);
			i->doPaint(painter, comp->m_dirty_region);
			painter.resetOffset();
		}

		if (m_comp_mode != cmImmediate)
			paintBackground(comp);
	}
	
	if (m_comp_mode == cmImmediate)
		paintBackground(&m_screen);
	
	if (m_comp_mode == cmBuffered)
	{
//		redrawComposition(0);
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
		delete m_timer;
		m_timer = 0;
		m_mainloop = 0;
	}
	m_mainloop = &ml;
	m_timer = new eTimer(m_mainloop);
	CONNECT(m_timer->timeout, eWidgetDesktop::paint);
	
	if (m_require_redraw)
		m_timer->start(0, 1);
}

void eWidgetDesktop::makeCompatiblePixmap(gPixmap &pm)
{
	if (m_comp_mode != cmImmediate)
		return;
	
//	eDebug("widgetDesktop: make compatible pixmap of %p", &pm);
	if (!m_screen.m_dc)
	{
		eWarning("eWidgetDesktop: no DC to make pixmap compatible with!");
		return;
	}

	ePtr<gPixmap> target_pixmap;
	m_screen.m_dc->getPixmap(target_pixmap);
	
	assert(target_pixmap);
	
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
			createBufferForWidget(*i);
	else
		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
			removeBufferForWidget(*i);
}

eWidgetDesktop::eWidgetDesktop(eSize size): m_mainloop(0), m_timer(0)
{
	m_screen.m_dirty_region = gRegion(eRect(ePoint(0, 0), size));
	m_screen.m_screen_size = size;
	m_require_redraw = 0;

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

void eWidgetDesktop::createBufferForWidget(eWidget *widget)
{
	removeBufferForWidget(widget);
	
	eWidgetDesktopCompBuffer *comp = widget->m_comp_buffer = new eWidgetDesktopCompBuffer;
	
	eDebug("create buffer for widget, %d x %d\n", widget->size().width(), widget->size().height());
	
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

void eWidgetDesktop::removeBufferForWidget(eWidget *widget)
{
	if (widget->m_comp_buffer)
	{
		delete widget->m_comp_buffer;
		widget->m_comp_buffer = 0;
	}
}

void eWidgetDesktop::redrawComposition(int notified)
{
	if (m_comp_mode != cmBuffered)
		return;
	
	assert(m_screen.m_dc);
	
	gPainter p(m_screen.m_dc);
	p.resetClip(eRect(ePoint(0, 0), m_screen.m_screen_size));
	p.setBackgroundColor(m_screen.m_background_color);
	p.clear();
	
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
	{
		if (!i->isVisible())
			continue;
		ePtr<gPixmap> pm;
		ASSERT(i->m_comp_buffer);
		i->m_comp_buffer->m_dc->getPixmap(pm);
		p.blit(pm, i->m_comp_buffer->m_position, eRect(), gPixmap::blitAlphaBlend);
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
