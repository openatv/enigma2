#ifndef __lib_gui_erectangle_h
#define __lib_gui_erectangle_h

#include <lib/gui/ewidget.h>

class eRectangle : public eWidget
{
public:
	eRectangle(eWidget *parent);

	void setBorderWidth(int pixel);
	void setBorderColor(const gRGB &color);

protected:
	int event(int event, void *data = 0, void *data2 = 0);

private:
	bool m_have_border_color;
	int m_border_width;
	gRGB m_border_color;
};

#endif
