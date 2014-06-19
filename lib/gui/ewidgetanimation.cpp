#include <lib/gui/ewidgetanimation.h>
#include <lib/gui/ewidget.h>

eWidgetAnimation::eWidgetAnimation(eWidget *widget): m_widget(widget)
{
	m_active = 0;
}

void eWidgetAnimation::tick(int inc)
{
	if (!m_active)
		return;

		// move animation
	if (m_move_length)
	{
		if (m_move_current_tick >= m_move_length)
		{
			m_active = 0;
			m_move_current_tick = m_move_length;
		}

		m_move_start = m_widget->position();

		int xdiff = m_move_start.x() - m_move_end.x();
		int ydiff = m_move_start.y() - m_move_end.y();

		xdiff *= 31; xdiff /= 32;
		ydiff *= 31; ydiff /= 32;

		#if 0
		xdiff *= m_move_current_tick;
		xdiff /= m_move_length;

		ydiff *= m_move_current_tick;
		ydiff /= m_move_length;
		#endif

		ePoint res(m_move_end.x() + xdiff, m_move_end.y() + ydiff);

		m_move_current_tick += inc;

		m_widget->move(res);
	}
}

void eWidgetAnimation::startMoveAnimation(ePoint start, ePoint end, int length)
{
	m_move_current_tick = 0;
	m_move_length = length;
	m_move_start = start;
	m_move_end = end;
	m_active = 1;
	m_widget->move(m_move_start);
}
