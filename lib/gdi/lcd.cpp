#include <lib/gdi/lcd.h>
#include <lib/gdi/epng.h>

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
	eDebug("lcd buffer %p %d bytes, stride %d", _buffer, xres*yres*bpp/8, _stride);
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
	dump = false;
	inverted = 0;
	lcd_type = 0;
	FILE *boxtype_file;
	char boxtype_name[20];
	FILE *fp_file;
	char fp_version[20];
#ifndef NO_LCD
	if((boxtype_file = fopen("/proc/stb/info/boxtype", "r")) != NULL)
	{
		fgets(boxtype_name, sizeof(boxtype_name), boxtype_file);
		fclose(boxtype_file);
		
		if((strcmp(boxtype_name, "7300S\n") == 0) || (strcmp(boxtype_name, "7400S\n") == 0) || (strcmp(boxtype_name, "xp1000s\n") == 0) || (strcmp(boxtype_name, "odinm7\n") == 0) || (strcmp(boxtype_name, "ew7358\n") == 0) || (strcmp(boxtype_name, "ew7362\n") == 0) || (strcmp(boxtype_name, "formuler3\n") == 0) || (strcmp(boxtype_name, "formuler4\n") == 0) || (strcmp(boxtype_name, "hd1100\n") == 0) || (strcmp(boxtype_name, "hd1200\n") == 0) || (strcmp(boxtype_name, "hd1265\n") == 0) || (strcmp(boxtype_name, "hd500c\n") == 0) || (strcmp(boxtype_name, "vp7358ci\n") == 0) || (strcmp(boxtype_name, "vg2000\n") == 0) || (strcmp(boxtype_name, "vg5000\n") == 0) || (strcmp(boxtype_name, "sh1\n") == 0) || (strcmp(boxtype_name, "yhgd2580\n") == 0) || (strcmp(boxtype_name, "spycatmini\n") == 0) || (strcmp(boxtype_name, "fegasusx3\n") == 0) || (strcmp(boxtype_name, "fegasusx5s\n") == 0) || (strcmp(boxtype_name, "fegasusx5t\n") == 0) || (strcmp(boxtype_name, "ini-2000oc\n") == 0) || (strcmp(boxtype_name, "osmini\n") == 0) || (strcmp(boxtype_name, "jj7362\n") == 0) || (strcmp(boxtype_name, "h3\n") == 0) || (strcmp(boxtype_name, "9900lx\n") == 0) || (strcmp(boxtype_name, "lc\n") == 0) || (strcmp(boxtype_name, "hd1500\n") == 0))
		{
			lcdfd = open("/dev/null", O_RDWR);
		}
		else if((strcmp(boxtype_name, "ini-1000de\n") == 0) || (strcmp(boxtype_name, "ini-2000am\n") == 0))
		{
				if((fp_file = fopen("/proc/stb/fp/version", "r")) != NULL)
				{
					fgets(fp_version, sizeof(fp_version), fp_file);
					fclose(fp_file);
				}
				if(strcmp(fp_version, "0\n") == 0) 
				{
					lcdfd = open("/dev/null", O_RDWR);
				}
				else
				{
					lcdfd = open("/dev/dbox/oled0", O_RDWR);
				}
		}
		else if((strcmp(boxtype_name, "spark\n") == 0))
		{
				if((fp_file = fopen("/proc/stb/fp/version", "r")) != NULL)
				{
					fgets(fp_version, sizeof(fp_version), fp_file);
					fclose(fp_file);
				}
				if(strcmp(fp_version, "4\n") == 0)
				{
					lcdfd = open("/dev/null", O_RDWR);
				}
				else
				{
					lcdfd = open("/dev/dbox/oled0", O_RDWR);
				}
		}		
		else
		{
			lcdfd = open("/dev/dbox/oled0", O_RDWR);
		}		
	}	
	else
	{
		lcdfd = open("/dev/dbox/oled0", O_RDWR);
	}
	
	if (lcdfd < 0)
	{
		if (!access("/proc/stb/lcd/oled_brightness", W_OK) || !access("/proc/stb/fp/oled_brightness", W_OK) )
			lcd_type = 2;
		lcdfd = open("/dev/dbox/lcd0", O_RDWR);
	} else
	{
		eDebug("found OLED display!");
		lcd_type = 1;
	}

	if (lcdfd < 0)
		eDebug("couldn't open LCD - load lcd.ko!");
	else
	{

#ifndef LCD_IOCTL_ASC_MODE
#define LCDSET                  0x1000
#define LCD_IOCTL_ASC_MODE		(21|LCDSET)
#define	LCD_MODE_ASC			0
#define	LCD_MODE_BIN			1
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
	}
#endif
	if (FILE * file = fopen("/proc/stb/lcd/right_half", "w"))
	{
		fprintf(file,"skin");
		fclose(file);
	}
	instance=this;

	setSize(xres, yres, bpp);
}

void eDBoxLCD::setInverted(unsigned char inv)
{
	inverted=inv;
	update();
}

void eDBoxLCD::setFlipped(bool onoff)
{
	flipped = onoff;
	update();
}

void eDBoxLCD::setDump(bool onoff)
 {
 	dump = onoff;
 	dumpLCD2PNG();
 }
 
