#include <unistd.h>
#include <fstream>
#include <lib/gdi/grc.h>
#include <lib/gdi/font.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#ifdef USE_LIBVUGLES2
#include <vuplus_gles.h>
#endif

#ifndef SYNC_PAINT
void *gRC::thread_wrapper(void *ptr)
{
	return ((gRC*)ptr)->thread();
}
#endif

gRC *gRC::instance=0;

gRC::gRC(): rp(0), wp(0)
#ifdef SYNC_PAINT
,m_notify_pump(eApp, 0)
#else
,m_notify_pump(eApp, 1)
#endif
,m_spinner_enabled(0), m_spinneronoff(1), m_prev_idle_count(0)
{
	ASSERT(!instance);
	instance=this;
	CONNECT(m_notify_pump.recv_msg, gRC::recv_notify);
#ifndef SYNC_PAINT
	pthread_mutex_init(&mutex, 0);
	pthread_cond_init(&cond, 0);
	pthread_attr_t attr;
	pthread_attr_init(&attr);
	if (pthread_attr_setstacksize(&attr, 2048*1024) != 0)
		eDebug("[gRC] pthread_attr_setstacksize failed");
	int res = pthread_create(&the_thread, &attr, thread_wrapper, this);
	pthread_attr_destroy(&attr);
	if (res)
		eFatal("[gRC] thread couldn't be created");
	else
		eDebug("[gRC] thread created successfully");
#endif
}

#ifdef CONFIG_ION
void gRC::lock()
{
#ifndef SYNC_PAINT
	pthread_mutex_lock(&mutex);
#endif
}

void gRC::unlock()
{
#ifndef SYNC_PAINT
	pthread_mutex_unlock(&mutex);
#endif
}
#endif

DEFINE_REF(gRC);

gRC::~gRC()
{
	instance=0;

	gOpcode o;
	o.opcode=gOpcode::shutdown;
	submit(o);
#ifndef SYNC_PAINT
	eDebug("[gRC] waiting for gRC thread shutdown");
	pthread_join(the_thread, 0);
	eDebug("[gRC] thread has finished");
#endif
}

void gRC::submit(const gOpcode &o)
{
	while(1)
	{
#ifndef SYNC_PAINT
		pthread_mutex_lock(&mutex);
#endif
		int tmp=wp+1;
		if ( tmp == MAXSIZE )
			tmp=0;
		if ( tmp == rp )
		{
#ifndef SYNC_PAINT
			pthread_cond_signal(&cond);  // wakeup gdi thread
			pthread_mutex_unlock(&mutex);
#else
			thread();
#endif
			//eDebug("[gRC] render buffer full...");
			//fflush(stdout);
			usleep(1000);  // wait 1 msec
			continue;
		}
		int free=rp-wp;
		if ( free <= 0 )
			free+=MAXSIZE;
		queue[wp++]=o;
		if ( wp == MAXSIZE )
			wp = 0;
		if (o.opcode==gOpcode::flush||o.opcode==gOpcode::shutdown||o.opcode==gOpcode::notify)
#ifndef SYNC_PAINT
			pthread_cond_signal(&cond);  // wakeup gdi thread
		pthread_mutex_unlock(&mutex);
#else
			thread(); // paint
#endif
		break;
	}
}

