#if 0
#ifndef DISABLE_LCD

#include <lib/gdi/lcd.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <dbox/fp.h>
#include <dbox/lcd-ks0713.h>

#include <lib/base/esize.h>
#include <lib/system/init.h>
#include <lib/system/init_num.h>
#include <lib/gdi/glcddc.h>
#include <lib/system/econfig.h>

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

/* void eLCD::line(ePoint start, ePoint dst, int color)
{
int Ax=start.x(), // dieser code rult ganz ganz doll weil er ganz ganz fast ist und auch sehr gut dokumentiert is
Ay=start.y(), Bx=dst.x(), // t. es handelt sich immerhin um den weltbekannten bresenham algorithmus der nicht nur
By=dst.y(); int dX, dY, fbXincr, // sehr schnell ist sondern auch sehr gut dokumentiert und getestet wurde. nicht
fbYincr, fbXYincr, dPr, dPru, P; __u8 // nur auf dem LCD der dbox, sondern auch ueberall anders. und auch auf der
*AfbAddr = &buffer()[Ay*stride()+Ax]; __u8 // dbox mit LCD soll das teil nun tun, und ich denke das tut es. ausse
*BfbAddr = &buffer()[By*stride()+Bx]; fbXincr= // rdem hat dieser algo den vorteil dass man fehler sehr leicht fi
1; if ( (dX=Bx-Ax) >= 0) goto AFTERNEGX; dX=-dX; // ndet und beheben kann. das liegt nicht zuletzt an den komment
fbXincr=-1; AFTERNEGX: fbYincr=stride(); if ( (dY=By // aren. und ausserdem, je kuerzer der code, desto weniger k
-Ay) >= 0) goto AFTERNEGY; fbYincr=-stride(); dY=-dY;AFTERNEGY: // ann daran falsch sein. erwaehnte ich schon, da
fbXYincr = fbXincr+fbYincr; if (dY > dX) goto YisIndependent; dPr = dY+ // s dieser tolle code wahnsinnig schnell
dY; P = -dX; dPru = P+P; dY = dX>>1; XLOOP: *AfbAddr=color; *BfbAddr=color; if ((P+=dPr) > 0) // ist? bye, tmbinc
goto RightAndUp;  AfbAddr+=fbXincr; BfbAddr-=fbXincr; if ((dY=dY-1) > 0) goto XLOOP; *AfbAddr=color; if ((dX & 1)
== 0) return;  *BfbAddr=color; return; RightAndUp: AfbAddr+=fbXYincr; BfbAddr-=fbXYincr; P+=dPru; if ((dY=dY-1) >
0) goto XLOOP;  *AfbAddr=color; if ((dX & 1) == 0) return; *BfbAddr=color; return; YisIndependent: dPr = dX+dX; P
= -dY; dPru = P+P; dX = dY>>1; YLOOP: *AfbAddr=color; *BfbAddr=color; if ((P+=dPr) > 0) goto RightAndUp2; AfbAddr
+=fbYincr;  BfbAddr-=fbYincr; if ((dX=dX-1) > 0) goto YLOOP; *AfbAddr=color; if ((dY & 1) == 0) return; *BfbAddr=
color;return; RightAndUp2: AfbAddr+=fbXYincr; BfbAddr-=fbXYincr; P+=dPru; if ((dX=dX-1) > 0) goto YLOOP; *AfbAddr
=color; if((dY & 1) == 0) return; *BfbAddr=color; return; // nun ist der tolle code leider zu ende. tut mir leid.
} */

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
		int lcdbrightness=0, lcdcontrast=0;

		if( eConfig::getInstance()->getKey("/ezap/lcd/brightness", lcdbrightness) )
		{
			lcdbrightness=130;
			eConfig::getInstance()->setKey("/ezap/lcd/brightness", lcdbrightness);
		}
		if( eConfig::getInstance()->getKey("/ezap/lcd/contrast", lcdcontrast) )
		{
			lcdcontrast=32;
			eConfig::getInstance()->setKey("/ezap/lcd/contrast", lcdcontrast);
		}
		setLCDParameter(lcdbrightness, lcdcontrast);
		int tmp;
		if( eConfig::getInstance()->getKey("/ezap/lcd/inverted", tmp ) )
		{
			inverted=0;
			eConfig::getInstance()->setKey("/ezap/lcd/inverted", (int) 0 );
		}
		else
			inverted=(unsigned char)tmp;
	}
}

void eDBoxLCD::setInverted(unsigned char inv)
{
	inverted=inv;
	update();	
}

int eDBoxLCD::setLCDParameter(int brightness, int contrast)
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

	if(ioctl(fp, FP_IOCTL_LCD_DIMM, &brightness))
	{
		eDebug("[LCD] can't set lcd brightness");
	}
	eDebug("[LCD] set brightness %d, contrast %d", brightness, contrast);
	return(0);
}

int eDBoxLCD::switchLCD(int state)
{
	int lcdbrightness, lcdcontrast, lcdstandby=0;

	eConfig::getInstance()->getKey("/ezap/lcd/contrast", lcdcontrast);

	if(state==0)
	{
		eConfig::getInstance()->getKey("/ezap/lcd/standby", lcdstandby);
		setLCDParameter(lcdstandby, lcdcontrast);
	}
	else
	{
		eConfig::getInstance()->getKey("/ezap/lcd/brightness", lcdbrightness);
		setLCDParameter(lcdbrightness, lcdcontrast);
		
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

class eDBoxLCDHardware
{
	eDBoxLCD lcd;
	gLCDDC lcddc;
public:
	eDBoxLCDHardware(): lcddc(&lcd)
	{
	}
};

eAutoInitP0<eDBoxLCDHardware> init_eDBoxLCDHardware(eAutoInitNumbers::lowlevel, "d-Box LCD Hardware");

#endif //DISABLE_LCD

#endif
