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
	virtual void setResolution(int xres, int yres) = 0;
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
);

#endif
