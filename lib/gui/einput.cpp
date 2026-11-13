#include <lib/gui/einput.h>
#include <lib/gdi/font.h>
#include <lib/actions/action.h>

#include <lib/driver/rc.h>

eInput::eInput(eWidget *parent): eWidget(parent)
{
	m_mode = 1;
	m_have_focus = 0;
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

		eDebug("[eInput] cursor is %d", cursor);
		para->setFont(m_font);
		para->renderString(text.empty()?0:text.c_str(), 0);
		int glyphs = para->size();

		if (m_have_focus)
		{
			if (m_mode && cursor < glyphs)
			{
					/* in overwrite mode, when not at end of line, invert the current cursor position. */
				para->setGlyphFlag(cursor, GS_INVERT);
				eRect bbox = para->getGlyphBBox(cursor);
				bbox = eRect(bbox.left(), 0, bbox.width(), size().height());
				painter.fill(bbox);
			} else
			{
					/* otherwise, insert small cursor */
				eRect bbox;
				if (cursor < glyphs)
				{
					bbox = para->getGlyphBBox(cursor);
					bbox = eRect(bbox.left()-1, 0, 2, size().height());
				} else if (cursor)
				{
					bbox = para->getGlyphBBox(cursor - 1);
					bbox = eRect(bbox.right(), 0, 2, size().height());
				} else
				{
					bbox = eRect(0, 0, 2, size().height());
				}
				painter.fill(bbox);
			}
		}

		painter.renderPara(para, ePoint(0, 0));

		return 0;
	}
	case evtAction:
		if (isVisible())
		{
			if ((long)data == ASCII_ACTIONS)
			{
				if ((long)data2 == gotAsciiCode)
				{
					if (m_content)
					{
						extern int getPrevAsciiCode();  // defined in enigma.cpp
						return m_content->haveKey(getPrevAsciiCode(), m_mode);
					}
				}
			}
			else if ((long)data == INPUT_ACTIONS)
			{
				switch((long)data2)
				{
				case moveLeft:
					if (m_content)
						m_content->moveCursor(eInputContent::dirLeft);
					break;
				case moveRight:
					if (m_content)
						m_content->moveCursor(eInputContent::dirRight);
					break;
				case moveHome:
					if (m_content)
						m_content->moveCursor(eInputContent::dirHome);
					break;
				case moveEnd:
					if (m_content)
						m_content->moveCursor(eInputContent::dirEnd);
					break;
				case deleteForward:
					if (m_content)
						m_content->deleteChar(eInputContent::deleteForward);
					break;
				case deleteBackward:
					if (m_content)
						m_content->deleteChar(eInputContent::deleteBackward);
					break;
				case toggleOverwrite:
					setOverwriteMode(!m_mode);
					break;
				case accept:
					changed();
					mayKillFocus();
				}
				return 1;
			}
		}
		return 0;
	case evtKey:
	{
		long key = (long)data;
		long flags = (long)data2;
		if (m_content && !(flags & 1)) // only make/repeat, no break
			return m_content->haveKey(key, m_mode);
		break;
	}
	case evtFocusGot:
	{
		eDebug("[eInput] focus got in %p", this);
		ePtr<eActionMap> ptr;
		eActionMap::getInstance(ptr);
		ptr->bindAction("InputActions", (int64_t)0, INPUT_ACTIONS, this);
		ptr->bindAction("AsciiActions", (int64_t)0, ASCII_ACTIONS, this);
		m_have_focus = 1;
		eRCInput::getInstance()->setKeyboardMode(eRCInput::kmAscii);
			// fixme. we should use a style for this.
		setBackgroundColor(gRGB(64, 64, 128));
		invalidate();
		break;
	}
	case evtFocusLost:
	{
		eDebug("[eInput] focus lostin %p", this);
		ePtr<eActionMap> ptr;
		eActionMap::getInstance(ptr);
		ptr->unbindAction(this, INPUT_ACTIONS);
		ptr->unbindAction(this, ASCII_ACTIONS);
		m_have_focus = 0;
		if (m_content)
			m_content->validate();
		eRCInput::getInstance()->setKeyboardMode(eRCInput::kmNone);
		clearBackgroundColor();
		invalidate();
		break;
	}
	default:
		break;
	}
	return eWidget::event(event, data, data2);
}

void eInput::setFont(gFont *fnt)
{
	m_font = fnt;
	invalidate();
}

void eInputContent::setInput(eInput *widget)
{
	m_input = widget;
}

