#include <lib/gui/epositiongauge.h>
#include <lib/gui/epixmap.h>

ePositionGauge::ePositionGauge(eWidget *parent)
	: eWidget(parent)
{
	m_point_widget = new ePixmap(this);
	m_seek_point_widget = new ePixmap(this);
	m_seek_point_widget->hide();
	m_point_widget->setAlphatest(1);
	m_seek_point_widget->setAlphatest(1);
	m_position = 0;
	m_length = 0;
	m_have_foreground_color = 0;
	m_seek_position = 0;
}

ePositionGauge::~ePositionGauge()
{
	delete m_point_widget;
	delete m_seek_point_widget;
}

void ePositionGauge::setLength(const pts_t &len)
{
	if (m_length == len)
		return;
	m_length = len;
	updatePosition();
	invalidate();
}

void ePositionGauge::setPosition(const pts_t &pos)
{
	if (m_position == pos)
		return;
	m_position = pos;
	updatePosition();
}

void ePositionGauge::setInColor(const gRGB &color)
{
	invalidate();
}

void ePositionGauge::setPointer(int which, ePtr<gPixmap> &pixmap, const ePoint &center)
{
	setPointer(which, pixmap.operator->(), center);
}

void ePositionGauge::setPointer(int which, gPixmap *pixmap, const ePoint &center)
{
	if (which == 0)
	{
		m_point_center = center;
		m_point_widget->setPixmap(pixmap);
		m_point_widget->resize(pixmap->size());
	} else
	{
		m_seek_point_center = center;
		m_seek_point_widget->setPixmap(pixmap);
		m_seek_point_widget->resize(pixmap->size());
	}
	updatePosition();
}

void ePositionGauge::setInOutList(ePyObject list)
{
	if (!PyList_Check(list))
		return;
	int size = PyList_Size(list);
	int i;

	m_cue_entries.clear();

	for (i=0; i<size; ++i)
	{
		ePyObject tuple = PyList_GET_ITEM(list, i);
		if (!PyTuple_Check(tuple))
			continue;

		if (PyTuple_Size(tuple) != 2)
			continue;

		ePyObject ppts = PyTuple_GET_ITEM(tuple, 0), ptype = PyTuple_GET_ITEM(tuple, 1);
		if (!(PyLong_Check(ppts) && PyInt_Check(ptype)))
			continue;

		pts_t pts = PyLong_AsLongLong(ppts);
		int type = PyInt_AsLong(ptype);
		m_cue_entries.insert(cueEntry(pts, type));
	}
	invalidate();
}

int ePositionGauge::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		gPainter &painter = *(gPainter*)data2;

		eSize s(size());

		getStyle(style);

		eWidget::event(evtPaint, data, data2);

		style->setStyle(painter, eWindowStyle::styleLabel); // TODO - own style
//		painter.fill(eRect(0, 10, s.width(), s.height()-20));

		pts_t in = 0, out = 0;
		int xm, xm_last = -1;

		std::multiset<cueEntry>::iterator i(m_cue_entries.begin());

		while (1)
		{
			if (i == m_cue_entries.end())
				out = m_length;
			else {
				if (i->what == 0) /* in */
				{
					in = i++->where;
					continue;
				} else if (i->what == 1) /* out */
					out = i++->where;
				else /* mark or last */
				{
					xm = scale(i->where);
					if (i->what == 2) {
						painter.setForegroundColor(gRGB(0xFF8080));
						if (xm - 2 < xm_last) /* Make sure last is not overdrawn */
							painter.fill(eRect(xm_last, 0, 2 + xm - xm_last, s.height()));
						else
							painter.fill(eRect(xm - 2, 0, 4, s.height()));
					} else if (i->what == 3) {
						painter.setForegroundColor(gRGB(0x80FF80));
						painter.fill(eRect(xm - 1, 0, 3, s.height()));
						xm_last = xm + 2;
					}
					i++;
					continue;
				}
			}

			if (m_have_foreground_color)
			{
				painter.setForegroundColor(gRGB(m_foreground_color));
				int xi = scale(in), xo = scale(out);
				painter.fill(eRect(xi, (s.height()-4) / 2, xo-xi, 4));
			}

			in = m_length;

			if (i == m_cue_entries.end())
				break;
		}
//		painter.setForegroundColor(gRGB(0x00000000));

		if (m_have_foreground_color)
		{
			painter.setForegroundColor(gRGB(0x225b7395));
			painter.fill(eRect(s.width() - 2, 2, s.width() - 1, s.height() - 4));
			painter.fill(eRect(0, 2, 2, s.height() - 4));
		}

#if 0
// border
		if (m_have_border_color)
			painter.setForegroundColor(m_border_color);
		painter.fill(eRect(0, 0, s.width(), m_border_width));
		painter.fill(eRect(0, m_border_width, m_border_width, s.height()-m_border_width));
		painter.fill(eRect(m_border_width, s.height()-m_border_width, s.width()-m_border_width, m_border_width));
		painter.fill(eRect(s.width()-m_border_width, m_border_width, m_border_width, s.height()-m_border_width));
#endif

		return 0;
	}
	case evtChangedPosition:
		return 0;
	default:
		return eWidget::event(event, data, data2);
	}
}

void ePositionGauge::updatePosition()
{
	m_pos = scale(m_position);
	m_seek_pos = scale(m_seek_position);
	int base = (size().height() - 10) / 2;

	m_point_widget->move(ePoint(m_pos - m_point_center.x(), base - m_point_center.y()));
	m_seek_point_widget->move(ePoint(m_seek_pos - m_seek_point_center.x(), base - m_seek_point_center.y()));
}

int ePositionGauge::scale(const pts_t &val)
{
	if (!m_length)
		return 0;

	int width = size().width();

	return (int)(width * val / m_length);
}

void ePositionGauge::setForegroundColor(const gRGB &col)
{
	if ((!m_have_foreground_color) || !(m_foreground_color == col))
	{
		m_foreground_color = col;
		m_have_foreground_color = 1;
		invalidate();
	}
}

void ePositionGauge::enableSeekPointer(int enable)
{
	if (enable)
		m_seek_point_widget->show();
	else
		m_seek_point_widget->hide();
}

void ePositionGauge::setSeekPosition(const pts_t &pos)
{
	if (m_seek_position == pos)
		return;
	m_seek_position = pos;
	updatePosition();
}
