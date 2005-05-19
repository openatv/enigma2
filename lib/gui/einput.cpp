#include <lib/gui/einput.h>
#include <lib/gdi/font.h>
#include <lib/actions/action.h>
#include <linux/input.h>

eInput::eInput(eWidget *parent): eLabel(parent)
{
		/* default to center alignment */
	m_valign = alignCenter;
	m_halign = alignCenter;

	m_mode = 0;
}

eInput::~eInput()
{
	mayKillFocus();
}

void eInput::setOverwriteMode(int m)
{
	int om = m_mode;
	m_mode = m;
	if (om != m_mode)
		invalidate();
}

void eInput::setContent(eInputContent *content)
{
	if (m_content)
		m_content->setInput(0);
	m_content = content;
	if (m_content)
		m_content->setInput(this);
}

int eInput::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		gPainter &painter = *(gPainter*)data2;
		ePtr<eWindowStyle> style;
		
		getStyle(style);
		
		eWidget::event(event, data, data2);
		
		ePtr<eTextPara> para = new eTextPara(eRect(0, 0, size().width(), size().height()));
		
		std::string text;
		int cursor = -1;
		
		if (m_content)
			m_content->getDisplay(text, cursor);
		
		eDebug("cursor is %d", cursor);
		para->setFont(m_font);
		para->renderString(text, 0);
		int glyphs = para->size();
		
		if (m_mode && cursor < glyphs)
		{
				/* in overwrite mode, when not at end of line, invert the current cursor position. */
			para->setGlyphFlag(cursor, GS_INVERT);
			eRect bbox = para->getGlyphBBox(cursor);
			bbox = eRect(bbox.left(), 0, bbox.width() + 2, size().height());
			painter.fill(bbox);
		} else
		{
				/* otherwise, insert small cursor */
			eRect bbox;
			if (cursor < glyphs)
			{
				bbox = para->getGlyphBBox(cursor);
				bbox = eRect(bbox.left()-1, 0, 2, size().height());
			} else
			{
				bbox = para->getGlyphBBox(cursor - 1);
				bbox = eRect(bbox.right(), 0, 2, size().height());
			}
			painter.fill(bbox);
		}
		
		painter.renderPara(para, ePoint(0, 0));
		
		return 0;
	}
	case evtAction:
		if (isVisible())
		{
			switch((int)data2)
			{
			case moveLeft:
				m_content->moveCursor(eInputContent::dirLeft);
				break;
			case moveRight:
				m_content->moveCursor(eInputContent::dirRight);
				break;
			case moveHome:
				m_content->moveCursor(eInputContent::dirHome);
				break;
			case moveEnd:
				m_content->moveCursor(eInputContent::dirEnd);
				break;
			case deleteForward:
				m_content->deleteChar(eInputContent::deleteForward);
				break;
			case deleteBackward:
				m_content->deleteChar(eInputContent::deleteBackward);
				break;
			case toggleOverwrite:
				setOverwriteMode(!m_mode);
				break;
			}
			return 1;
		}
		return 0;
	case evtKey:
	{
		int key = (int)data;
		int flags = (int)data2;
		if (m_content && !(flags & 1)) // only make/repeat, no break
			return m_content->haveKey(key, m_mode);
		break;
	}
	case evtFocusGot:
	{
		eDebug("focus got in %p", this);
		ePtr<eActionMap> ptr;
		eActionMap::getInstance(ptr);
		ptr->bindAction("InputActions", 0, 0, this);
			// bind all keys
		ptr->bindAction("", 0, 1, this);
		break;
	}
	case evtFocusLost:
	{
		eDebug("focus lostin %p", this);
		ePtr<eActionMap> ptr;
		eActionMap::getInstance(ptr);
		ptr->unbindAction(this, 0);
		ptr->unbindAction(this, 1);
		break;
	}
	default:
		break;
	}
	return eLabel::event(event, data, data2);
}

int eInput::getNumber()
{
	return atoi(m_text.c_str());
}

DEFINE_REF(eInputContentNumber);

void eInputContent::setInput(eInput *widget)
{
	m_input = widget;
}

eInputContentNumber::eInputContentNumber(int cur, int min, int max)
{
	m_min = min;
	m_max = max;
	m_value = cur;
	m_cursor = 0;
	m_input = 0;
	recalcLen();
}

void eInputContentNumber::getDisplay(std::string &res, int &cursor)
{
	// TODO
	char r[128];
	sprintf(r, "%d", m_value);
	res = r;
	cursor = m_cursor;
}

void eInputContentNumber::moveCursor(int dir)
{
	eDebug("move cursor..");
	int old_cursor = m_cursor;
	
	switch (dir)
	{
	case dirLeft:
		--m_cursor;
		break;
	case dirRight:
		++m_cursor;
		break;
	case dirHome:
		m_cursor = 0;
		break;
	case dirEnd:
		m_cursor = m_len;
		break;
	}
	
	if (m_cursor < 0)
		m_cursor = 0;
	if (m_cursor > m_len)
		m_cursor = m_len;
	
	if (m_cursor != old_cursor)
		if (m_input)
			m_input->invalidate();
}

int eInputContentNumber::haveKey(int code, int overwrite)
{
	int have_digit = -1;

#define ASCII(x) (x | 0x8000)
#define DIGIT(x) case KEY_##x: case KEY_KP##x: case ASCII(x|0x30): have_digit=x; break;
	switch (code)
	{
	DIGIT(0);
	DIGIT(1);
	DIGIT(2);
	DIGIT(3);
	DIGIT(4);
	DIGIT(5);
	DIGIT(6);
	DIGIT(7);
	DIGIT(8);
	DIGIT(9);
	default:
		return 0;
	}
	
	if (have_digit != -1)
	{
		insertDigit(m_cursor, have_digit);
			/* if overwrite and not end of line, erase char first. */
		if (overwrite && m_cursor < m_len)
			insertDigit(m_cursor + 1, -1);
		m_cursor++;
		
		recalcLen();
		
				// can happen when 0 -> x
		if (m_cursor > m_len)
			m_cursor = m_len;
 
		if (m_input)
			m_input->invalidate();
		return 1;
	}
	return 0;
}

void eInputContentNumber::deleteChar(int dir)
{
	if (dir == deleteForward)
	{
		eDebug("forward");
		if (m_cursor != m_len)
			++m_cursor;
		else
			return;
	}
		/* backward delete at begin */
	if (!m_cursor)
		return;
	insertDigit(m_cursor, -1);
	
	if (m_len > 1)
		m_cursor--;
	recalcLen();
	if (m_input)
		m_input->invalidate();
}

int eInputContentNumber::isValid()
{
	return m_value >= m_min && m_value <= m_max;
}

void eInputContentNumber::recalcLen()
{
	int v = m_value;
	m_len = 0;
	while (v)
	{
		++m_len;
		v /= 10;
	}
	
	if (!m_len) /* zero */
		m_len = 1;
}

void eInputContentNumber::insertDigit(int pos, int dig)
{
		/* get stuff left from cursor */
	int exp = 1;
	int i;
	for (i = 0; i < (m_len - pos); ++i)
		exp *= 10;
	
		/* now it's 1...max */
	int left = m_value / exp;
	int right = m_value % exp;
	
	if (dig >= 0)
	{
		left *= 10;
		left += dig;
	} else if (dig == -1) /* delete */
	{
		left /= 10;
	}
	
	left *= exp;
	left += right;
	m_value = left;
}
