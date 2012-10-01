#ifndef __lib_gui_egauge_h
#define __lib_gui_egauge_h

#include <lib/gui/ewidget.h>

class eGauge: public eWidget
{
public:
	eGauge(eWidget *parent);
	void setValue(int val);
	void setBorderColor(const gRGB &color);
protected:
	int event(int event, void *data=0, void *data2=0);
private:
	enum eGaugeEvent
	{
		evtChangedGauge = evtUserWidget
	};
	bool m_have_border_color;
	int m_value;
	int endx, endy, basex, basey;
	
	gRGB m_border_color;
};

#endif
