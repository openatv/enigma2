#include <lib/gui/elabel.h>

eLabel::eLabel(eWidget *parent): eWidget(parent)
{
	
}

int eLabel::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		gPainter &painter = *(gPainter*)data2;
		ePtr<gFont> fnt = new gFont("Arial", 70);
		painter.setFont(fnt);
		painter.setBackgroundColor(gColor(0x10));
		painter.setForegroundColor(gColor(0x1f));
		painter.clear();
		painter.setBackgroundColor(gColor(0x1f));
		painter.setForegroundColor(gColor(0x10));
		painter.renderText(eRect(0, 0, size().width(), size().height()), m_text);
		return 0;
	}
	case evtChangedText:
		invalidate();
		return 0;
	default:
		return eWidget::event(event, data, data2);
	}
}

void eLabel::setText(const std::string &string)
{
	if (m_text == string)
		return;
	m_text = string;
	event(evtChangedText);
}
