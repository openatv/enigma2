#include <lib/gui/elabel.h>

eLabel::eLabel(eWidget *parent): eWidget(parent)
{
	ePtr<eWindowStyle> style;
	getStyle(style);
	
	style->getFont(eWindowStyle::fontStatic, m_font);
	
		/* default to topleft alignment */
	m_valign = alignTop;
	m_halign = alignLeft;
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
		painter.setFont(m_font);
		style->setStyle(painter, eWindowStyle::styleLabel);
		
		int flags = 0;
		if (m_valign == alignTop)
			flags |= gPainter::RT_VALIGN_TOP;
		else if (m_valign == alignCenter)
			flags |= gPainter::RT_VALIGN_CENTER;
		else if (m_valign == alignBottom)
			flags |= gPainter::RT_VALIGN_BOTTOM;

		if (m_halign == alignLeft)
			flags |= gPainter::RT_HALIGN_LEFT;
		else if (m_halign == alignCenter)
			flags |= gPainter::RT_HALIGN_CENTER;
		else if (m_halign == alignRight)
			flags |= gPainter::RT_HALIGN_RIGHT;
		else if (m_halign == alignBlock)
			flags |= gPainter::RT_HALIGN_BLOCK;
		
		flags |= gPainter::RT_WRAP;
		painter.renderText(eRect(0, 0, size().width(), size().height()), m_text, flags);
		
		return 0;
	}
	case evtChangedFont:
	case evtChangedText:
	case evtChangedAlignment:
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

void eLabel::setFont(gFont *font)
{
	m_font = font;
	event(evtChangedFont);
}

void eLabel::setVAlign(int align)
{
	m_valign = align;
	event(evtChangedAlignment);
}

void eLabel::setHAlign(int align)
{
	m_halign = align;
	event(evtChangedAlignment);
}
