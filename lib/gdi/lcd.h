#ifndef __lcd_h
#define __lcd_h

#include <asm/types.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/erect.h>

#define LCD_CONTRAST_MIN 0
#define LCD_CONTRAST_MAX 63
#define LCD_BRIGHTNESS_MIN 0
#define LCD_BRIGHTNESS_MAX 255

class eLCD
{
#ifdef SWIG
	eLCD();
	~eLCD();
#else
protected:
	void setSize(int xres, int yres, int bpp);
	eSize res;
	unsigned char *_buffer;
	int lcdfd;
	int _stride;
	int locked;
#endif
public:
	int lock();
	void unlock();
	int islocked() { return locked; }
	bool detected() { return lcdfd >= 0; }
#ifndef SWIG
	eLCD();
	virtual ~eLCD();
	__u8 *buffer() { return (__u8*)_buffer; }
	int stride() { return _stride; }
	eSize size() { return res; }
	virtual void update()=0;
#endif
};

class eDBoxLCD: public eLCD
{
	static eDBoxLCD *instance;
	unsigned char inverted;
	int is_oled;
#ifdef SWIG
	eDBoxLCD();
	~eDBoxLCD();
#endif
public:
#ifndef SWIG
	eDBoxLCD();
	~eDBoxLCD();
#endif
	static eDBoxLCD *getInstance();
	int setLCDContrast(int contrast);
	int setLCDBrightness(int brightness);
	void setInverted( unsigned char );
	bool isOled() const { return !!is_oled; }
	void update();
};

#endif
