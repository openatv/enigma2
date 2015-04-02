#include <lib/gdi/lcd.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/gdi/esize.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#ifdef HAVE_TEXTLCD
	#include <lib/base/estring.h>
#endif
#include <lib/gdi/glcddc.h>

eLCD *eLCD::instance;

eLCD::eLCD()
{
	lcdfd = -1;
	locked=0;
	instance = this;
}

eLCD *eLCD::getInstance()
{
	return instance;
}

void eLCD::setSize(int xres, int yres, int bpp)
{
	res = eSize(xres, yres);
	_buffer=new unsigned char[xres * yres * bpp/8];
	memset(_buffer, 0, res.height()*res.width()*bpp/8);
	_stride=res.width()*bpp/8;
	eDebug("[eLCD] (%dx%dx%d) buffer %p %d bytes, stride %d", xres, yres, bpp, _buffer, xres*yres*bpp/8, _stride);
}

eLCD::~eLCD()
{
	if (_buffer)
		delete [] _buffer;
}

int eLCD::lock()
{
	if (locked)
		return -1;

	locked=1;
	return lcdfd;
}

void eLCD::unlock()
{
	locked=0;
}

#ifdef HAVE_TEXTLCD
void eLCD::renderText(ePoint start, const char *text)
{
	if (lcdfd >= 0 && start.y() < 5)
	{
		std::string message = text;
		message = replace_all(message, "\n", " ");
		::write(lcdfd, message.c_str(), message.size());
	}
}
#endif

eDBoxLCD::eDBoxLCD()
{
	int xres=132, yres=64, bpp=8;
	flipped = false;
	inverted = 0;
	lcd_type = 0;
#ifndef NO_LCD
	lcdfd = open("/dev/dbox/oled0", O_RDWR);
	if (lcdfd < 0)
	{
		if (!access("/proc/stb/lcd/oled_brightness", W_OK) ||
		    !access("/proc/stb/fp/oled_brightness", W_OK) )
			lcd_type = 2;
		lcdfd = open("/dev/dbox/lcd0", O_RDWR);
	} else
	{
		lcd_type = 1;
	}

	if (lcdfd < 0)
		eDebug("[eDboxLCD] No oled0 or lcd0 device found!");
	else
	{

#ifndef LCD_IOCTL_ASC_MODE
#define LCDSET                  0x1000
#define LCD_IOCTL_ASC_MODE	(21|LCDSET)
#define	LCD_MODE_ASC		0
#define	LCD_MODE_BIN		1
#endif

		int i=LCD_MODE_BIN;
		ioctl(lcdfd, LCD_IOCTL_ASC_MODE, &i);
		FILE *f = fopen("/proc/stb/lcd/xres", "r");
		if (f)
		{
			int tmp;
			if (fscanf(f, "%x", &tmp) == 1)
				xres = tmp;
			fclose(f);
			f = fopen("/proc/stb/lcd/yres", "r");
			if (f)
			{
				if (fscanf(f, "%x", &tmp) == 1)
					yres = tmp;
				fclose(f);
				f = fopen("/proc/stb/lcd/bpp", "r");
				if (f)
				{
					if (fscanf(f, "%x", &tmp) == 1)
						bpp = tmp;
					fclose(f);
				}
			}
			lcd_type = 3;
		}
		eDebug("[eDboxLCD] xres=%d, yres=%d, bpp=%d lcd_type=%d", xres, yres, bpp, lcd_type);
	}
#endif
	instance = this;

	setSize(xres, yres, bpp);
}

void eDBoxLCD::setInverted(unsigned char inv)
{
	inverted = inv;
	update();
}

void eDBoxLCD::setFlipped(bool onoff)
{
	flipped = onoff;
	update();
}

int eDBoxLCD::setLCDContrast(int contrast)
{
#ifndef NO_LCD

#ifndef LCD_IOCTL_SRV
#define LCDSET                  0x1000
#define	LCD_IOCTL_SRV			(10|LCDSET)
#endif
	eDebug("[eDboxLCD] setLCDContrast %d", contrast);

	int fp;
	if((fp=open("/dev/dbox/fp0", O_RDWR))<0)
	{
		eDebug("[eDboxLCD] can't open /dev/dbox/fp0: %m");
		return(-1);
	}

	if(ioctl(lcdfd, LCD_IOCTL_SRV, &contrast)<0)
		eDebug("[eDboxLCD] can't set lcd contrast: %m");
	close(fp);
#endif
	return(0);
}

