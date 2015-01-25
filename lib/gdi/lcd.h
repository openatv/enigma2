#ifndef __lcd_h
#define __lcd_h

#include <asm/types.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/erect.h>
#include "gpixmap.h"

#define LCD_CONTRAST_MIN 0
#define LCD_CONTRAST_MAX 63
#define LCD_BRIGHTNESS_MIN 0
#define LCD_BRIGHTNESS_MAX 255

enum op { LED_BRIGHTNESS = 0, LED_DEEPSTANDBY, LED_BLINKINGTIME };

#define LED_IOCTL_BRIGHTNESS_NORMAL 0X10
#define LED_IOCTL_BRIGHTNESS_DEEPSTANDBY 0X11
#define LED_IOCTL_BLINKING_TIME 0X12
#define LED_IOCTL_SET_DEFAULT 0x13

class eLCD
{
#ifdef SWIG
	eLCD();
	~eLCD();
#else
protected:
	eSize res;
	int lcd_type;
	unsigned char *_buffer;
	int lcdfd;
	int _stride;
	int locked;
	static eLCD *instance;
	void setSize(int xres, int yres, int bpp);
#endif
public:
	static eLCD *getInstance();
	virtual int lock();
	virtual void unlock();
	virtual int islocked() { return locked; };
	virtual bool detected() { return lcdfd >= 0; };
	virtual int setLCDContrast(int contrast)=0;
	virtual int setLCDBrightness(int brightness)=0;
	virtual void setInverted( unsigned char )=0;
	virtual void setFlipped(bool)=0;
	virtual int waitVSync()=0;
	virtual bool isOled() const=0;
	int getLcdType() { return lcd_type; };
	virtual void setPalette(gUnmanagedSurface)=0;
	virtual int setLED(int value, int option)=0;
#ifndef SWIG
	eLCD();
	virtual ~eLCD();
	uint8_t *buffer() { return (uint8_t*)_buffer; };
	int stride() { return _stride; };
	virtual eSize size() { return res; };
	virtual void update()=0;
#ifdef HAVE_TEXTLCD
	virtual void renderText(ePoint start, const char *text);
#endif
#endif
};

class eDBoxLCD: public eLCD
{
	unsigned char inverted;
	bool flipped;
#ifdef SWIG
	eDBoxLCD();
	~eDBoxLCD();
#endif
public:
#ifndef SWIG
	eDBoxLCD();
	~eDBoxLCD();
#endif
	int setLCDContrast(int contrast);
	int setLCDBrightness(int brightness);
	void setInverted( unsigned char );
	void setFlipped(bool);
	int setLED(int value, int option);
	bool isOled() const { return !!lcd_type; };
	void setPalette(gUnmanagedSurface) {};
	void update();
	int waitVSync() { return 0; };
};

#endif
