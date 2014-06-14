#ifndef __lib_gui_ewidgetanimation_h
#define __lib_gui_ewidgetanimation_h

#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>

class eWidget;

class eWidgetAnimation
{
public:
	eWidgetAnimation(eWidget *widget);

	void tick(int inc);

	void startMoveAnimation(ePoint start, ePoint end, int length);

	int m_active;
private:
	int m_move_current_tick, m_move_length;
	ePoint m_move_start, m_move_end;
	eWidget *m_widget;
};

#endif
