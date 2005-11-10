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
	void setOrientation(int orientation);
protected:
	int event(int event, void *data=0, void *data2=0);
private:
	enum eSliderEvent
	{
		evtChangedSlider = evtUserWidget
	};
	int m_min, m_max, m_value, m_start, m_orientation;
	
	gRegion m_currently_filled;
};

#endif
