#include <lib/gui/ebutton.h>

eButton::eButton(eWidget *parent): eLabel(parent)
{
		/* default to center alignment */
	m_valign = alignCenter;
	m_halign = alignCenter;
}

void eButton::push()
{
	selected();
}

int eButton::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		gPainter &painter = *(gPainter*)data2;
		ePtr<eWindowStyle> style;
		
		getStyle(style);
		
		eLabel::event(event, data, data2);
		style->drawFrame(painter, eRect(ePoint(0, 0), size()), eWindowStyle::frameButton);
		
		return 0;
	}
	default:
		break;
	}
	return eLabel::event(event, data, data2);
}
