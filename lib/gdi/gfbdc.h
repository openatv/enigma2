#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "grc.h"

class gFBDC: public gDC
{
	fbClass *fb;
	static gFBDC *instance;
	void exec(gOpcode *opcode);
	unsigned char ramp[256], rampalpha[256]; // RGB ramp 0..255
	int brightness, gamma, alpha;
	void calcRamp();
	void setPalette();
	gSurface surface;
public:
	void reloadSettings();
	void setAlpha(int alpha);
	void setBrightness(int brightness);
	void setGamma(int gamma);
	
	int getAlpha() { return alpha; }
	int getBrightness() { return brightness; }
	int getGamma() { return gamma; }
	
	void saveSettings();
	
	gFBDC();
	virtual ~gFBDC();
	static int getInstance(ePtr<gFBDC> &ptr) { if (!instance) return -1; ptr = instance; return 0; }
	int islocked() { return fb->islocked(); }
};


#endif
