#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "grc.h"

class gFBDC: public gPixmapDC
{
	fbClass *fb;
	static gFBDC *instance;
	void exec(gOpcode *opcode);
	unsigned char ramp[256], rampalpha[256]; // RGB ramp 0..255
	int brightness, gamma, alpha;
	void calcRamp();
	void setPalette();
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
	~gFBDC();
	static gFBDC *getInstance();
};


#endif
