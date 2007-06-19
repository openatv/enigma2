#ifndef __lib_gui_evideo_h
#define __lib_gui_evideo_h

#include <lib/gui/ewidget.h>

class eVideoWidget: public eWidget
{
public:
	eVideoWidget(eWidget *parent);
	~eVideoWidget();
	void setDecoder(int target);
protected:
	int event(int event, void *data=0, void *data2=0);
	void updatePosition(int disable = 0);

	int m_decoder;
};

#endif
