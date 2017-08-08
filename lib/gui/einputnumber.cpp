#include <lib/gui/einputnumber.h>
#include <linux/input.h>

DEFINE_REF(eInputContentNumber);

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

	int e = 1;
	for (int i = 1; i < m_len; ++i)
		e *= 10;

	int v = m_value;

	int i;
	for (i = 0; i < m_len; ++i)
	{
		int rem = v / e;
		r[i] = '0' + rem;
		v %= e;

		e /= 10;
	}

	r[i] = 0;

	res = r;
	cursor = m_cursor;
}

void eInputContentNumber::moveCursor(int dir)
{
	eDebug("[eInputContentNumber] move cursor..");
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

		/* we handle KEY_KPx, but not KEY_x. otherwise we would get stuff twice. */
#define ASCII(x) (x | 0x8000)
#define DIGIT(x) /* case KEY_##x: */ case KEY_KP##x: case ASCII(x|0x30): have_digit=x; break;
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
		else
			++m_len;

		m_cursor++;

		ASSERT(m_cursor <= m_len);

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
		eDebug("[eInputContentNumber] forward");
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

	insertDigit(m_cursor, -1);

	m_len--;
	m_cursor--;

	if (m_input)
		m_input->invalidate();
}

int eInputContentNumber::isValid()
{
	return m_value >= m_min && m_value <= m_max;
}

void eInputContentNumber::validate()
{
	recalcLen();
}

void eInputContentNumber::setValue(int val)
{
	m_value = val;
	recalcLen();
	if (m_cursor > m_len)
		m_cursor = m_len;
	if (m_input)
		m_input->invalidate();
}

int eInputContentNumber::getValue()
{
	return m_value;
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

