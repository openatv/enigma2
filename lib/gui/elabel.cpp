#include <lib/gui/elabel.h>
#include <lib/gdi/font.h>

eLabel::eLabel(eWidget *parent, int markedPos): eWidget(parent)
{
	m_pos = markedPos;
	ePtr<eWindowStyle> style;
	getStyle(style);

	style->getFont(eWindowStyle::fontStatic, m_font);

		/* default to topleft alignment */
	m_valign = alignTop;
	m_halign = alignBidi;

	m_have_foreground_color = 0;
	m_have_shadow_color = 0;

	m_nowrap = 0;
	m_border_size = 0;
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

		if (m_pos != -1)
		{
			style->setStyle(painter, eWindowStyle::styleLabel);
			ePtr<eTextPara> para = new eTextPara(eRect(0, 0, size().width(), size().height()));
			para->setFont(m_font);
			para->renderString(m_text.empty()?0:m_text.c_str(), 0);

			if (m_halign == alignLeft)
				para->realign(eTextPara::dirLeft);
			else if (m_halign == alignCenter)
				para->realign(m_nowrap ? eTextPara::dirCenterIfFits : eTextPara::dirCenter);
			else if (m_halign == alignRight)
				para->realign(eTextPara::dirRight);
			else if (m_halign == alignBlock)
				para->realign(eTextPara::dirBlock);
			else if (m_halign == alignBidi)
				para->realign(eTextPara::dirBidi);

			int glyphs = para->size();

			if (m_pos == -2) {  /* All glyphs inverted */
				eRect bbox;
				int left = 0, right = 0;
				for (int i=0; i<glyphs; i++)
					para->setGlyphFlag(i, GS_INVERT);
				if (glyphs > 0) {
					bbox = para->getGlyphBBox(0);
					left = bbox.left();
					bbox = para->getGlyphBBox(glyphs-1);
					right = bbox.left() + bbox.width();
				}
				bbox = eRect(left, 0, right-left, size().height());
				painter.fill(bbox);
			} else if ((m_pos < 0) || (m_pos >= glyphs))
				eWarning("glyph index %d in eLabel out of bounds!", m_pos);
			else
			{
				para->setGlyphFlag(m_pos, GS_INVERT);
				eRect bbox;
				bbox = para->getGlyphBBox(m_pos);
				bbox = eRect(bbox.left(), 0, bbox.width(), size().height());
				painter.fill(bbox);
			}

			painter.renderPara(para, ePoint(0, 0));
			return 0;
		} else
		{
			painter.setFont(m_font);
			style->setStyle(painter, eWindowStyle::styleLabel);

			if (m_have_shadow_color)
				painter.setForegroundColor(m_shadow_color);
			else if (m_have_foreground_color)
				painter.setForegroundColor(m_foreground_color);

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

			if (!m_nowrap)
				flags |= gPainter::RT_WRAP;

				/* if we don't have shadow, m_shadow_offset will be 0,0 */
			painter.renderText(eRect(-m_shadow_offset.x(), -m_shadow_offset.y(), size().width(), size().height()), m_text, flags, m_border_color, m_border_size);

			if (m_have_shadow_color)
			{
				if (!m_have_foreground_color)
					style->setStyle(painter, eWindowStyle::styleLabel);
				else
					painter.setForegroundColor(m_foreground_color);
				painter.setBackgroundColor(m_shadow_color);
				painter.renderText(eRect(0, 0, size().width(), size().height()), m_text, flags);
			}

			return 0;
		}
	}
	case evtChangedFont:
	case evtChangedText:
	case evtChangedAlignment:
	case evtChangedMarkedPos:
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

void eLabel::setMarkedPos(int markedPos)
{
	m_pos = markedPos;
	event(evtChangedMarkedPos);
}

void eLabel::setFont(gFont *font)
{
	m_font = font;
	event(evtChangedFont);
}

gFont* eLabel::getFont()
{
	return m_font;
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

void eLabel::setForegroundColor(const gRGB &col)
{
	if ((!m_have_foreground_color) || (m_foreground_color != col))
	{
		m_foreground_color = col;
		m_have_foreground_color = 1;
		invalidate();
	}
}

void eLabel::setShadowColor(const gRGB &col)
{
	if ((!m_have_shadow_color) || (m_shadow_color != col))
	{
		m_shadow_color = col;
		m_have_shadow_color = 1;
		invalidate();
	}
}

void eLabel::setShadowOffset(const ePoint &offset)
{
	m_shadow_offset = offset;
}

void eLabel::setBorderColor(const gRGB &col)
{
	if (m_border_color != col)
	{
		m_border_color = col;
		invalidate();
	}
}

void eLabel::setBorderWidth(int size)
{
	m_border_size = size;
}

void eLabel::setNoWrap(int nowrap)
{
	if (m_nowrap != nowrap)
	{
		m_nowrap = nowrap;
		invalidate();
	}
}

void eLabel::clearForegroundColor()
{
	if (m_have_foreground_color)
	{
		m_have_foreground_color = 0;
		invalidate();
	}
}

eSize eLabel::calculateSize()
{
	ePtr<eTextPara> p = new eTextPara(eRect(0, 0, size().width(), size().height()));

	p->setFont(m_font);
	p->renderString(m_text.empty()?0:m_text.c_str(), m_nowrap ? 0 : RS_WRAP);

	eRect bbox = p->getBoundBox();
	return bbox.size();
}