int eDBoxLCD::setLCDBrightness(int brightness)
{
#ifndef NO_LCD
	eDebug("[eDboxLCD] setLCDBrightness %d", brightness);
	FILE *f=fopen("/proc/stb/lcd/oled_brightness", "w");
	if (!f)
		f = fopen("/proc/stb/fp/oled_brightness", "w");
	if (f)
	{
		if (fprintf(f, "%d", brightness) == 0)
			eDebug("[eDboxLCD] write /proc/stb/lcd/oled_brightness failed: %m");
		fclose(f);
	}
	else
	{
		int fp;
		if((fp=open("/dev/dbox/fp0", O_RDWR)) < 0)
		{
			eDebug("[eDboxLCD] can't open /dev/dbox/fp0: %m");
			return(-1);
		}
#ifndef FP_IOCTL_LCD_DIMM
#define FP_IOCTL_LCD_DIMM       3
#endif
		if(ioctl(fp, FP_IOCTL_LCD_DIMM, &brightness) < 0)
			eDebug("[eDboxLCD] can't set lcd brightness: %m");
		close(fp);
	}
#endif
	return(0);
}

eDBoxLCD::~eDBoxLCD()
{
	if (lcdfd>=0)
	{
		close(lcdfd);
		lcdfd=-1;
	}
}

void eDBoxLCD::update()
{
#ifndef HAVE_TEXTLCD
	if (lcdfd < 0)
		return;

	if (lcd_type == 0 || lcd_type == 2)
	{
		unsigned char raw[132*8];
		int x, y, yy;
		for (y=0; y<8; y++)
		{
			for (x=0; x<132; x++)
			{
				int pix=0;
				for (yy=0; yy<8; yy++)
				{
					pix|=(_buffer[(y*8+yy)*132+x]>=108)<<yy;
				}
				if (flipped)
				{
					/* 8 pixels per byte, swap bits */
#define BIT_SWAP(a) (( ((a << 7)&0x80) + ((a << 5)&0x40) + ((a << 3)&0x20) + ((a << 1)&0x10) + ((a >> 1)&0x08) + ((a >> 3)&0x04) + ((a >> 5)&0x02) + ((a >> 7)&0x01) )&0xff)
					raw[(7 - y) * 132 + (131 - x)] = BIT_SWAP(pix ^ inverted);
				}
				else
				{
					raw[y * 132 + x] = pix ^ inverted;
				}
			}
		}
		write(lcdfd, raw, 132*8);
	}
	else if (lcd_type == 3)
	{
		/* for now, only support flipping / inverting for 8bpp displays */
		if ((flipped || inverted) && _stride == res.width())
		{
			unsigned int height = res.height();
			unsigned int width = res.width();
			unsigned char raw[_stride * height];
			for (unsigned int y = 0; y < height; y++)
			{
				for (unsigned int x = 0; x < width; x++)
				{
					if (flipped)
					{
						/* 8bpp, no bit swapping */
						raw[(height - 1 - y) * width + (width - 1 - x)] = _buffer[y * width + x] ^ inverted;
					}
					else
					{
						raw[y * width + x] = _buffer[y * width + x] ^ inverted;
					}
				}
			}
			write(lcdfd, raw, _stride * height);
		}
		else
		{
			write(lcdfd, _buffer, _stride * res.height());
		}
	}
	else /* lcd_type == 1 */
	{
		unsigned char raw[64*64];
		int x, y;
		memset(raw, 0, 64*64);
		for (y=0; y<64; y++)
		{
			int pix=0;
			for (x=0; x<128 / 2; x++)
			{
				pix = (_buffer[y*132 + x * 2 + 2] & 0xF0) |(_buffer[y*132 + x * 2 + 1 + 2] >> 4);
				if (inverted)
					pix = 0xFF - pix;
				if (flipped)
				{
					/* device seems to be 4bpp, swap nibbles */
					unsigned char byte;
					byte = (pix >> 4) & 0x0f;
					byte |= (pix << 4) & 0xf0;
					raw[(63 - y) * 64 + (63 - x)] = byte;
				}
				else
				{
					raw[y * 64 + x] = pix;
				}
			}
		}
		write(lcdfd, raw, 64*64);
	}
#endif
}
