#include <lib/gui/eslider.h>

eSlider::eSlider(eWidget *parent): eWidget(parent)
{
}

int eSlider::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		gPainter &painter = *(gPainter*)data2;
		
		
		getStyle(style);
		style->paintBackground(painter, ePoint(0, 0), size());
		style->setStyle(painter, eWindowStyle::styleLabel); // TODO - own style
		painter.fill(m_currently_filled);
		
		return 0;
	}
	case evtChangedSlider:
	{

		int num_pix = 0;
		if (m_min < m_max)
			num_pix = size().width() * m_value / (m_max - m_min);
		gRegion old_currently_filled = m_currently_filled;
		m_currently_filled = eRect(0, 0, num_pix, size().height());
		
			// redraw what *was* filled before and now isn't.
		invalidate(m_currently_filled - old_currently_filled);
			// redraw what wasn't filled before and is now.
		invalidate(old_currently_filled - m_currently_filled);
		
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}

void eSlider::setValue(int value)
{
	m_value = value;
	event(evtChangedSlider);
}

void eSlider::setRange(int min, int max)
{
	m_min = min;
	m_max = max;
	event(evtChangedSlider);
}
