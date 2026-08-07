#ifndef __gfbdc_h
#define __gfbdc_h

#include "fb.h"
#include "gpixmap.h"
#include "gmaindc.h"

#ifndef SWIG
#include <mutex>

class gFBDC: public gMainDC
{
	fbClass *fb;
	int brightness, gamma, alpha;
	gUnmanagedSurface surface;
	gUnmanagedSurface surface_back;
	gUnmanagedSurface surface_third;
	int m_number_of_pages = 1;
	bool m_graphics_suspended = false;
	mutable std::recursive_mutex m_graphics_mutex;
	unsigned char ramp[256], rampalpha[256]; // RGB ramp 0..255
	void exec(const gOpcode *opcode);
	void calcRamp();
	void setPalette();
	void rotateSurfaces();
	int getSurfaceOffset(const gUnmanagedSurface &s) const;
public:
	void setResolution(int xres, int yres, int bpp = 32);
	bool suspendGraphics() override;
	bool resumeGraphics() override;
	bool isGraphicsSuspended() const override;
	void reloadSettings();
	void setAlpha(int alpha);
	void setBrightness(int brightness);
	void setGamma(int gamma);

	int getAlpha() const { return alpha; }
	int getBrightness() const { return brightness; }
	int getGamma() const { return gamma; }

	int haveDoubleBuffering() const { return surface_back.data_phys != 0; }
	std::string getGraphicsBackend() const override { return "framebuffer"; }
	std::string getGraphicsAccelerator() const override;
	std::string getGraphicsBuffering() const override;
	int getGraphicsBufferPages() const override { return m_number_of_pages; }
	bool getGraphicsHardwareAccelerated() const override;

	void saveSettings();

	gFBDC();
	virtual ~gFBDC();
	int islocked() const { return fb->islocked(); }
};
#endif
#endif
