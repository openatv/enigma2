// for debugging use:
// #define SYNC_PAINT
#include <unistd.h>
#ifndef SYNC_PAINT
#include <pthread.h>
#endif

#include <lib/gdi/grc.h>
#include <lib/gdi/font.h>
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

gRC::gRC(): queuelock(MAXSIZE), queue(2048)
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
	gOpcode o;
	o.dc=0;
	o.opcode=gOpcode::shutdown;
	submit(o);
	instance=0;
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
		queue.dequeue();
	}
#ifndef SYNC_PAINT
	pthread_exit(0);
#endif
	return 0;
}

gRC &gRC::getInstance()
{
	return *instance;
}

static int gPainter_instances;

gPainter::gPainter(gDC &dc, eRect rect): dc(dc), rc(gRC::getInstance()), foregroundColor(0), backgroundColor(0)
{
	if (rect.isNull())
		rect=eRect(ePoint(0, 0), dc.getSize());
//	ASSERT(!gPainter_instances);
	gPainter_instances++;
	begin(rect);
}

gPainter::~gPainter()
{
	end();
	gPainter_instances--;
}

void gPainter::begin(const eRect &rect)
{
	gOpcode o;
	dc.lock();
	o.dc=&dc;
	o.opcode=gOpcode::begin;
	o.parm.begin=new gOpcode::para::pbegin(rect);
//	cliparea=std::stack<eRect, std::list<eRect> >();
	cliparea=std::stack<eRect>();
	cliparea.push(rect);
	setLogicalZero(cliparea.top().topLeft());
	rc.submit(o);
}

void gPainter::setBackgroundColor(const gColor &color)
{
	backgroundColor=color;
}

void gPainter::setForegroundColor(const gColor &color)
{
	foregroundColor=color;
}

void gPainter::setFont(const gFont &mfont)
{
	font=mfont;
}

void gPainter::renderText(const eRect &pos, const std::string &string, int flags)
{
	eRect area=pos;
	area.moveBy(logicalZero.x(), logicalZero.y());

	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::renderText;
	o.parm.renderText=new gOpcode::para::prenderText(font, area, string, dc.getRGB(foregroundColor), dc.getRGB(backgroundColor));
	o.flags=flags;
	rc.submit(o);
}

void gPainter::renderPara(eTextPara &para, ePoint offset)
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::renderPara;
	o.parm.renderPara=new gOpcode::para::prenderPara(logicalZero+offset, para.grab(), dc.getRGB(foregroundColor), dc.getRGB(backgroundColor));
	rc.submit(o);
}

void gPainter::fill(const eRect &area)
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::fill;
	eRect a=area;
	a.moveBy(logicalZero.x(), logicalZero.y());
	a&=cliparea.top();
	
	o.parm.fill=new gOpcode::para::pfill(a, foregroundColor);
	rc.submit(o);
}

void gPainter::clear()
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::fill;
	o.parm.fill=new gOpcode::para::pfill(cliparea.top(), backgroundColor);
	rc.submit(o);
}

void gPainter::setPalette(gRGB *colors, int start, int len)
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::setPalette;
	gPalette *p=new gPalette;
	
	p->data=new gRGB[len];
	memcpy(p->data, colors, len*sizeof(gRGB));
	p->start=start;
	p->colors=len;
	o.parm.setPalette=new gOpcode::para::psetPalette(p);
	rc.submit(o);
}

void gPainter::mergePalette(gPixmap *target)
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::mergePalette;
	o.parm.mergePalette=new gOpcode::para::pmergePalette(target);
	rc.submit(o);
}

void gPainter::line(ePoint start, ePoint end)
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::line;
	o.parm.line=new gOpcode::para::pline(start+logicalZero, end+logicalZero, foregroundColor);
	rc.submit(o);
}

void gPainter::setLogicalZero(ePoint rel)
{
	logicalZero=rel;
}

void gPainter::moveLogicalZero(ePoint rel)
{
	logicalZero+=rel;
}

void gPainter::resetLogicalZero()
{
	logicalZero.setX(0);
	logicalZero.setY(0);
}

