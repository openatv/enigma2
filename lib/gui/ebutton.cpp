#include <lib/gui/ebutton.h>

eButton::eButton(eWidget *parent): eLabel(parent)
{
}

void eButton::push()
{
	selected();
}

int eButton::event(int event, void *data, void *data2)
{
	switch (event)
	{
	default:
		break;
	}
	return eLabel::event(event, data, data2);
}
