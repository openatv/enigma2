#ifndef __lib_gui_ebutton_h
#define __lib_gui_ebutton_h

#include <lib/gui/elabel.h>
#include <lib/python/connections.h>

class eButton: public eLabel
{
public:
	eButton(eWidget *parent);
	PSignal0<void> selected;

	void push();
protected:
	int event(int event, void *data=0, void *data2=0);
};

#endif
