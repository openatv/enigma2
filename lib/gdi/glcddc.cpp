#include <lib/gdi/glcddc.h>
#include <lib/gdi/lcd.h>
#include <lib/gdi/fblcd.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/epng.h>

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
	eDebug("[gLCDDC] resolution: %dx%dx%d stride=%d", surface.x, surface.y, surface.bpp, surface.stride);

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
	{
		eDebug("[gLCDDC] LCD flush");
		int bpp = m_pixmap->surface->bpp;
		switch(bpp)
		{
			case 8:
				eDebug("[gLCDDC] 8 bit not supported yet");
				break;
			case 16:
				{
					int lcd_width = m_pixmap->surface->x;
					int lcd_hight = m_pixmap->surface->y;

					ePtr<gPixmap> pixmap32;
					pixmap32 = new gPixmap(eSize(lcd_width, lcd_hight), 32, gPixmap::accelAuto);

					const uint8_t *srcptr = (uint8_t*)m_pixmap->surface->data;
					uint8_t *dstptr=(uint8_t*)pixmap32->surface->data;

					for (int y = lcd_hight; y != 0; --y)
					{
						gRGB pixel32;
						uint16_t pixel16;
						int x = lcd_width;
						gRGB *dst = (gRGB *)dstptr;
						const uint16_t *src = (const uint16_t *)srcptr;
						while (x--)
						{
#if BYTE_ORDER == LITTLE_ENDIAN
							pixel16 = bswap_16(*src++);
#else
							pixel16 = *src++;;
#endif
							pixel32.a = 0xFF;
							pixel32.r = (pixel16 << 3) & 0xF8;
							pixel32.g = (pixel16 >> 3) & 0xFC;
							pixel32.b = (pixel16 >> 8) & 0xF8;
							*dst++ = pixel32;
						}
						srcptr += m_pixmap->surface->stride;
						dstptr += pixmap32->surface->stride;
					}
					savePNG("/tmp/lcd.png", pixmap32);
				}
				break;
			case 32:
				savePNG("/tmp/lcd.png", m_pixmap);
				break;
			default:
				eDebug("[gLCDDC] %d bit not supported yet",bpp);
		}
		lcd->update();
	}
	default:
		gDC::exec(o);
		break;
	}
}

void gLCDDC::setUpdate(int u)
{
	update = u;
}

eAutoInitPtr<gLCDDC> init_gLCDDC(eAutoInitNumbers::graphic-1, "gLCD");
