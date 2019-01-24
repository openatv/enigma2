#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "gmaindc.h"

#ifndef SWIG
class gFBDC: public gMainDC
{
	fbClass *fb;
	int brightness, gamma, alpha;
	gUnmanagedSurface surface;
	gUnmanagedSurface surface_back;
	unsigned char ramp[256], rampalpha[256]; // RGB ramp 0..255
	void exec(const gOpcode *opcode);
	void calcRamp();
	void setPalette();
public:
	void setResolution(int xres, int yres, int bpp = 32);
	void reloadSettings();
	void setAlpha(int alpha);
	void setBrightness(int brightness);
	void setGamma(int gamma);

	int getAlpha() const { return alpha; }
	int getBrightness() const { return brightness; }
	int getGamma() const { return gamma; }

	int haveDoubleBuffering() const { return surface_back.data_phys != 0; }

	void saveSettings();

	gFBDC();
	virtual ~gFBDC();
	int islocked() const { return fb->islocked(); }
};
#endif
#ifdef HAVE_OSDANIMATION
void setAnimation_current(int a);
void setAnimation_speed(int speed);
void setAnimation_current_listbox(int a);
#endif

#endif