void *gRC::thread()
{
	int need_notify = 0;
#ifdef USE_LIBVUGLES2
	if (gles_open()) {
		gles_state_open();
		gles_viewport(720, 576, 720 * 4);
	}
#endif
#ifndef SYNC_PAINT
	while (1)
	{
#else
	while (rp != wp)
	{
#endif
#ifndef SYNC_PAINT
		pthread_mutex_lock(&mutex);
#endif
		if ( rp != wp )
		{
				/* make sure the spinner is not displayed when we something is painted */
			disableSpinner();

			gOpcode o(queue[rp++]);
			if ( rp == MAXSIZE )
				rp=0;
#ifndef SYNC_PAINT
			pthread_mutex_unlock(&mutex);
#endif
			if (o.opcode==gOpcode::shutdown)
				break;
			else if (o.opcode==gOpcode::notify)
				need_notify = 1;
			else if (o.opcode==gOpcode::setCompositing)
			{
				m_compositing = o.parm.setCompositing;
				m_compositing->Release();
			} else if(o.dc)
			{
				o.dc->exec(&o);
				// o.dc is a gDC* filled with grabref... so we must release it here
				o.dc->Release();
			}
		}
		else
		{
			if (need_notify)
			{
				need_notify = 0;
				m_notify_pump.send(1);
			}
#ifndef SYNC_PAINT
			while(rp == wp)
			{

					/* when the main thread is non-idle for a too long time without any display output,
					   we want to display a spinner. */
				struct timespec timeout;
				clock_gettime(CLOCK_REALTIME, &timeout);

				if (m_spinner_enabled)
				{
					timeout.tv_nsec += 100*1000*1000;
					/* yes, this is required. */
					if (timeout.tv_nsec > 1000*1000*1000)
					{
						timeout.tv_nsec -= 1000*1000*1000;
						timeout.tv_sec++;
					}
				}
				else
					timeout.tv_sec += 2;

				int idle = 1;

				if (pthread_cond_timedwait(&cond, &mutex, &timeout) == ETIMEDOUT)
				{
					if (eApp && !eApp->isIdle())
					{
						int idle_count = eApp->idleCount();
						if (idle_count == m_prev_idle_count)
							idle = 0;
						else
							m_prev_idle_count = idle_count;
					}
				}

				if (!idle)
				{
					if (!m_spinner_enabled)
					{
						eDebug("[gRC] main thread is non-idle! display spinner!");
							std::ofstream dummy("/tmp/doPythonStackTrace");
							dummy.close();
					}
					enableSpinner();
				} else
					disableSpinner();
			}
			pthread_mutex_unlock(&mutex);
#endif
		}
	}
#ifdef USE_LIBVUGLES2
	gles_state_close();
	gles_close();
#endif
#ifndef SYNC_PAINT
	pthread_exit(0);
#endif
	return 0;
}

void gRC::recv_notify(const int &i)
{
	notify();
}

gRC *gRC::getInstance()
{
	return instance;
}

void gRC::enableSpinner()
{
	if (!m_spinner_dc)
	{
		eDebug("[gRC] enabelSpinner: no spinner DC!");
		return;
	}

	if (m_spinneronoff)
	{
		gOpcode o;
		o.opcode = m_spinner_enabled ? gOpcode::incrementSpinner : gOpcode::enableSpinner;
		m_spinner_dc->exec(&o);
		o.opcode = gOpcode::flush;
		m_spinner_dc->exec(&o);
	}
	m_spinner_enabled = 1;
}

void gRC::disableSpinner()
{
	if (!m_spinner_enabled)
		return;

	if (!m_spinner_dc)
	{
		eDebug("[gRC] disableSpinner: no spinner DC!");
		return;
	}

	m_spinner_enabled = 0;

	gOpcode o;
	o.opcode = gOpcode::disableSpinner;
	m_spinner_dc->exec(&o);
	o.opcode = gOpcode::flush;
	m_spinner_dc->exec(&o);
}

static int gPainter_instances;

gPainter::gPainter(gDC *dc, eRect rect): m_dc(dc), m_rc(gRC::getInstance())
{
//	ASSERT(!gPainter_instances);
	gPainter_instances++;
//	begin(rect);
}

gPainter::~gPainter()
{
	end();
	gPainter_instances--;
}

void gPainter::setBackgroundColor(const gColor &color)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::setBackgroundColor;
	o.dc = m_dc.grabRef();
	o.parm.setColor = new gOpcode::para::psetColor;
	o.parm.setColor->color = color;

	m_rc->submit(o);
}

void gPainter::setForegroundColor(const gColor &color)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::setForegroundColor;
	o.dc = m_dc.grabRef();
	o.parm.setColor = new gOpcode::para::psetColor;
	o.parm.setColor->color = color;

	m_rc->submit(o);
}

void gPainter::setBackgroundColor(const gRGB &color)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::setBackgroundColorRGB;
	o.dc = m_dc.grabRef();
	o.parm.setColorRGB = new gOpcode::para::psetColorRGB;
	o.parm.setColorRGB->color = color;

	m_rc->submit(o);
}