void gPainter::clip(eRect clip)
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::clip;
	clip.moveBy(logicalZero.x(), logicalZero.y());
	cliparea.push(cliparea.top()&clip);
	o.parm.clip=new gOpcode::para::pclip(cliparea.top());

	rc.submit(o);
}

void gPainter::clippop()
{
	ASSERT (cliparea.size()>1);
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::clip;
	cliparea.pop();
	o.parm.clip=new gOpcode::para::pclip(cliparea.top());
	rc.submit(o);
}

void gPainter::flush()
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::flush;
	rc.submit(o);
}

void gPainter::end()
{
	gOpcode o;
	o.dc=&dc;
	o.opcode=gOpcode::end;
	rc.submit(o);
}

gDC::~gDC()
{
}

gPixmapDC::gPixmapDC(): pixmap(0)
{
}

gPixmapDC::gPixmapDC(gPixmap *pixmap): pixmap(pixmap)
{
}

gPixmapDC::~gPixmapDC()
{
	dclock.lock();
}

void gPixmapDC::exec(gOpcode *o)
{
	switch(o->opcode)
	{
	case gOpcode::begin:
		clip=o->parm.begin->area;
		delete o->parm.begin;
		break;
	case gOpcode::renderText:
	{
		eTextPara *para=new eTextPara(o->parm.renderText->area);
		para->setFont(o->parm.renderText->font);
		para->renderString(o->parm.renderText->text, o->flags);
		para->blit(*this, ePoint(0, 0), o->parm.renderText->backgroundColor, o->parm.renderText->foregroundColor);
		para->destroy();
		delete o->parm.renderText;
		break;
	}
	case gOpcode::renderPara:
	{
		o->parm.renderPara->textpara->blit(*this, o->parm.renderPara->offset, o->parm.renderPara->backgroundColor, o->parm.renderPara->foregroundColor);
		o->parm.renderPara->textpara->destroy();
		delete o->parm.renderPara;
		break;
	}
	case gOpcode::fill:
		pixmap->fill(o->parm.fill->area, o->parm.fill->color);
		delete o->parm.fill;
		break;
	case gOpcode::blit:
	{
		if (o->parm.blit->clip.isNull())
			o->parm.blit->clip=clip;
		else
			o->parm.blit->clip&=clip;
		pixmap->blit(*o->parm.blit->pixmap, o->parm.blit->position, o->parm.blit->clip, o->flags);
		delete o->parm.blit;
		break;
	}
	case gOpcode::setPalette:
		if (o->parm.setPalette->palette->start>pixmap->clut.colors)
			o->parm.setPalette->palette->start=pixmap->clut.colors;
		if (o->parm.setPalette->palette->colors>(pixmap->clut.colors-o->parm.setPalette->palette->start))
			o->parm.setPalette->palette->colors=pixmap->clut.colors-o->parm.setPalette->palette->start;
		if (o->parm.setPalette->palette->colors)
			memcpy(pixmap->clut.data+o->parm.setPalette->palette->start, o->parm.setPalette->palette->data, o->parm.setPalette->palette->colors*sizeof(gRGB));
		delete[] o->parm.setPalette->palette->data;
		delete o->parm.setPalette->palette;
		delete o->parm.setPalette;
		break;
	case gOpcode::mergePalette:
		pixmap->mergePalette(*o->parm.blit->pixmap);
		delete o->parm.blit;
		break;
	case gOpcode::line:
		pixmap->line(o->parm.line->start, o->parm.line->end, o->parm.line->color);
		delete o->parm.line;
		break;
	case gOpcode::clip:
		clip=o->parm.clip->clip;
		delete o->parm.clip;
		break;
	case gOpcode::end:
		unlock();
	case gOpcode::flush:
		break;
	default:
		eFatal("illegal opcode %d. expect memory leak!", o->opcode);
	}
}

gRGB gPixmapDC::getRGB(gColor col)
{
	if ((!pixmap) || (!pixmap->clut.data))
		return gRGB(col, col, col);
	if (col<0)
	{
		eFatal("bla transp");
		return gRGB(0, 0, 0, 0xFF);
	}
	return pixmap->clut.data[col];
}

eAutoInitP0<gRC> init_grc(eAutoInitNumbers::graphic, "gRC");
