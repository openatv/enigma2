#ifndef DISABLE_LCD

#include <lib/gdi/glcddc.h>

gLCDDC *gLCDDC::instance;

gLCDDC::gLCDDC(eLCD *lcd): lcd(lcd)
{
	instance=this;
	
	update=1;

	surface.x=lcd->size().width();
	surface.y=lcd->size().height();
	surface.bpp=8;
	surface.bypp=1;
	surface.stride=lcd->stride();
	surface.data=lcd->buffer();

	surface.clut.colors=256;
	surface.clut.data=0;
	m_pixmap = new gPixmap(&surface);
}

gLCDDC::~gLCDDC()
{
	instance=0;
}

void gLCDDC::exec(gOpcode *o)
{
	switch (o->opcode)
	{
//	case gOpcode::flush:
	case gOpcode::end:
		if (update)
			lcd->update();
	default:
		gDC::exec(o);
		break;
	}
}

gLCDDC *gLCDDC::getInstance()
{
	return instance;
}

void gLCDDC::setUpdate(int u)
{
	update=u;
}

#endif //DISABLE_LCD
