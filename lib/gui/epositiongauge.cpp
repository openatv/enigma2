#include <lib/gui/epositiongauge.h>
#include <lib/gui/epixmap.h>

ePositionGauge::ePositionGauge(eWidget *parent)
	: eWidget(parent)
{
	m_point_widget = new ePixmap(this);
	m_point_widget->setAlphatest(1);
	m_position = 0;
	m_length = 0;
}

ePositionGauge::~ePositionGauge()
{
	delete m_point_widget;
}

void ePositionGauge::setLength(const pts_t &len)
{
	eDebug("set len: %llx", len);
	if (m_length == len)
		return;
	m_length = len;
	updatePosition();
}

void ePositionGauge::setPosition(const pts_t &pos)
{
	eDebug("set position: %llx", pos);
	if (m_position == pos)
		return;
	m_position = pos;
	updatePosition();
}

void ePositionGauge::setInColor(const gRGB &color)
{
	invalidate();
}

void ePositionGauge::setPointer(gPixmap *pixmap, const ePoint &center)
{
	m_point_center = center;
	m_point_widget->setPixmap(pixmap);
	m_point_widget->resize(pixmap->size());
	updatePosition();
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
		style->paintBackground(painter, ePoint(0,0), s);
		style->setStyle(painter, eWindowStyle::styleLabel); // TODO - own style

		painter.fill(eRect(0, 10, s.width(), s.height()-20));
		
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
	if (!m_length)
		return;

	int width = size().width();
	int x = width * m_position / m_length;
	m_pos = x;
	int base = (size().height() - 10) / 2;

	m_point_widget->move(ePoint(m_pos - m_point_center.x(), base - m_point_center.y()));
}
