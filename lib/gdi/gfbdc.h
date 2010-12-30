#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "gmaindc.h"

class gFBDC: public gMainDC
{
	fbClass *fb;
	void exec(const gOpcode *opcode);
	unsigned char ramp[256], rampalpha[256]; // RGB ramp 0..255
	int brightness, gamma, alpha;
	void calcRamp();
	void setPalette();
	gSurface surface, surface_back;
	int m_enable_double_buffering;
	int m_xres, m_yres;
public:
	void setResolution(int xres, int yres);
	void reloadSettings();
	void setAlpha(int alpha);
	void setBrightness(int brightness);
	void setGamma(int gamma);

	int getAlpha() { return alpha; }
	int getBrightness() { return brightness; }
	int getGamma() { return gamma; }

	int haveDoubleBuffering() { return m_enable_double_buffering; }

	void saveSettings();

	gFBDC();
	virtual ~gFBDC();
	int islocked() { return fb->islocked(); }
};

#endif
