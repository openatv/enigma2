#include <lib/gui/einputstring.h>
#include <algorithm>

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
	if (code >= 0x8020)
	{
		unsigned int character = code & ~0x8000;
		if (character > 0x10FFFF || (character >= 0xD800 && character <= 0xDFFF))
			return 0;
		std::string encoded;
		if (character < 0x80)
			encoded += char(character);
		else
		{
			int shift = character < 0x800 ? 6 : (character < 0x10000 ? 12 : 18);
			encoded += char((shift == 6 ? 0xC0 : (shift == 12 ? 0xE0 : 0xF0)) | (character >> shift));
			for (shift -= 6; shift >= 0; shift -= 6)
				encoded += char(0x80 | ((character >> shift) & 0x3F));
		}
		size_t offset = byteOffset(m_cursor);
		if (overwrite && m_cursor < m_len)
			m_string.replace(offset, byteOffset(m_cursor + 1) - offset, encoded);
		else
		{
			m_string.insert(offset, encoded);
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

	size_t offset = byteOffset(m_cursor - 1);
	m_string.erase(offset, byteOffset(m_cursor) - offset);

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
	m_len = std::count_if(str.begin(), str.end(), [](unsigned char ch) { return (ch & 0xC0) != 0x80; });
	if (m_cursor > m_len)
		m_cursor = m_len;

	if (m_input)
		m_input->invalidate();
}

std::string eInputContentString::getText()
{
	return m_string;
}

size_t eInputContentString::byteOffset(int position) const
{
	size_t offset = 0;
	while (position-- > 0 && offset < m_string.size())
	{
		++offset;
		while (offset < m_string.size() && (static_cast<unsigned char>(m_string[offset]) & 0xC0) == 0x80)
			++offset;
	}
	return offset;
}
