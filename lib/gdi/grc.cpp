// for debugging use:
// #define SYNC_PAINT
#include <unistd.h>
#ifndef SYNC_PAINT
#include <pthread.h>
#endif

#include <lib/gdi/grc.h>
#include <lib/gdi/font.h>
#include <lib/gdi/lcd.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#define MAXSIZE 1024

#ifndef SYNC_PAINT
void *gRC::thread_wrapper(void *ptr)
{
	nice(3);
	return ((gRC*)ptr)->thread();
}
#endif

gRC *gRC::instance=0;

gRC::gRC(): queue(2048), queuelock(MAXSIZE)
{
	ASSERT(!instance);
	instance=this;
	queuelock.lock(MAXSIZE);
#ifndef SYNC_PAINT
	eDebug(pthread_create(&the_thread, 0, thread_wrapper, this)?"RC thread couldn't be created":"RC thread createted successfully");
#endif
}

gRC::~gRC()
{
	fbClass::getInstance()->lock();
#ifndef DISABLE_LCD
	eDBoxLCD::getInstance()->lock();
#endif
	instance=0;

	gOpcode o;
	o.opcode=gOpcode::shutdown;
	submit(o);
	eDebug("waiting for gRC thread shutdown");
	pthread_join(the_thread, 0);
	eDebug("gRC thread has finished");
}

void *gRC::thread()
{
#ifndef SYNC_PAINT
	while (1)
#else
	while (queue.size())
#endif
	{
		queuelock.lock(1);
		gOpcode& o(queue.current());
		if (o.opcode==gOpcode::shutdown)
			break;
		o.dc->exec(&o);
		o.dc->Release();
		queue.dequeue();
	}
#ifndef SYNC_PAINT
	pthread_exit(0);
#endif
	return 0;
}

gRC *gRC::getInstance()
{
	return instance;
}

static int gPainter_instances;

gPainter::gPainter(gDC *dc, eRect rect): m_dc(dc), m_rc(gRC::getInstance())
{
//	ASSERT(!gPainter_instances);
	gPainter_instances++;
	begin(rect);
}

gPainter::~gPainter()
{
	end();
	gPainter_instances--;
}

void gPainter::setBackgroundColor(const gColor &color)
{
	gOpcode o;
	o.opcode = gOpcode::setBackgroundColor;
	o.dc = m_dc.grabRef();
	o.parm.setColor = new gOpcode::para::psetColor;
	o.parm.setColor->color = color;
	
	m_rc->submit(o);
}

void gPainter::setForegroundColor(const gColor &color)
{
	gOpcode o;
	o.opcode = gOpcode::setForegroundColor;
	o.dc = m_dc.grabRef();
	o.parm.setColor = new gOpcode::para::psetColor;
	o.parm.setColor->color = color;
	
	m_rc->submit(o);
}

void gPainter::setFont(gFont *font)
{
	gOpcode o;
	o.opcode = gOpcode::setFont;
	o.dc = m_dc.grabRef();
	font->AddRef();
	o.parm.setFont = new gOpcode::para::psetFont;
	o.parm.setFont->font = font;
	
	m_rc->submit(o);
}

void gPainter::renderText(const eRect &pos, const std::string &string, int flags)
{
	gOpcode o;
	o.opcode=gOpcode::renderText;
	o.dc = m_dc.grabRef();
	o.parm.renderText = new gOpcode::para::prenderText;
	o.parm.renderText->area = pos;
	o.parm.renderText->text = string;
	o.parm.renderText->flags = flags;
	m_rc->submit(o);
}

void gPainter::renderPara(eTextPara *para, ePoint offset)
{
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
	gOpcode o;
	o.opcode=gOpcode::fill;

	o.dc = m_dc.grabRef();
	o.parm.fill = new gOpcode::para::pfillRect;
	o.parm.fill->area = area;
	m_rc->submit(o);
}

void gPainter::clear()
{
	gOpcode o;
	o.opcode=gOpcode::clear;
	o.dc = m_dc.grabRef();
	o.parm.fill = new gOpcode::para::pfillRect;
	o.parm.fill->area = eRect();
	m_rc->submit(o);
}

void gPainter::blit(gPixmap *pixmap, ePoint pos, gRegion *clip, int flags)
{
	gOpcode o;

	o.opcode=gOpcode::blit;
	o.dc = m_dc.grabRef();
	pixmap->AddRef();
	o.parm.blit  = new gOpcode::para::pblit;
	o.parm.blit->pixmap = pixmap;
	o.parm.blit->position = pos;
	clip->AddRef();
	o.parm.blit->clip = clip;
	o.flags=flags;
	m_rc->submit(o);
}


void gPainter::setPalette(gRGB *colors, int start, int len)
{
	gOpcode o;
	o.opcode=gOpcode::setPalette;
	o.dc = m_dc.grabRef();
	gPalette *p=new gPalette;
	
	p->data=new gRGB[len];
	memcpy(p->data, colors, len*sizeof(gRGB));
	p->start=start;
	p->colors=len;
	o.parm.setPalette->palette = p;
	m_rc->submit(o);
}

void gPainter::mergePalette(gPixmap *target)
{
	gOpcode o;
	o.opcode=gOpcode::mergePalette;
	o.dc = m_dc.grabRef();
	target->AddRef();
	o.parm.mergePalette->target = target;
	m_rc->submit(o);
}

