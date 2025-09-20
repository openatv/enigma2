#include <lib/gui/estack.h>

eStack::eStack(eWidget* parent, LayoutDirection dir) : eWidget(parent), m_direction(dir) {
	m_spacing = 0;
}

void eStack::setLayoutDirection(LayoutDirection dir) {
	m_direction = dir;
	recalcLayout();
}

void eStack::addChild(eWidget* child) {
	if (!child)
		return;

	child->setStack(this);
	m_stackchilds.push_back(child);
	recalcLayout();
}

void eStack::removeChild(eWidget* child) {
	if (!child)
		return;

	if (auto it = std::ranges::find(m_stackchilds, child); it != m_stackchilds.end()) {
		m_stackchilds.erase(it);
	}

	recalcLayout();
}

void eStack::invalidateChilds() {
	recalcLayout();
}


int eStack::event(int event, void* data, void* data2) {
	if (event == evtPaint)
		return 0;

	return eWidget::event(event, data, data2);
}

void eStack::recalcLayout() {
	int stack_w = size().width();
	int stack_h = size().height();

	if (stack_w < 0 || stack_h < 0)
		return;

	int x = 0, y = 0;
	int xr = stack_w;
	int yb = stack_h;
	int lcount = 0;
	int rcount = 0;
	int tcount = 0;
	int bcount = 0;

	for (auto child : m_stackchilds) {
		if (!child->isVisible())
			continue;

		eSize csize = child->size();
		int cx = 0, cy = 0;
		int cw = csize.width();
		int ch = csize.height();
		if (child->align() == 0)
			continue;

		if (m_direction == Horizontal) {
			if (child->align() & eStackAlignLeft) {
				cx = x;
				x += cw;
				if (lcount > 0) {
					x += m_spacing;
					cx += m_spacing;
				}
				lcount++;
			} else if (child->align() & eStackAlignRight) {
				cx = xr - cw;
				xr -= cx;
				if (lcount > 0) {
					cx -= m_spacing;
					xr -= m_spacing;
				}
				rcount++;
			} else if (child->align() & eStackAlignCenter)
				cx = (stack_w - cw) / 2;

			child->move(ePoint(cx + position().x(), child->position().y()));
		} else {
			if (child->align() & eStackAlignTop) {
				cy = y;
				y += cy;
				if (tcount > 0) {
					y += m_spacing;
					cy += m_spacing;
				}
				tcount++;
			} else if (child->align() & eStackAlignBottom) {
				cy = yb - ch;
				yb -= cy;
				if (bcount > 0) {
					cy -= m_spacing;
					yb -= m_spacing;
				}
				bcount++;
			} else if (child->align() & eStackAlignCenter)
				cy = (stack_h - ch) / 2;

			child->move(ePoint(child->position().x(), cy + position().y()));
		}
	}
}
