#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "grc.h"

class gFBDC;

SWIG_TEMPLATE_TYPEDEF(ePtr<gFBDC>, gFBDCPtr);

class gFBDC: public gDC
{
#ifndef SWIG
	fbClass *fb;
	static gFBDC *instance;
	void exec(gOpcode *opcode);
	unsigned char ramp[256], rampalpha[256]; // RGB ramp 0..255
	int brightness, gamma, alpha;
	void calcRamp();
	void setPalette();
	gSurface surface, surface_back;
	int m_enable_double_buffering;
	int m_xres, m_yres;
#endif
public:
	void reloadSettings();
	void setAlpha(int alpha);
	void setBrightness(int brightness);
	void setGamma(int gamma);

	int getAlpha() { return alpha; }
	int getBrightness() { return brightness; }
	int getGamma() { return gamma; }

	int haveDoubleBuffering() { return m_enable_double_buffering; }

	void setResolution(int xres, int yres);

	void saveSettings();

	gFBDC();
	virtual ~gFBDC();
	static SWIG_VOID(int) getInstance(ePtr<gFBDC> &SWIG_NAMED_OUTPUT(ptr)) { if (!instance) return -1; ptr = instance; return 0; }
	int islocked() { return fb->islocked(); }
};

#endif
