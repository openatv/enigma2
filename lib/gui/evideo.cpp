#include <lib/gui/evideo.h>
#include <lib/gui/ewidgetdesktop.h>

static ePtr<eTimer> fullsizeTimer;
static int pendingFullsize;

void setFullsize()
{
	for (int decoder=0; decoder < 1; ++decoder)
	{
		if (pendingFullsize & (1 << decoder))
		{
			for (int i=0; i<4; ++i)
			{
				const char *targets[]={"left", "top", "width", "height"};
				char filename[128];
				snprintf(filename, 128, "/proc/stb/vmpeg/%d/dst_%s", decoder, targets[i]);
				FILE *f = fopen(filename, "w");
				if (!f)
				{
					eDebug("failed to open %s - %m", filename);
					break;
				}
				fprintf(f, "%08x\n", 0);
				fclose(f);
			}
			pendingFullsize &= ~(1 << decoder);
		}
	}
}

eVideoWidget::eVideoWidget(eWidget *parent)
	:eLabel(parent), m_fb_size(720, 576), m_state(0), m_decoder(1)
{
	if (!fullsizeTimer)
	{
		fullsizeTimer = eTimer::create(eApp);
		fullsizeTimer->timeout.connect(slot(setFullsize));
	}
	parent->setPositionNotifyChild(1);
//	setBackgroundColor(gRGB(0xFF000000));
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

void eVideoWidget::updatePosition(int disable)
{
	if (!disable)
		m_state |= 4;

	if (disable && !(m_state & 4))
	{
//		eDebug("was not visible!");
		return;
	}

	if ((m_state & 2) != 2)
	{
//		eDebug("no size!");
		return;
	}

//	eDebug("position %d %d -> %d %d", position().x(), position().y(), size().width(), size().height());

	eRect pos(0,0,0,0);
	if (!disable)
		pos = eRect(getAbsolutePosition(), size());
	else
		m_state &= ~4;

//	eDebug("abs position %d %d -> %d %d", pos.left(), pos.top(), pos.width(), pos.height());

	if (!disable && m_state & 8 && pos == m_user_rect)
	{
//		eDebug("matched");
		return;
	}

	if (!(m_state & 1))
	{
		m_user_rect = pos;
		m_state |= 1;
//		eDebug("set user rect pos!");
	}

//	eDebug("m_user_rect %d %d -> %d %d", m_user_rect.left(), m_user_rect.top(), m_user_rect.width(), m_user_rect.height());

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

//	eDebug("picture recalced %d %d -> %d %d", left, top, width, height);

	if (!disable)
	{
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
			{
				switch (i)
				{
				case 0: val = left; break;
				case 1: val = top; break;
				case 2: val = width; break;
				case 3: val = height; break;
				}
				fprintf(f, "%08x\n", val);
				fclose(f);
//				eDebug("%s %08x", filename, val);
			}
		}
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
