#include <lib/gdi/glcddc.h>
#include <lib/gdi/lcd.h>
#include <lib/gdi/fblcd.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

gLCDDC *gLCDDC::instance;

gLCDDC::gLCDDC()
{
	lcd = new eFbLCD();
	if (!lcd->detected())
	{
		delete lcd;
		lcd = new eDBoxLCD();
	}
	instance = this;

	update = 1;

	surface.x = lcd->size().width();
	surface.y = lcd->size().height();
	surface.stride = lcd->stride();
	surface.bypp = surface.stride / surface.x;
	surface.bpp = surface.bypp*8;
	surface.data = lcd->buffer();
	surface.data_phys = 0;
	if (lcd->getLcdType() == 4)
	{
		surface.clut.colors = 256;
		surface.clut.data = new gRGB[surface.clut.colors];
		memset(surface.clut.data, 0, sizeof(*surface.clut.data)*surface.clut.colors);
	}
	else
	{
		surface.clut.colors = 0;
		surface.clut.data = 0;
	}
	eDebug("LCD resolution: %d x %d x %d (stride: %d)", surface.x, surface.y, surface.bpp, surface.stride);

	m_pixmap = new gPixmap(&surface);
}

gLCDDC::~gLCDDC()
{
	delete lcd;
	if (surface.clut.data)
		delete[] surface.clut.data;
	instance = 0;
}

void gLCDDC::exec(const gOpcode *o)
{
	switch (o->opcode)
	{
	case gOpcode::setPalette:
	{
		gDC::exec(o);
		lcd->setPalette(surface);
		break;
	}
#ifdef HAVE_TEXTLCD
	case gOpcode::renderText:
		if (o->parm.renderText->text)
		{
			lcd->renderText(gDC::m_current_offset, o->parm.renderText->text);
			free(o->parm.renderText->text);
		}
		delete o->parm.renderText;
		break;
#endif
	case gOpcode::flush:
		lcd->update();
	default:
		gDC::exec(o);
		break;
	}
}

void gLCDDC::setUpdate(int u)
{
	update = u;
}

eAutoInitPtr<gLCDDC> init_gLCDDC(eAutoInitNumbers::graphic-1, "gLCDDC");
