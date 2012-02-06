#include <lib/gui/evideo.h>
#include <lib/gui/ewidgetdesktop.h>

ePtr<eTimer> eVideoWidget::fullsizeTimer;
int eVideoWidget::pendingFullsize = 0;

eVideoWidget::eVideoWidget(eWidget *parent)
	:eLabel(parent), m_fb_size(720, 576), m_state(0), m_decoder(1)
{
	if (!fullsizeTimer)
	{
		fullsizeTimer = eTimer::create(eApp);
		fullsizeTimer->timeout.connect(bind(slot(eVideoWidget::setFullsize), false));
	}
	parent->setPositionNotifyChild(1);
}

int eVideoWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtChangedPosition:
	case evtParentChangedPosition:
		m_state &= ~1;
		updatePosition(!isVisible());
		break;
	case evtChangedSize:
		m_state |= 2;
		updatePosition(!isVisible());
		break;
	case evtParentVisibilityChanged:
		updatePosition(!isVisible());
		break;
	}
	return eLabel::event(event, data, data2);
}

eVideoWidget::~eVideoWidget()
{
	updatePosition(1);
}

void eVideoWidget::setFBSize(eSize size)
{
	m_fb_size = size;
}

void eVideoWidget::writeProc(const std::string &filename, int value)
{
	FILE *f = fopen(filename.c_str(), "w");
	if (f)
	{
		fprintf(f, "%08x\n", value);
		fclose(f);
	}
}

void eVideoWidget::setPosition(int index, int left, int top, int width, int height)
{
	char filenamebase[128];
	snprintf(filenamebase, sizeof(filenamebase), "/proc/stb/vmpeg/%d/dst_", index);
	std::string filename = filenamebase;
	writeProc(filename + "left", left);
	writeProc(filename + "top", top);
	writeProc(filename + "width", width);
	writeProc(filename + "height", height);
	writeProc(filename + "apply", 1);
}

void eVideoWidget::setFullsize(bool force)
{
	for (int decoder=0; decoder < 2; ++decoder)
	{
		if (force || (pendingFullsize & (1 << decoder)))
		{
			eVideoWidget::setPosition(decoder, 0, 0, 0, 0);
			pendingFullsize &= ~(1 << decoder);
		}
	}
}

void eVideoWidget::updatePosition(int disable)
{
	if (!disable)
		m_state |= 4;

	if (disable && !(m_state & 4))
	{
		return;
	}

	if ((m_state & 2) != 2)
	{
		return;
	}

	eRect pos(0,0,0,0);
	if (!disable)
		pos = eRect(getAbsolutePosition(), size());
	else
		m_state &= ~4;

	if (!disable && m_state & 8 && pos == m_user_rect)
	{
		return;
	}

	if (!(m_state & 1))
	{
		m_user_rect = pos;
		m_state |= 1;
	}

	int left = pos.left() * 720 / m_fb_size.width();
	int top = pos.top() * 576 / m_fb_size.height();
	int width = pos.width() * 720 / m_fb_size.width();
	int height = pos.height() * 576 / m_fb_size.height();

	int tmp = left - (width * 4) / 100;
	left = tmp < 0 ? 0 : tmp;
	tmp = top - (height * 4) / 100;
	top = tmp < 0 ? 0 : tmp;
	tmp = (width * 108) / 100;
	width = left + tmp > 720 ? 720 - left : tmp;
	tmp = (height * 108) / 100;
	height = top + tmp > 576 ? 576 - top : tmp;

	if (!disable)
	{
		setPosition(m_decoder, left, top, width, height);
		pendingFullsize &= ~(1 << m_decoder);
		m_state |= 8;
	}
	else
	{
		m_state &= ~8;
		pendingFullsize |= (1 << m_decoder);
		fullsizeTimer->start(100, true);
	}
}

void eVideoWidget::setDecoder(int decoder)
{
	m_decoder = decoder;
}