void gPainter::setForegroundColor(const gRGB &color)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::setForegroundColorRGB;
	o.dc = m_dc.grabRef();
	o.parm.setColorRGB = new gOpcode::para::psetColorRGB;
	o.parm.setColorRGB->color = color;

	m_rc->submit(o);
}

void gPainter::setFont(gFont *font)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::setFont;
	o.dc = m_dc.grabRef();
	font->AddRef();
	o.parm.setFont = new gOpcode::para::psetFont;
	o.parm.setFont->font = font;

	m_rc->submit(o);
}

void gPainter::renderText(const eRect &pos, const std::string &string, int flags, gRGB bordercolor, int border)
{
	if (string.empty()) return;
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::renderText;
	o.dc = m_dc.grabRef();
	o.parm.renderText = new gOpcode::para::prenderText;
	o.parm.renderText->area = pos;
	o.parm.renderText->text = strdup(string.c_str());
	o.parm.renderText->flags = flags;
	o.parm.renderText->border = border;
	o.parm.renderText->bordercolor = bordercolor;
	m_rc->submit(o);
}

void gPainter::renderPara(eTextPara *para, ePoint offset)
{
	if ( m_dc->islocked() )
		return;
	ASSERT(para);
	gOpcode o;
	o.opcode=gOpcode::renderPara;
	o.dc = m_dc.grabRef();
	o.parm.renderPara = new gOpcode::para::prenderPara;
	o.parm.renderPara->offset = offset;

 	para->AddRef();
	o.parm.renderPara->textpara = para;
	m_rc->submit(o);
}

void gPainter::fill(const eRect &area)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::fill;

	o.dc = m_dc.grabRef();
	o.parm.fill = new gOpcode::para::pfillRect;
	o.parm.fill->area = area;
	m_rc->submit(o);
}

void gPainter::fill(const gRegion &region)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::fillRegion;

	o.dc = m_dc.grabRef();
	o.parm.fillRegion = new gOpcode::para::pfillRegion;
	o.parm.fillRegion->region = region;
	m_rc->submit(o);
}

void gPainter::clear()
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::clear;
	o.dc = m_dc.grabRef();
	o.parm.fill = new gOpcode::para::pfillRect;
	o.parm.fill->area = eRect();
	m_rc->submit(o);
}

void gPainter::blit(gPixmap *pixmap, ePoint pos, const eRect &clip, int flags)
{
	blitScale(pixmap, eRect(pos, eSize()), clip, flags, 0);
}

void gPainter::blitScale(gPixmap *pixmap, const eRect &position, const eRect &clip, int flags, int aflags)
{
	flags |= aflags;

	if ( m_dc->islocked() )
		return;
	gOpcode o;

	ASSERT(pixmap);

	o.opcode=gOpcode::blit;
	o.dc = m_dc.grabRef();
	pixmap->AddRef();
	o.parm.blit  = new gOpcode::para::pblit;
	o.parm.blit->pixmap = pixmap;
	o.parm.blit->clip = clip;
	o.parm.blit->flags = flags;
	o.parm.blit->position = position;
	m_rc->submit(o);
}

void gPainter::setPalette(gRGB *colors, int start, int len)
{
	if ( m_dc->islocked() )
		return;
	ASSERT(colors);
	gOpcode o;
	o.opcode=gOpcode::setPalette;
	o.dc = m_dc.grabRef();
	gPalette *p=new gPalette;

	o.parm.setPalette = new gOpcode::para::psetPalette;
	p->data=new gRGB[len];

	memcpy(p->data, colors, len*sizeof(gRGB));
	p->start=start;
	p->colors=len;
	o.parm.setPalette->palette = p;
	m_rc->submit(o);
}

void gPainter::setPalette(gPixmap *source)
{
	ASSERT(source);
	setPalette(source->surface->clut.data, source->surface->clut.start, source->surface->clut.colors);
}

void gPainter::mergePalette(gPixmap *target)
{
	if ( m_dc->islocked() )
		return;
	ASSERT(target);
	gOpcode o;
	o.opcode = gOpcode::mergePalette;
	o.dc = m_dc.grabRef();
	target->AddRef();
	o.parm.mergePalette = new gOpcode::para::pmergePalette;
	o.parm.mergePalette->target = target;
	m_rc->submit(o);
}

