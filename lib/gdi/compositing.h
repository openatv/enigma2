#ifndef __lib_gdi_compositing_h
#define __lib_gdi_compositing_h

#include <lib/gdi/gpixmap.h>

#include <vector>

class gDC;

struct gContext
{
	ePtr<gDC> m_pixmap;
	int m_reg_int[256];
	float m_reg_float[256];
	~gContext();
};

struct gCompositingElement
{
	std::vector<unsigned int> m_code;
	gContext m_context;
};

class gCompositingData: public sigc::trackable
{
DECLARE_REF(gCompositingData);
public:
	int execute(void); /* returns ticks until next execution */
private:
	std::vector<gCompositingElement> m_elements;
	gContext m_globals;
};

#endif
