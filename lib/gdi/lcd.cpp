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

eDBoxLCD::eDBoxLCD(): eLCD(eSize(128, 64))
{
#ifndef NO_LCD
	lcdfd=open("/dev/dbox/lcd0", O_RDWR);
#else
	lcdfd=-1;
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
	unsigned char raw[120*8];
	int x, y, yy;
	for (y=0; y<8; y++)
	{
		for (x=0; x<120; x++)
		{
			int pix=0;
			for (yy=0; yy<8; yy++)
			{
				pix|=(_buffer[(y*8+yy)*128+x]>=108)<<yy;
			}
			raw[y*120+x]=(pix^inverted);
		}
	}
	if (lcdfd>0)
		write(lcdfd, raw, 120*8);
}

