#include <lib/gdi/lcd.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <dbox/fp.h>
#include <dbox/lcd-ks0713.h>

#include <lib/gdi/esize.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#ifdef HAVE_TEXTLCD
	#include <lib/base/estring.h>
#endif
#include <lib/gdi/glcddc.h>

eDBoxLCD *eDBoxLCD::instance;

eLCD::eLCD(eSize size): res(size)
{
	lcdfd = -1;
	locked=0;
	_buffer=new unsigned char[res.height()*res.width()];
	memset(_buffer, 0, res.height()*res.width());
	_stride=res.width();
}

eLCD::~eLCD()
{
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
	std::string message = text;
	message = replace_all(message, "\n", " ");
	::write(lcdfd, message.c_str(), message.size());
}
#endif

eDBoxLCD::eDBoxLCD(): eLCD(eSize(132, 64))
{
	is_oled = 0;
#ifndef NO_LCD
	lcdfd = open("/dev/dbox/oled0", O_RDWR);
	if (lcdfd < 0)
	{
		FILE *f=fopen("/proc/stb/fp/oled_brightness", "w");
		if (f)
		{
			is_oled = 2;
			fclose(f);
		}
		lcdfd = open("/dev/dbox/lcd0", O_RDWR);
	} else
	{
		eDebug("found OLED display!");
		is_oled = 1;
	}
#else
	lcdfd = -1;
#endif
	instance=this;

	if (lcdfd<0)
		eDebug("couldn't open LCD - load lcd.o!");
	else
	{
		int i=LCD_MODE_BIN;
		ioctl(lcdfd, LCD_IOCTL_ASC_MODE, &i);
		inverted=0;
	}
}

void eDBoxLCD::setInverted(unsigned char inv)
{
	inverted=inv;
	update();	
}

int eDBoxLCD::setLCDContrast(int contrast)
{
	int fp;
	if((fp=open("/dev/dbox/fp0", O_RDWR))<=0)
	{
		eDebug("[LCD] can't open /dev/dbox/fp0");
		return(-1);
	}

	if(ioctl(lcdfd, LCD_IOCTL_SRV, &contrast))
	{
		eDebug("[LCD] can't set lcd contrast");
	}
	close(fp);
	return(0);
}

int eDBoxLCD::setLCDBrightness(int brightness)
{
	eDebug("setLCDBrightness %d", brightness);
	FILE *f=fopen("/proc/stb/fp/oled_brightness", "w");
	if (f)
	{
		if (fprintf(f, "%d", brightness) == 0)
			eDebug("write /proc/stb/fp/oled_brightness failed!! (%m)");
		fclose(f);
	}
	else
	{
		int fp;
		if((fp=open("/dev/dbox/fp0", O_RDWR))<=0)
		{
			eDebug("[LCD] can't open /dev/dbox/fp0");
			return(-1);
		}

		if(ioctl(fp, FP_IOCTL_LCD_DIMM, &brightness)<=0)
			eDebug("[LCD] can't set lcd brightness (%m)");
		close(fp);
	}
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

eDBoxLCD *eDBoxLCD::getInstance()
{
	return instance;
}

void eDBoxLCD::update()
{
	if (!is_oled || is_oled == 2)
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
				raw[y*132+x]=(pix^inverted);
			}
		}
		if (lcdfd >= 0)
			write(lcdfd, raw, 132*8);
	} else
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
				raw[y*64+x] = pix;
			}
		}
		if (lcdfd >= 0)
			write(lcdfd, raw, 64*64);
	}
}

