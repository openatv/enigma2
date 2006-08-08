#include <lib/gdi/lcd.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <dbox/fp.h>
#include <dbox/lcd-ks0713.h>

#include <lib/gdi/esize.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/glcddc.h>

eDBoxLCD *eDBoxLCD::instance;

eLCD::eLCD(eSize size): res(size)
{
	locked=0;
	_buffer=new unsigned char[res.height()*res.width()];
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
	read( lcdfd, NULL, 0);
	if ( errno == 9 )
	{
		eDebug("reopen lcd");
		lcdfd=open("/dev/dbox/lcd0", O_RDWR);  // reopen device
	}
	else
		eDebug("do not reopen lcd.. errno = %d", errno);
    
	locked=0;
}

eDBoxLCD::eDBoxLCD(): eLCD(eSize(132, 64))
{
#ifndef NO_LCD
	lcdfd = open("/dev/dbox/oled0", O_RDWR);
	if (lcdfd < 0)
	{
		lcdfd = open("/dev/dbox/lcd0", O_RDWR);
		is_oled = 0;
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
	int fp;
	if((fp=open("/dev/dbox/fp0", O_RDWR))<=0)
	{
		eDebug("[LCD] can't open /dev/dbox/fp0");
		return(-1);
	}

	if(ioctl(fp, FP_IOCTL_LCD_DIMM, &brightness))
	{
		eDebug("[LCD] can't set lcd brightness");
	}
	close(fp);
	return(0);
}

eDBoxLCD::~eDBoxLCD()
{
	if (lcdfd>0)
	{
		close(lcdfd);
		lcdfd=0;
	}
}

eDBoxLCD *eDBoxLCD::getInstance()
{
	return instance;
}

void eDBoxLCD::update()
{
	if (!is_oled)
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
		if (lcdfd>0)
			write(lcdfd, raw, 132*8);
	} else
	{
		unsigned char raw[64*64];
		int x, y;
		memset(raw, 0, 64*64);
		for (y=0; y<64; y++)
		{
			for (x=0; x<128 / 2; x++)
				raw[y*64+x] = (_buffer[y*132 + x * 2 + 2] & 0xF0) |(_buffer[y*132 + x * 2 + 1 + 2] >> 4);
		}
		if (lcdfd > 0)
			write(lcdfd, raw, 64*64);
	}
}

