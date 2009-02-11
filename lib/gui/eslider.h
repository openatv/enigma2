#ifndef __lib_gui_eslider_h
#define __lib_gui_eslider_h

#include <lib/gui/ewidget.h>

class eSlider: public eWidget
{
public:
	eSlider(eWidget *parent);
	void setValue(int val);
	void setStartEnd(int start, int end);
	void setRange(int min, int max);
	enum { orHorizontal, orVertical };
	void setOrientation(int orientation, int swapped = 0);
	void setBorderWidth(int pixel);
	void setBorderColor(const gRGB &color);
	void setPixmap(gPixmap *pixmap);
	void setPixmap(ePtr<gPixmap> &pixmap);
protected:
	int event(int event, void *data=0, void *data2=0);
private:
	enum eSliderEvent
	{
		evtChangedSlider = evtUserWidget
	};
	bool m_have_border_color;
	int m_min, m_max, m_value, m_start, m_orientation, m_orientation_swapped, m_border_width;
	ePtr<gPixmap> m_pixmap;
	
	gRegion m_currently_filled;
	gRGB m_border_color;
};

#endif
