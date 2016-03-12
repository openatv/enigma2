#include <lib/gui/eslider.h>

eSlider::eSlider(eWidget *parent)
	:eWidget(parent), m_have_border_color(false), m_have_foreground_color(false), m_start(0), m_orientation(orHorizontal), m_orientation_swapped(0), m_border_width(0)
{
}

void eSlider::setPixmap(ePtr<gPixmap> &pixmap)
{
	setPixmap(pixmap.operator->());
}

void eSlider::setPixmap(gPixmap *pixmap)
{
	m_pixmap = pixmap;
	event(evtChangedSlider);
}

void eSlider::setBackgroundPixmap(ePtr<gPixmap> &pixmap)
{
	setBackgroundPixmap(pixmap.operator->());
}

void eSlider::setBackgroundPixmap(gPixmap *pixmap)
{
	m_backgroundpixmap = pixmap;
	invalidate();
}

void eSlider::setBorderWidth(int pixel)
{
	m_border_width=pixel;
	invalidate();
}

void eSlider::setBorderColor(const gRGB &color)
{
	m_border_color=color;
	m_have_border_color=true;
	invalidate();
}

void eSlider::setForegroundColor(const gRGB &color)
{
	m_foreground_color = color;
	m_have_foreground_color = true;
	invalidate();
}

int eSlider::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;

		eSize s(size());
		getStyle(style);
			/* paint background */
		eWidget::event(evtPaint, data, data2);

		gPainter &painter = *(gPainter*)data2;

		style->setStyle(painter, eWindowStyle::styleLabel); // TODO - own style

		if (m_backgroundpixmap)
		{
			painter.blit(m_backgroundpixmap, ePoint(0, 0), eRect(), isTransparent() ? gPainter::BT_ALPHATEST : 0);
		}

		if (!m_pixmap)
		{
			if (m_have_foreground_color)
				painter.setForegroundColor(m_foreground_color);
			painter.fill(m_currently_filled);
		}
		else
			painter.blit(m_pixmap, ePoint(0, 0), m_currently_filled.extends, isTransparent() ? gPainter::BT_ALPHATEST : 0);

// border
		if (m_have_border_color)
			painter.setForegroundColor(m_border_color);
		painter.fill(eRect(0, 0, s.width(), m_border_width));
		painter.fill(eRect(0, m_border_width, m_border_width, s.height()-m_border_width));
		painter.fill(eRect(m_border_width, s.height()-m_border_width, s.width()-m_border_width, m_border_width));
		painter.fill(eRect(s.width()-m_border_width, m_border_width, m_border_width, s.height()-m_border_width));

		return 0;
	}
	case evtChangedSlider:
	{
		int num_pix = 0, start_pix = 0;
		gRegion old_currently_filled = m_currently_filled;

		int pixsize = (m_orientation == orHorizontal) ? size().width() : size().height();

		if (m_min < m_max)
		{
			int val_range = m_max - m_min;
			num_pix = (pixsize * (m_value - m_start) + val_range - 1) / val_range; /* properly round up */
			start_pix = (pixsize * m_start + val_range - 1) / val_range;

			if (m_orientation_swapped)
				start_pix = pixsize - num_pix - start_pix;
		}

		if  (start_pix < 0)
		{
			num_pix += start_pix;
			start_pix = 0;
		}

		if (num_pix < 0)
			num_pix = 0;

		if (m_orientation == orHorizontal)
			m_currently_filled = eRect(start_pix, 0, num_pix, pixsize);
		else
			m_currently_filled = eRect(0, start_pix, pixsize, num_pix);

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

void eSlider::setStartEnd(int start, int end)
{
	m_value = end;
	m_start = start;
	event(evtChangedSlider);
}

void eSlider::setOrientation(int orientation, int swapped)
{
	m_orientation = orientation;
	m_orientation_swapped = swapped;
	event(evtChangedSlider);
}

void eSlider::setRange(int min, int max)
{
	m_min = min;
	m_max = max;
	event(evtChangedSlider);
}