void gPainter::line(ePoint start, ePoint end)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::line;
	o.dc = m_dc.grabRef();
	o.parm.line = new gOpcode::para::pline;
	o.parm.line->start = start;
	o.parm.line->end = end;
	m_rc->submit(o);
}

void gPainter::setOffset(ePoint val)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::setOffset;
	o.dc = m_dc.grabRef();
	o.parm.setOffset = new gOpcode::para::psetOffset;
	o.parm.setOffset->rel = 0;
	o.parm.setOffset->value = val;
	m_rc->submit(o);
}

void gPainter::moveOffset(ePoint rel)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::setOffset;
	o.dc = m_dc.grabRef();
	o.parm.setOffset = new gOpcode::para::psetOffset;
	o.parm.setOffset->rel = 1;
	o.parm.setOffset->value = rel;
	m_rc->submit(o);
}

void gPainter::resetOffset()
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::setOffset;
	o.dc = m_dc.grabRef();
	o.parm.setOffset = new gOpcode::para::psetOffset;
	o.parm.setOffset->rel = 0;
	o.parm.setOffset->value = ePoint(0, 0);
	m_rc->submit(o);
}

void gPainter::resetClip(const gRegion &region)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::setClip;
	o.dc = m_dc.grabRef();
	o.parm.clip = new gOpcode::para::psetClip;
	o.parm.clip->region = region;
	m_rc->submit(o);
}

void gPainter::clip(const gRegion &region)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::addClip;
	o.dc = m_dc.grabRef();
	o.parm.clip = new gOpcode::para::psetClip;
	o.parm.clip->region = region;
	m_rc->submit(o);
}

void gPainter::clippop()
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::popClip;
	o.dc = m_dc.grabRef();
	m_rc->submit(o);
}

void gPainter::waitVSync()
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::waitVSync;
	o.dc = m_dc.grabRef();
	m_rc->submit(o);
}

void gPainter::flip()
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::flip;
	o.dc = m_dc.grabRef();
	m_rc->submit(o);
}

void gPainter::notify()
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::notify;
	o.dc = m_dc.grabRef();
	m_rc->submit(o);
}

void gPainter::setCompositing(gCompositingData *comp)
{
	gOpcode o;
	o.opcode = gOpcode::setCompositing;
	o.dc = 0;
	o.parm.setCompositing = comp;
	comp->AddRef(); /* will be freed in ::thread */
	m_rc->submit(o);
}

void gPainter::flush()
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode = gOpcode::flush;
	o.dc = m_dc.grabRef();
	m_rc->submit(o);
}

void gPainter::end()
{
	if ( m_dc->islocked() )
		return;
}

void gPainter::sendShow(ePoint point, eSize size)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::sendShow;
	o.dc = m_dc.grabRef();
	o.parm.setShowHideInfo = new gOpcode::para::psetShowHideInfo;
	o.parm.setShowHideInfo->point = point;
	o.parm.setShowHideInfo->size = size;
	m_rc->submit(o);
}

void gPainter::sendHide(ePoint point, eSize size)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::sendHide;
	o.dc = m_dc.grabRef();
	o.parm.setShowHideInfo = new gOpcode::para::psetShowHideInfo;
	o.parm.setShowHideInfo->point = point;
	o.parm.setShowHideInfo->size = size;
	m_rc->submit(o);
}

#ifdef USE_LIBVUGLES2
void gPainter::sendShowItem(long dir, ePoint point, eSize size)
{
       if ( m_dc->islocked() )
               return;
       gOpcode o;
       o.opcode=gOpcode::sendShowItem;
       o.dc = m_dc.grabRef();
       o.parm.setShowItemInfo = new gOpcode::para::psetShowItemInfo;
       o.parm.setShowItemInfo->dir = dir;
       o.parm.setShowItemInfo->point = point;
       o.parm.setShowItemInfo->size = size;
       m_rc->submit(o);
}
void gPainter::setFlush(bool val)
{
       if ( m_dc->islocked() )
               return;
       gOpcode o;
       o.opcode=gOpcode::setFlush;
       o.dc = m_dc.grabRef();
       o.parm.setFlush = new gOpcode::para::psetFlush;
       o.parm.setFlush->enable = val;
       m_rc->submit(o);
}
void gPainter::setView(eSize size)
{
	if ( m_dc->islocked() )
		return;
	gOpcode o;
	o.opcode=gOpcode::setView;
	o.dc = m_dc.grabRef();
	o.parm.setViewInfo = new gOpcode::para::psetViewInfo;
	o.parm.setViewInfo->size = size;
	m_rc->submit(o);
}
#endif