void gPainter::line(ePoint start, ePoint end)
{
	gOpcode o;
	o.opcode=gOpcode::line;
	o.dc = m_dc.grabRef();
	o.parm.line = new gOpcode::para::pline;
	o.parm.line->start = start;
	o.parm.line->end = end;
	m_rc->submit(o);
}

void gPainter::setLogicalZero(ePoint val)
{
	gOpcode o;
	o.opcode=gOpcode::setOffset;
	o.dc = m_dc.grabRef();
	o.parm.setOffset = new gOpcode::para::psetOffset;
	o.parm.setOffset->rel = 0;
	o.parm.setOffset->value = val;
	m_rc->submit(o);
}

void gPainter::moveLogicalZero(ePoint rel)
{
	gOpcode o;
	o.opcode=gOpcode::moveOffset;
	o.dc = m_dc.grabRef();
	o.parm.setOffset = new gOpcode::para::psetOffset;
	o.parm.setOffset->rel = 1;
	o.parm.setOffset->value = rel;
	m_rc->submit(o);
}

void gPainter::resetLogicalZero()
{
	gOpcode o;
	o.opcode=gOpcode::moveOffset;
	o.dc = m_dc.grabRef();
	o.parm.setOffset = new gOpcode::para::psetOffset;
	o.parm.setOffset->value = ePoint(0, 0);
	m_rc->submit(o);
}

void gPainter::clip(const gRegion &region)
{
	gOpcode o;
	o.opcode = gOpcode::addClip;
	o.dc = m_dc.grabRef();
	o.parm.clip = new gOpcode::para::psetClip;
	o.parm.clip->region = new gRegion(region);
	o.parm.clip->region->AddRef();
	m_rc->submit(o);
}

void gPainter::clippop()
{
	gOpcode o;
	o.opcode = gOpcode::popClip;
	o.dc = m_dc.grabRef();
	m_rc->submit(o);
}

void gPainter::flush()
{
}

void gPainter::end()
{
}

gDC::gDC()
{
}

gDC::gDC(gPixmap *pixmap): m_pixmap(pixmap)
{
}

gDC::~gDC()
{
}

void gDC::exec(gOpcode *o)
{
#if 0
	switch(o->opcode)
	{
	case gOpcode::renderText:
	{
		ePtr<eTextPara> para = new eTextPara(o->parm.renderText.area);
		para->setFont(m_current_font);
		para->renderString(*o->parm.renderText.text, o->parm.renderText.flags);
		para->blit(*this, ePoint(0, 0), m_foregroundColor, m_backgroundColor);
		delete o->parm.renderText->text;
		break;
	}
	case gOpcode::renderPara:
	{
		o->parm.renderPara.textpara->blit(*this, o->parm.renderPara.offset, m_foregroundColor, m_backgroundColor);
		o->parm.renderPara.textpara.Release();
		break;
	}
	case gOpcode::fill:
		m_pixmap->fill(o->parm.fill.area, m_foregroundColor);
		delete o->parm.fill;
		break;
	case gOpcode::blit:
	{
		gRegion clip;
		if (o->parm.blit.clip)
		{
			clip.intersect(o->parm.blit.clip, clip);
			o->parm.blit.clip->Release();
		} else
			clip = m_current_clip;
		pixmap->blit(*o->parm.blit.pixmap, o->parm.blit.pos, clip, o->parm.blit.flags);
		o->parm.blit.pixmap->Release();
		break;
	}
	case gOpcode::setPalette:
#if 0
		if (o->parm.setPalette->palette->start>pixmap->surface->clut.colors)
			o->parm.setPalette->palette->start=pixmap->surface->clut.colors;
		if (o->parm.setPalette->palette->colors>(pixmap->surface->clut.colors-o->parm.setPalette->palette->start))
			o->parm.setPalette->palette->colors=pixmap->surface->clut.colors-o->parm.setPalette->palette->start;
		if (o->parm.setPalette->palette->colors)
			memcpy(pixmap->surface->clut.data+o->parm.setPalette->palette->start, o->parm.setPalette->palette->data, o->parm.setPalette->palette->colors*sizeof(gRGB));
		delete[] o->parm.setPalette->palette->data;
		delete o->parm.setPalette->palette;
		delete o->parm.setPalette;
#endif
		break;
	case gOpcode::mergePalette:
#if 0
		pixmap->mergePalette(*o->parm.blit->pixmap);
		o->parm.blit->pixmap->unlock();
		delete o->parm.blit;
#endif
		break;
	case gOpcode::line:
#if 0
		pixmap->line(o->parm.line->start, o->parm.line->end, o->parm.line->color);
		delete o->parm.line;
#endif
		break;
	case gOpcode::setBackgroundColor:
		m_backgroundColor = o->parm.setColor.color;
		break;
	case gOpcode::setForegroundColor:
		m_foregroundColor = o->parm.setColor.color;
		break;
	case gOpcode::clip:
		break;
	default:
		eFatal("illegal opcode %d. expect memory leak!", o->opcode);
	}
#endif
}

gRGB gDC::getRGB(gColor col)
{
	if ((!m_pixmap) || (!m_pixmap->surface->clut.data))
		return gRGB(col, col, col);
	if (col<0)
	{
		eFatal("bla transp");
		return gRGB(0, 0, 0, 0xFF);
	}
	return m_pixmap->surface->clut.data[col];
}

DEFINE_REF(gDC);

eAutoInitP0<gRC> init_grc(eAutoInitNumbers::graphic, "gRC");