int eDBoxLCD::setLCDContrast(int contrast)
{
#ifndef NO_LCD

#ifndef LCD_IOCTL_SRV
#define LCDSET                  0x1000
#define	LCD_IOCTL_SRV			(10|LCDSET)
#endif

	int fp;
	if((fp=open("/dev/dbox/fp0", O_RDWR))<0)
	{
		eDebug("[LCD] can't open /dev/dbox/fp0");
		return(-1);
	}

	if(ioctl(lcdfd, LCD_IOCTL_SRV, &contrast)<0)
	{
		eDebug("[LCD] can't set lcd contrast");
	}
	close(fp);
#endif
	return(0);
}

int eDBoxLCD::setLCDBrightness(int brightness)
{
#ifndef NO_LCD
//	eDebug("setLCDBrightness %d", brightness);
	FILE *f=fopen("/proc/stb/lcd/oled_brightness", "w");
	if (!f)
		f = fopen("/proc/stb/fp/oled_brightness", "w");
	if (f)
	{
		if (fprintf(f, "%d", brightness) == 0)
			eDebug("write /proc/stb/lcd/oled_brightness failed!! (%m)");
		fclose(f);
	}
	else
	{
		int fp;
		if((fp=open("/dev/dbox/fp0", O_RDWR)) < 0)
		{
			eDebug("[LCD] can't open /dev/dbox/fp0");
			return(-1);
		}
#ifndef FP_IOCTL_LCD_DIMM
#define FP_IOCTL_LCD_DIMM       3
#endif
		if(ioctl(fp, FP_IOCTL_LCD_DIMM, &brightness) < 0)
			eDebug("[LCD] can't set lcd brightness");
		close(fp);
	}
#endif
	return(0);
}

int eDBoxLCD::setLED(int value, int option)
{
	switch(option)
	{
		case LED_BRIGHTNESS:
			eDebug("setLEDNormalState %d", value);
			if(ioctl(lcdfd, LED_IOCTL_BRIGHTNESS_NORMAL, (unsigned char)value) < 0)
				eDebug("[LED] can't set led brightness");
			break;
		case LED_DEEPSTANDBY:
			eDebug("setLEDBlinkingTime %d", value);
			if(ioctl(lcdfd, LED_IOCTL_BRIGHTNESS_DEEPSTANDBY, (unsigned char)value) < 0)
				eDebug("[LED] can't set led deep standby");
			break;
		case LED_BLINKINGTIME:
			eDebug("setLEDBlinkingTime %d", value);
			if(ioctl(lcdfd, LED_IOCTL_BLINKING_TIME, (unsigned char)value) < 0)
				eDebug("[LED] can't set led blinking time");
			break;
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

void eDBoxLCD::dumpLCD2PNG(void)
 {
 		if (dump)
 		{
 			int bpp =( _stride *8)/res.width();
 			int lcd_width = res.width();
 			int lcd_hight = res.height();
 			ePtr<gPixmap> pixmap32;
 			pixmap32 = new gPixmap(eSize(lcd_width, lcd_hight), 32, gPixmap::accelAuto);
 			const uint8_t *srcptr = (uint8_t*)_buffer;
 			uint8_t *dstptr=(uint8_t*)pixmap32->surface->data;
 
 			switch(bpp)
 			{
 				case 8:
 					eDebug(" 8 bit not supportet yet");
 					break;
 				case 16:
 					{
 
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
 							srcptr += _stride;
 							dstptr += pixmap32->surface->stride;
 						}
 						savePNG("/tmp/lcd.png", pixmap32);
 					}
 					break;
 				case 32:
 					eDebug(" 32 bit not supportet yet");
 					break;
 				default:
 					eDebug("%d bit not supportet yet",bpp);
 			}
 		}
 }
 
void eDBoxLCD::update()
{
#ifndef HAVE_TEXTLCD
	if (lcdfd >= 0)
	{
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
				FILE *file;
				FILE *boxtype_file;
				char boxtype_name[20];
				if((boxtype_file = fopen("/proc/stb/info/boxtype", "r")) != NULL)
				{
					fgets(boxtype_name, sizeof(boxtype_name), boxtype_file);
					fclose(boxtype_file);
				}
				if (((file = fopen("/proc/stb/info/gbmodel", "r")) != NULL ) || (strcmp(boxtype_name, "7100S\n") == 0))
				{
					//gggrrrrrbbbbbggg bit order from memory
					//gggbbbbbrrrrrggg bit order to LCD
					unsigned char gb_buffer[_stride * res.height()];
					if(! (0x03 & (_stride * res.height())))
					{//fast
						for (int offset = 0; offset < ((_stride * res.height())>>2); offset ++)
						{
							unsigned int src = ((unsigned int*)_buffer)[offset];
							((unsigned int*)gb_buffer)[offset] = src & 0xE007E007 | (src & 0x1F001F00) >>5 | (src & 0x00F800F8) << 5;
						}
					}
					else
					{//slow
						for (int offset = 0; offset < _stride * res.height(); offset += 2)
						{
							gb_buffer[offset] = (_buffer[offset] & 0x07) | ((_buffer[offset + 1] << 3) & 0xE8);
							gb_buffer[offset + 1] = (_buffer[offset + 1] & 0xE0)| ((_buffer[offset] >> 3) & 0x1F);
						}
					}
					write(lcdfd, gb_buffer, _stride * res.height());
					if (file != NULL)
					{
						fclose(file);
					}
				}
				else
				{
					write(lcdfd, _buffer, _stride * res.height());
				}
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
	}
	dumpLCD2PNG();
#endif
}
