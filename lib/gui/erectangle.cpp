#include <lib/base/wrappers.h>
#include <lib/gui/erectangle.h>
#include <lib/gui/ewidgetdesktop.h>

eRectangle::eRectangle(eWidget *parent)
	: eWidget(parent), m_have_border_color(false), m_gradient_set(false), m_border_width(0), m_gradient_direction(0)
{
}

void eRectangle::setBorderWidth(int pixel)
{
	m_border_width = pixel;
	invalidate();
}

void eRectangle::setBorderColor(const gRGB &color)
{
	m_border_color = color;
	m_have_border_color = true;
	invalidate();
}

void eRectangle::setBackgroundGradient(const gRGB &startcolor, const gRGB &endcolor, int direction, int blend)
{
	m_gradient_startcolor = startcolor;
	m_gradient_endcolor = endcolor;
	m_gradient_direction = direction;
	m_gradient_blend = blend;
	m_gradient_set = true;
	invalidate();
}

int eRectangle::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		gPainter &painter = *(gPainter *)data2;

		eSize s(size());

		getStyle(style);

		eWidget::event(event, data, data2);

		if (m_have_border_color)
			painter.setForegroundColor(m_border_color);

		if (m_border_width)
		{
			painter.fill(eRect(0, 0, s.width(), m_border_width));
			painter.fill(eRect(0, m_border_width, m_border_width, s.height() - m_border_width));
			painter.fill(eRect(m_border_width, s.height() - m_border_width, s.width() - m_border_width, m_border_width));
			painter.fill(eRect(s.width() - m_border_width, m_border_width, m_border_width, s.height() - m_border_width));
		}

		if (m_gradient_set)
			painter.drawGradient(eRect(ePoint(0, 0), s), m_gradient_startcolor, m_gradient_endcolor, m_gradient_direction, m_gradient_blend);

		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}
