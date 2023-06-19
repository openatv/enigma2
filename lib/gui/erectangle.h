#ifndef __lib_gui_erectangle_h
#define __lib_gui_erectangle_h

#include <lib/gui/ewidget.h>

class eRectangle : public eWidget
{
public:
	eRectangle(eWidget *parent);

	void setBorderWidth(int pixel);
	void setBorderColor(const gRGB &color);
	void setBackgroundGradient(const gRGB &startcolor, const gRGB &endcolor, int direction, int blend);

	enum
	{
		GRADIENT_VERTICAL = 0,
		GRADIENT_HORIZONTAL = 1
	};

protected:
	int event(int event, void *data = 0, void *data2 = 0);

private:
	bool m_have_border_color, m_gradient_set;
	int m_border_width, m_gradient_direction, m_gradient_blend;
	gRGB m_border_color, m_gradient_startcolor, m_gradient_endcolor;
};

#endif
