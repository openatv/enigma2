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

		/* the creation will be postponed. */
	root->m_comp_buffer = 0;
}

void eWidgetDesktop::removeRootWidget(eWidget *root)
{
	if (m_comp_mode == cmBuffered)
		removeBufferForWidget(root);

	m_root.remove(root);
}

void eWidgetDesktop::calcWidgetClipRegion(struct eWidgetDesktopCompBuffer *comp, eWidget *widget, gRegion &parent_visible)
{
		/* start with our clip region, clipped with the parent's */
	if (widget->m_vis & eWidget::wVisShow)
	{
		widget->m_visible_region = widget->m_clip_region;
		widget->m_visible_region.moveBy(widget->position() - comp->m_position);
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
		calcWidgetClipRegion(comp, *i, widget->m_visible_region);
}

void eWidgetDesktop::recalcClipRegions()
{
	if (m_comp_mode == cmImmediate)
		m_screen.m_background_region = gRegion(eRect(ePoint(0, 0), m_screen.m_screen_size));
	
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
	{
		eWidgetDesktopCompBuffer *comp = (m_comp_mode == cmImmediate) ? &m_screen : i->m_comp_buffer;
		
		if (m_comp_mode != cmImmediate)
		{
			if (!comp)
			{
	 			createBufferForWidget(*i);
	 			comp = i->m_comp_buffer;
	 		}
	 		
			comp->m_background_region = gRegion(eRect(ePoint(0, 0), comp->m_screen_size));
		}
		
		calcWidgetClipRegion(comp, *i, comp->m_background_region);
	}
}

void eWidgetDesktop::invalidate(const gRegion &region)
{
	if (m_timer && !m_require_redraw)
		m_timer->start(0, 1); // start singleshot redraw timer
	
	m_require_redraw = 1;
	
	if (m_comp_mode == cmImmediate)
		m_screen.m_dirty_region |= region;
	else
		for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
		{
			eWidgetDesktopCompBuffer *comp = i->m_comp_buffer;
			
			gRegion mregion = region;
			mregion.moveBy(-comp->m_position);
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
	if (m_comp_mode == cmImmediate)
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
	eDebug("paint");
	m_require_redraw = 0;
	
		/* walk all root windows. */
	for (ePtrList<eWidget>::iterator i(m_root.begin()); i != m_root.end(); ++i)
	{
		eWidgetDesktopCompBuffer *comp = (m_comp_mode == cmImmediate) ? &m_screen : i->m_comp_buffer;
		
		{
			gPainter painter(comp->m_dc);
			i->doPaint(painter, comp->m_dirty_region);
		}

		if (m_comp_mode != cmImmediate)
			paintBackground(comp);
	}
	
	if (m_comp_mode == cmImmediate)
		paintBackground(&m_screen);
}

void eWidgetDesktop::setDC(gDC *dc)
{
	m_screen.m_dc = dc;
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
	
	eDebug("widgetDesktop: make compatible pixmap of %p\n", &pm);
	if (!m_screen.m_dc)
	{
		eWarning("eWidgetDesktop: no DC to make pixmap compatible with!");
		return;
	}

	ePtr<gDC> pixmap_dc = new gDC(&pm);
	gPainter pixmap_painter(pixmap_dc);
	
	ePtr<gPixmap> target_pixmap;
	m_screen.m_dc->getPixmap(target_pixmap);
	
	assert(target_pixmap);
	
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

	setCompositionMode(cmImmediate);
}

eWidgetDesktop::~eWidgetDesktop()
{
		/* destroy all buffer */
	setCompositionMode(-1);
}

void eWidgetDesktop::createBufferForWidget(eWidget *widget)
{
	removeBufferForWidget(widget);
	
	eWidgetDesktopCompBuffer *comp = widget->m_comp_buffer = new eWidgetDesktopCompBuffer;
	
	eRect bbox = widget->m_clip_region.extends;
	comp->m_position = bbox.topLeft();
	comp->m_dirty_region = gRegion(eRect(ePoint(0, 0), bbox.size()));
	comp->m_screen_size = bbox.size();
//	comp->m_dc = new .. ;
}

void eWidgetDesktop::removeBufferForWidget(eWidget *widget)
{
	if (widget->m_comp_buffer)
	{
		delete widget->m_comp_buffer;
		widget->m_comp_buffer = 0;
	}
}
