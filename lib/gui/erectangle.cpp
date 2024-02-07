#include <lib/base/wrappers.h>
#include <lib/gui/erectangle.h>
#include <lib/gui/ewidgetdesktop.h>

eRectangle::eRectangle(eWidget *parent)
	: eWidget(parent)
{
}

int eRectangle::event(int event, void *data, void *data2)
{
	switch (event)
	{
		case evtPaint:
		{
			ePtr<eWindowStyle> style;
			// gPainter &painter = *(gPainter *)data2;
			getStyle(style);
			eWidget::event(event, data, data2);
			return 0;
		}
		default:
			return eWidget::event(event, data, data2);
	}
}
