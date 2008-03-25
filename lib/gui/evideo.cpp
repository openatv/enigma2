#include <lib/gui/evideo.h>

eVideoWidget::eVideoWidget(eWidget *parent): eWidget(parent)
{
	m_decoder = 1;
	parent->setPositionNotifyChild(1);
}

int eVideoWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtChangedPosition:
	case evtChangedSize:
	case evtParentChangedPosition:
	case evtParentVisibilityChanged:
		updatePosition(!isVisible());
		break;
	}
	return eWidget::event(event, data, data2);
}

eVideoWidget::~eVideoWidget()
{
	updatePosition(1);
}

void eVideoWidget::updatePosition(int disable)
{
	eRect pos(0, 0, 0, 0);
	if (!disable)
		pos = eRect(getAbsolutePosition(), size());

	if (m_cur_pos == pos)
		return;

	m_cur_pos = pos;

	eDebug("position is %d %d -> %d %d", pos.left(), pos.top(), pos.width(), pos.height());

	for (int i=0; i<4; ++i)
	{
		const char *targets[]={"left", "top", "width", "height"};
		char filename[128];
		snprintf(filename, 128, "/proc/stb/vmpeg/%d/dst_%s", m_decoder, targets[i]);
		FILE *f = fopen(filename, "w");
		if (!f)
		{
			eDebug("failed to open %s - %m", filename);
			break;
		}
		int val = 0;
		switch (i)
		{
		case 0: val = pos.left(); break;
		case 1: val = pos.top(); break;
		case 2: val = pos.width(); break;
		case 3: val = pos.height(); break;
		}
		fprintf(f, "%08x\n", val);
		fclose(f);
		eDebug("%s %08x", filename, val);
	}
}

void eVideoWidget::setDecoder(int decoder)
{
	m_decoder = decoder;
}
