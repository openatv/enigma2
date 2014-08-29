#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "gmaindc.h"

// #define DEBUG_FBDC

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

	int getAlpha() const {
#ifdef DEBUG_FBDC
		eDebug("[gFBDC] %s", __FUNCTION__);
#endif
		return alpha;
	}
	int getBrightness() const {
#ifdef DEBUG_FBDC
		eDebug("[gFBDC] %s", __FUNCTION__);
#endif
		return brightness;
	}
	int getGamma() const {
#ifdef DEBUG_FBDC
		eDebug("[gFBDC] %s", __FUNCTION__);
#endif
		return gamma;
	}

	int haveDoubleBuffering() const {
#ifdef DEBUG_FBDC
		eDebug("[gFBDC] %s", __FUNCTION__);
#endif
		return surface_back.data_phys != 0;
	}

	void saveSettings();

	gFBDC();
	virtual ~gFBDC();
	int islocked() const {
#ifdef DEBUG_FBDC
		eDebug("[gFBDC] %s", __FUNCTION__);
#endif
		return fb->islocked();
	}
};

#endif