gDC::gDC()
{
	m_spinner_pic = 0;
}

gDC::gDC(gPixmap *pixmap): m_pixmap(pixmap)
{
	m_spinner_pic = 0;
}

gDC::~gDC()
{
	delete[] m_spinner_pic;
}

void gDC::exec(const gOpcode *o)
{
	switch (o->opcode)
	{
	case gOpcode::setBackgroundColor:
		m_background_color = o->parm.setColor->color;
		m_background_color_rgb = getRGB(m_background_color);
		delete o->parm.setColor;
		break;
	case gOpcode::setForegroundColor:
		m_foreground_color = o->parm.setColor->color;
		m_foreground_color_rgb = getRGB(m_foreground_color);
		delete o->parm.setColor;
		break;
	case gOpcode::setBackgroundColorRGB:
		if (m_pixmap->needClut())
			m_background_color = m_pixmap->surface->clut.findColor(o->parm.setColorRGB->color);
		m_background_color_rgb = o->parm.setColorRGB->color;
		delete o->parm.setColorRGB;
		break;
	case gOpcode::setForegroundColorRGB:
		if (m_pixmap->needClut())
			m_foreground_color = m_pixmap->surface->clut.findColor(o->parm.setColorRGB->color);
		m_foreground_color_rgb = o->parm.setColorRGB->color;
		delete o->parm.setColorRGB;
		break;
	case gOpcode::setFont:
		m_current_font = o->parm.setFont->font;
		o->parm.setFont->font->Release();
		delete o->parm.setFont;
		break;
	case gOpcode::renderText:
	{
		ePtr<eTextPara> para = new eTextPara(o->parm.renderText->area);
		int flags = o->parm.renderText->flags;
		ASSERT(m_current_font);
		para->setFont(m_current_font);
		para->renderString(o->parm.renderText->text, (flags & gPainter::RT_WRAP) ? RS_WRAP : 0, o->parm.renderText->border);
		if (o->parm.renderText->text)
			free(o->parm.renderText->text);
		if (flags & gPainter::RT_HALIGN_LEFT)
			para->realign(eTextPara::dirLeft);
		else if (flags & gPainter::RT_HALIGN_RIGHT)
			para->realign(eTextPara::dirRight);
		else if (flags & gPainter::RT_HALIGN_CENTER)
			para->realign((flags & gPainter::RT_WRAP) ? eTextPara::dirCenter : eTextPara::dirCenterIfFits);
		else if (flags & gPainter::RT_HALIGN_BLOCK)
			para->realign(eTextPara::dirBlock);
		else
			para->realign(eTextPara::dirBidi);

		ePoint offset = m_current_offset;

		if (o->parm.renderText->flags & gPainter::RT_VALIGN_CENTER)
		{
			eRect bbox = para->getBoundBox();
			int vcentered_top = o->parm.renderText->area.top() + ((o->parm.renderText->area.height() - bbox.height()) / 2);
			int correction = vcentered_top - bbox.top();
			// Only center if it fits, don't push text out the top
			if ((correction > 0) || (para->getLineCount() == 1))
			{
				offset += ePoint(0, correction);
			}
		}
		else if (o->parm.renderText->flags & gPainter::RT_VALIGN_BOTTOM)
		{
			eRect bbox = para->getBoundBox();
			int correction = o->parm.renderText->area.height() - bbox.height() - 2;
			offset += ePoint(0, correction);
		}
		if (o->parm.renderText->border)
		{
			para->blit(*this, offset, m_background_color_rgb, o->parm.renderText->bordercolor, true);
			para->blit(*this, offset, o->parm.renderText->bordercolor, m_foreground_color_rgb);
		}
		else
		{
			para->blit(*this, offset, m_background_color_rgb, m_foreground_color_rgb);
		}
		delete o->parm.renderText;
		break;
	}
	case gOpcode::renderPara:
	{
		o->parm.renderPara->textpara->blit(*this, o->parm.renderPara->offset + m_current_offset, m_background_color_rgb, m_foreground_color_rgb);
		o->parm.renderPara->textpara->Release();
		delete o->parm.renderPara;
		break;
	}
	case gOpcode::fill:
	{
		eRect area = o->parm.fill->area;
		area.moveBy(m_current_offset);
		gRegion clip = m_current_clip & area;
		if (m_pixmap->needClut())
			m_pixmap->fill(clip, m_foreground_color);
		else
			m_pixmap->fill(clip, m_foreground_color_rgb);
		delete o->parm.fill;
		break;
	}
	case gOpcode::fillRegion:
	{
		o->parm.fillRegion->region.moveBy(m_current_offset);
		gRegion clip = m_current_clip & o->parm.fillRegion->region;
		if (m_pixmap->needClut())
			m_pixmap->fill(clip, m_foreground_color);
		else
			m_pixmap->fill(clip, m_foreground_color_rgb);
		delete o->parm.fillRegion;
		break;
	}
	case gOpcode::clear:
		if (m_pixmap->needClut())
			m_pixmap->fill(m_current_clip, m_background_color);
		else
			m_pixmap->fill(m_current_clip, m_background_color_rgb);
		delete o->parm.fill;
		break;
	case gOpcode::blit:
	{
		gRegion clip;
				// this code should be checked again but i'm too tired now

		o->parm.blit->position.moveBy(m_current_offset);

		if (o->parm.blit->clip.valid())
		{
			o->parm.blit->clip.moveBy(m_current_offset);
			clip.intersect(gRegion(o->parm.blit->clip), m_current_clip);
		} else
			clip = m_current_clip;

		m_pixmap->blit(*o->parm.blit->pixmap, o->parm.blit->position, clip, o->parm.blit->flags);
		o->parm.blit->pixmap->Release();
		delete o->parm.blit;
		break;
	}
	case gOpcode::setPalette:
		if (o->parm.setPalette->palette->start > m_pixmap->surface->clut.colors)
			o->parm.setPalette->palette->start = m_pixmap->surface->clut.colors;
		if (o->parm.setPalette->palette->colors > (m_pixmap->surface->clut.colors-o->parm.setPalette->palette->start))
			o->parm.setPalette->palette->colors = m_pixmap->surface->clut.colors-o->parm.setPalette->palette->start;
		if (o->parm.setPalette->palette->colors)
			memcpy(m_pixmap->surface->clut.data+o->parm.setPalette->palette->start, o->parm.setPalette->palette->data, o->parm.setPalette->palette->colors*sizeof(gRGB));

		delete[] o->parm.setPalette->palette->data;
		delete o->parm.setPalette->palette;
		delete o->parm.setPalette;
		break;
	case gOpcode::mergePalette:
		m_pixmap->mergePalette(*o->parm.mergePalette->target);
		o->parm.mergePalette->target->Release();
		delete o->parm.mergePalette;
		break;
	case gOpcode::line:
	{
		ePoint start = o->parm.line->start + m_current_offset, end = o->parm.line->end + m_current_offset;
		if (m_pixmap->needClut())
			m_pixmap->line(m_current_clip, start, end, m_foreground_color);
		else
			m_pixmap->line(m_current_clip, start, end, m_foreground_color_rgb);
		delete o->parm.line;
		break;
	}
	case gOpcode::addClip:
		m_clip_stack.push(m_current_clip);
		o->parm.clip->region.moveBy(m_current_offset);
		m_current_clip &= o->parm.clip->region;
		delete o->parm.clip;
		break;
	case gOpcode::setClip:
		o->parm.clip->region.moveBy(m_current_offset);
		m_current_clip = o->parm.clip->region & eRect(ePoint(0, 0), m_pixmap->size());
		delete o->parm.clip;
		break;
	case gOpcode::popClip:
		if (!m_clip_stack.empty())
		{
			m_current_clip = m_clip_stack.top();
			m_clip_stack.pop();
		}
		break;
	case gOpcode::setOffset:
		if (o->parm.setOffset->rel)
			m_current_offset += o->parm.setOffset->value;
		else
			m_current_offset  = o->parm.setOffset->value;
		delete o->parm.setOffset;
		break;
	case gOpcode::waitVSync:
		break;
	case gOpcode::flip:
		break;
	case gOpcode::flush:
		break;
	case gOpcode::sendShow:
		break;
	case gOpcode::sendHide:
		break;
#ifdef USE_LIBVUGLES2
	case gOpcode::sendShowItem:
		break;
	case gOpcode::setFlush:
		break;
	case gOpcode::setView:
		break;
#endif
	case gOpcode::enableSpinner:
		enableSpinner();
		break;
	case gOpcode::disableSpinner:
		disableSpinner();
		break;
	case gOpcode::incrementSpinner:
		incrementSpinner();
		break;
	default:
		eFatal("[gDC] illegal opcode %d. expect memory leak!", o->opcode);
	}
}

