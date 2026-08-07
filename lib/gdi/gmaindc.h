#ifndef __lib_gdi_gmaindc_h
#define __lib_gdi_gmaindc_h

#include "grc.h"
#include <string>

class gMainDC;

SWIG_IGNORE(gMainDC);
class gMainDC: public gDC
{
protected:
	static gMainDC *m_instance;

	gMainDC();
	gMainDC(gPixmap *pixmap);
	virtual ~gMainDC();
public:
	virtual void setResolution(int xres, int yres, int bpp = 32) = 0;
	virtual bool suspendGraphics() { return false; }
	virtual bool resumeGraphics() { return false; }
	virtual bool isGraphicsSuspended() const { return false; }
	virtual void refresh() {}
	virtual std::string getGraphicsBackend() const { return "framebuffer"; }
	virtual std::string getGraphicsWindowProvider() const { return ""; }
	virtual std::string getGraphicsAccelerator() const { return ""; }
	virtual std::string getGraphicsBuffering() const { return ""; }
	virtual int getGraphicsBufferPages() const { return 0; }
	virtual int getGraphicsLogicalWidth() const;
	virtual int getGraphicsLogicalHeight() const;
	virtual int getGraphicsSurfaceWidth() const { return getGraphicsLogicalWidth(); }
	virtual int getGraphicsSurfaceHeight() const { return getGraphicsLogicalHeight(); }
	virtual int getGraphicsEGLMajor() const { return 0; }
	virtual int getGraphicsEGLMinor() const { return 0; }
	virtual int getGraphicsGLESVersion() const { return 0; }
	virtual bool getGraphicsPreservedSwap() const { return false; }
	virtual bool getGraphicsHardwareAccelerated() const { return isHardwareAccelerated(); }
	virtual bool getGraphicsAnimationsSupported() const { return supportsShowHideAnimations(); }
	virtual std::string getOSDAxis() const;
	virtual bool hasOSDPosition() const { return false; }
	virtual bool setOSDPosition(int left, int top, int width, int height) { return false; }
#ifndef SWIG
	static int getInstance(ePtr<gMainDC> &ptr) { if (!m_instance) return -1; ptr = m_instance; return 0; }
#endif
};

SWIG_TEMPLATE_TYPEDEF(ePtr<gMainDC>, gMainDC);
SWIG_EXTEND(ePtr<gMainDC>,
	static ePtr<gMainDC> getInstance()
	{
		extern ePtr<gMainDC> NewgMainDCPtr(void);
		return NewgMainDCPtr();
	}
	bool suspendGraphics()
	{
		return $self && *$self && (*$self)->suspendGraphics();
	}
	bool resumeGraphics()
	{
		return $self && *$self && (*$self)->resumeGraphics();
	}
	bool isGraphicsSuspended()
	{
		return $self && *$self && (*$self)->isGraphicsSuspended();
	}
	void refresh()
	{
		if ($self && *$self)
			(*$self)->refresh();
	}
);

#endif
