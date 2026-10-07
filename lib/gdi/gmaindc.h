#ifndef __lib_gdi_gmaindc_h
#define __lib_gdi_gmaindc_h

#include "grc.h"

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
);

#endif
