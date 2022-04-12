#include <lib/gui/einputstring.h>

DEFINE_REF(eInputContentString);

eInputContentString::eInputContentString()
{
	m_string = "bla";
	m_cursor = 0;
	m_input = 0;
	m_len = m_string.size();
}

void eInputContentString::getDisplay(std::string &res, int &cursor)
{
	res = m_string;
	cursor = m_cursor;
}

void eInputContentString::moveCursor(int dir)
{
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

int eInputContentString::haveKey(int code, int overwrite)
{
	int have_char = -1;

	if (code >= 0x8020)
		have_char = code &~ 0x8000;

	if (have_char != -1)
	{
		if (overwrite && m_cursor < m_len)
			m_string[m_cursor] = have_char;
		else
		{
			m_string.insert(m_cursor, 1, have_char);
			++m_len;
		}

		m_cursor++;

		ASSERT(m_cursor <= m_len);

		if (m_input)
			m_input->invalidate();
		return 1;
	}
	return 0;
}

void eInputContentString::deleteChar(int dir)
{
	if (dir == deleteForward)
	{
		eDebug("[eInputString] forward");
		if (m_cursor != m_len)
			++m_cursor;
		else
			return;
	}
		/* backward delete at begin */
	if (!m_cursor)
		return;

	if (!m_len)
		return;

	m_string.erase(m_cursor - 1, m_cursor);

	m_len--;
	m_cursor--;

	if (m_input)
		m_input->invalidate();
}

int eInputContentString::isValid()
{
	return 1;
}

void eInputContentString::validate()
{
}

void eInputContentString::setText(const std::string &str)
{
	m_string = str;
	m_len = m_string.size();
	if (m_cursor > m_len)
		m_cursor = m_len;

	if (m_input)
		m_input->invalidate();
}

std::string eInputContentString::getText()
{
	return m_string;
}