gRGB gDC::getRGB(gColor col)
{
	if ((!m_pixmap) || (!m_pixmap->surface->clut.data))
		return gRGB(col, col, col);
	if (col<0)
	{
		eFatal("[gDC] getRGB transp");
		return gRGB(0, 0, 0, 0xFF);
	}
	return m_pixmap->surface->clut.data[col];
}

void gDC::enableSpinner()
{
	ASSERT(m_spinner_saved);

		/* save the background to restore it later. We need to negative position because we want to blit from the middle of the screen. */
	m_spinner_saved->blit(*m_pixmap, eRect(-m_spinner_pos.topLeft(), eSize()), gRegion(eRect(ePoint(0, 0), m_spinner_saved->size())), 0);

	incrementSpinner();
}

void gDC::disableSpinner()
{
	ASSERT(m_spinner_saved);

		/* restore background */
	m_pixmap->blit(*m_spinner_saved, eRect(m_spinner_pos.topLeft(), eSize()), gRegion(m_spinner_pos), 0);
}

void gDC::incrementSpinner()
{
	ASSERT(m_spinner_saved);

	static int blub;
	blub++;

#if 0
	int i;

	for (i = 0; i < 5; ++i)
	{
		int x = i * 20 + m_spinner_pos.left();
		int y = m_spinner_pos.top();

		int col = ((blub - i) * 30) % 256;

		m_pixmap->fill(eRect(x, y, 10, 10), gRGB(col, col, col));
	}
#endif

	m_spinner_temp->blit(*m_spinner_saved, eRect(0, 0, 0, 0), eRect(ePoint(0, 0), m_spinner_pos.size()));

	if (m_spinner_pic[m_spinner_i])
		m_spinner_temp->blit(*m_spinner_pic[m_spinner_i], eRect(0, 0, 0, 0), eRect(ePoint(0, 0), m_spinner_pos.size()), gPixmap::blitAlphaBlend);

	m_pixmap->blit(*m_spinner_temp, eRect(m_spinner_pos.topLeft(), eSize()), gRegion(m_spinner_pos), 0);
	m_spinner_i++;
	m_spinner_i %= m_spinner_num;
}

void gDC::setSpinner(eRect pos, ePtr<gPixmap> *pic, int len)
{
	ASSERT(m_pixmap);
	ASSERT(m_pixmap->surface);
	m_spinner_saved = new gPixmap(pos.size(), m_pixmap->surface->bpp);
	m_spinner_temp = new gPixmap(pos.size(), m_pixmap->surface->bpp);
	m_spinner_pos = pos;

	m_spinner_i = 0;
	m_spinner_num = len;

	int i;
	if (m_spinner_pic)
		delete[] m_spinner_pic;

	m_spinner_pic = new ePtr<gPixmap>[len];

	for (i = 0; i < len; ++i)
		m_spinner_pic[i] = pic[i];
}

DEFINE_REF(gDC);

eAutoInitPtr<gRC> init_grc(eAutoInitNumbers::graphic, "gRC");
