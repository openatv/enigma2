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
		ePtr<eWindowStyle> style;
		
		getStyle(style);
		
		eWidget::event(event, data, data2);

		gPainter &painter = *(gPainter*)data2;
		ePtr<gFont> fnt = new gFont("Arial", 14);
		painter.setFont(fnt);
		style->setStyle(painter, eWindowStyle::styleLabel);
		painter.renderText(eRect(0, 0, size().width(), size().height()), m_text, gPainter::RT_HALIGN_CENTER|gPainter::RT_VALIGN_CENTER);
		
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
