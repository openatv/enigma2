#include <lib/gui/evideo.h>

eVideoWidget::eVideoWidget(eWidget *parent): eWidget(parent)
{
	parent->setPositionNotifyChild(1);
}

int eVideoWidget::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtChangedPosition:
	case evtChangedSize:
	case evtParentChangedPosition:
		eDebug("position is now ...");
		updatePosition();
	}
	return eWidget::event(event, data, data2);
}


void eVideoWidget::updatePosition()
{
	ePoint abspos = getAbsolutePosition();
	eDebug("position is %d %d -> %d %d", abspos.x(), abspos.y(), size().width(), size().height());
	
	for (int i=0; i<4; ++i)
	{
		char *targets[]={"left", "top", "width", "height"};
		char filename[128];
		snprintf(filename, 128, "/proc/stb/vmpeg/%d/dst_%s", 1, targets[i]);
		FILE *f = fopen(filename, "w");
		if (!f)
		{
			eDebug("failed to open %s - %m", filename);
			break;
		}
		int val = 0;
		switch (i)
		{
		case 0: val = abspos.x(); break;
		case 1: val = abspos.y(); break;
		case 2: val = size().width(); break;
		case 3: val = size().height(); break;
		}
		fprintf(f, "%08x\n", val);
		fclose(f);
		eDebug("%s %08x", filename, val);
	}
}
