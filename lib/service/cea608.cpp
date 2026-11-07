#include <lib/service/cea608.h>

/* basic character set (0x20 - 0x7f) with the CEA-608 substitutions */
static const char *const basic_chars[0x60] = {
	" ", "!", "\"", "#", "$", "%", "&", "'", "(", ")", "\xc3\xa1", "+", ",", "-", ".", "/",
	"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":", ";", "<", "=", ">", "?",
	"@", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O",
	"P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "[", "\xc3\xa9", "]", "\xc3\xad", "\xc3\xb3",
	"\xc3\xba", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
	"p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "\xc3\xa7", "\xc3\xb7", "\xc3\x91", "\xc3\xb1", "\xe2\x96\xa0",
};

/* special characters, 0x11 0x30 - 0x11 0x3f */
static const char *const special_chars[16] = {
	"\xc2\xae", "\xc2\xb0", "\xc2\xbd", "\xc2\xbf", "\xe2\x84\xa2", "\xc2\xa2", "\xc2\xa3", "\xe2\x99\xaa",
	"\xc3\xa0", " ", "\xc3\xa8", "\xc3\xa2", "\xc3\xaa", "\xc3\xae", "\xc3\xb4", "\xc3\xbb",
};

/* extended characters, 0x12 0x20 - 0x12 0x3f (Spanish / misc) */
static const char *const extended_chars_12[32] = {
	"\xc3\x81", "\xc3\x89", "\xc3\x93", "\xc3\x9a", "\xc3\x9c", "\xc3\xbc", "\xe2\x80\x98", "\xc2\xa1",
	"*", "'", "\xe2\x80\x94", "\xc2\xa9", "\xe2\x84\xa0", "\xe2\x80\xa2", "\xe2\x80\x9c", "\xe2\x80\x9d",
	"\xc3\x80", "\xc3\x82", "\xc3\x87", "\xc3\x88", "\xc3\x8a", "\xc3\x8b", "\xc3\xab", "\xc3\x8e",
	"\xc3\x8f", "\xc3\xaf", "\xc3\x94", "\xc3\x99", "\xc3\xb9", "\xc3\x9b", "\xc2\xab", "\xc2\xbb",
};

/* extended characters, 0x13 0x20 - 0x13 0x3f (French / Portuguese / German) */
static const char *const extended_chars_13[32] = {
	"\xc3\x83", "\xc3\xa3", "\xc3\x8d", "\xc3\x8c", "\xc3\xac", "\xc3\x92", "\xc3\xb2", "\xc3\x95",
	"\xc3\xb5", "{", "}", "\\", "^", "_", "\xc2\xa6", "~",
	"\xc3\x84", "\xc3\xa4", "\xc3\x96", "\xc3\xb6", "\xc3\x9f", "\xc2\xa5", "\xc2\xa4", "|",
	"\xc3\x85", "\xc3\xa5", "\xc3\x98", "\xc3\xb8", "\xe2\x94\x8c", "\xe2\x94\x90", "\xe2\x94\x94", "\xe2\x94\x98",
};

/* preamble address code row table, index = ((b1 & 7) << 1) | ((b2 >> 5) & 1) */
static const int pac_rows[16] = { 10, 10, 0, 1, 2, 3, 11, 12, 13, 14, 4, 5, 6, 7, 8, 9 };

eCea608Decoder::eCea608Decoder()
{
	reset();
	m_last_emitted.clear();
	m_force_emit = false; /* no prior display exists at construction */
}

void eCea608Decoder::reset()
{
	clearBuf(m_disp);
	clearBuf(m_back);
	m_mode = MODE_POP_ON;
	m_rollup_rows = 2;
	m_row = ROWS - 1;
	m_col = 0;
	m_channel = 1;
	m_text_mode = false;
	m_last_control = 0;
	/* force an emit so a caption left on screen gets hidden after a flush */
	m_changed = true;
	m_force_emit = true;
}

void eCea608Decoder::clearBuf(std::string (*buf)[COLS])
{
	for (int r = 0; r < ROWS; r++)
		for (int c = 0; c < COLS; c++)
			buf[r][c].clear();
}

std::string (*eCea608Decoder::captionBuf())[COLS]
{
	return m_mode == MODE_POP_ON ? m_back : m_disp;
}

void eCea608Decoder::putChar(const char *utf8)
{
	if (m_col >= COLS)
		m_col = COLS - 1; /* overwrite the last cell instead of wrapping */
	captionBuf()[m_row][m_col] = utf8;
	m_col++;
	if (m_mode != MODE_POP_ON)
		m_changed = true;
}

void eCea608Decoder::backspace()
{
	if (m_col > 0)
		m_col--;
	captionBuf()[m_row][m_col].clear();
	if (m_mode != MODE_POP_ON)
		m_changed = true;
}

void eCea608Decoder::carriageReturn()
{
	if (m_mode != MODE_ROLL_UP)
		return;
	int top = m_row - (m_rollup_rows - 1);
	if (top < 0)
		top = 0;
	for (int r = top; r < m_row; r++)
		for (int c = 0; c < COLS; c++)
			m_disp[r][c] = m_disp[r + 1][c];
	for (int c = 0; c < COLS; c++)
		m_disp[m_row][c].clear();
	m_col = 0;
	m_changed = true;
}

void eCea608Decoder::pac(uint8_t b1, uint8_t b2)
{
	int row = pac_rows[((b1 & 0x07) << 1) | ((b2 >> 5) & 0x01)];
	if (m_mode == MODE_ROLL_UP && row != m_row)
	{
		/* the PAC moves the base row of the roll-up window with its content */
		int delta = row - m_row;
		std::string tmp[ROWS][COLS];
		for (int r = 0; r < ROWS; r++)
		{
			int nr = r + delta;
			if (nr < 0 || nr >= ROWS)
				continue;
			for (int c = 0; c < COLS; c++)
				tmp[nr][c].swap(m_disp[r][c]);
		}
		for (int r = 0; r < ROWS; r++)
			for (int c = 0; c < COLS; c++)
				m_disp[r][c].swap(tmp[r][c]);
		m_changed = true;
	}
	m_row = row;
	m_col = 0;
	if (b2 & 0x10)
		m_col = ((b2 >> 1) & 0x07) * 4; /* indent PAC */
}

void eCea608Decoder::control(uint8_t b2)
{
	switch (b2)
	{
	case 0x20: /* RCL - resume caption loading (pop-on) */
		m_mode = MODE_POP_ON;
		m_text_mode = false;
		break;
	case 0x21: /* BS */
		backspace();
		break;
	case 0x24: /* DER - delete to end of row */
		for (int c = m_col; c < COLS; c++)
			captionBuf()[m_row][c].clear();
		if (m_mode != MODE_POP_ON)
			m_changed = true;
		break;
	case 0x25: /* RU2 */
	case 0x26: /* RU3 */
	case 0x27: /* RU4 */
		if (m_mode != MODE_ROLL_UP)
		{
			clearBuf(m_disp);
			m_row = ROWS - 1;
			m_col = 0;
			m_changed = true;
		}
		m_mode = MODE_ROLL_UP;
		m_rollup_rows = b2 - 0x23;
		m_text_mode = false;
		break;
	case 0x29: /* RDC - resume direct captioning (paint-on) */
		m_mode = MODE_PAINT_ON;
		m_text_mode = false;
		break;
	case 0x2A: /* TR - text restart */
	case 0x2B: /* RTD - resume text display */
		m_text_mode = true; /* text service, not captions - ignore its data */
		break;
	case 0x2C: /* EDM - erase displayed memory */
		clearBuf(m_disp);
		m_changed = true;
		break;
	case 0x2D: /* CR */
		carriageReturn();
		break;
	case 0x2E: /* ENM - erase non-displayed memory */
		clearBuf(m_back);
		break;
	case 0x2F: /* EOC - end of caption: swap memories */
		for (int r = 0; r < ROWS; r++)
			for (int c = 0; c < COLS; c++)
				m_disp[r][c].swap(m_back[r][c]);
		m_mode = MODE_POP_ON;
		m_text_mode = false;
		m_changed = true;
		break;
	default: /* AOF/AON/FON - nothing to do */
		break;
	}
}

void eCea608Decoder::processPair(uint8_t b1, uint8_t b2)
{
	b1 &= 0x7F; /* strip odd parity */
	b2 &= 0x7F;

	if (b1 == 0 && b2 == 0)
		return; /* padding */

	if (b1 >= 0x20)
	{
		/* printable characters */
		m_last_control = 0;
		if (m_channel != 1 || m_text_mode)
			return;
		putChar(basic_chars[b1 - 0x20]);
		if (b2 >= 0x20)
			putChar(basic_chars[b2 - 0x20]);
		return;
	}

	if (b1 < 0x10)
		return; /* XDS - field 2 only, not ours */

	/* control codes are transmitted twice, execute once */
	uint16_t code = (uint16_t)((b1 << 8) | b2);
	if (code == m_last_control)
	{
		m_last_control = 0;
		return;
	}
	m_last_control = code;

	m_channel = (b1 & 0x08) ? 2 : 1;
	uint8_t b1nc = b1 & 0xF7; /* strip the channel bit */
	if (m_channel != 1)
		return;

	if (m_text_mode && !(b1nc == 0x14 && b2 >= 0x20 && b2 <= 0x2F))
		return; /* while in text mode only the misc control set matters to us */

	if (b2 >= 0x40)
	{
		pac(b1nc, b2);
		return;
	}

	switch (b1nc)
	{
	case 0x11:
		if (b2 >= 0x30)
			putChar(special_chars[b2 - 0x30]);
		else if (b2 >= 0x20)
			putChar(" "); /* mid-row style code occupies one cell */
		break;
	case 0x12:
		if (b2 >= 0x20)
		{
			backspace(); /* extended characters replace the preceding one */
			putChar(extended_chars_12[b2 - 0x20]);
		}
		break;
	case 0x13:
		if (b2 >= 0x20)
		{
			backspace();
			putChar(extended_chars_13[b2 - 0x20]);
		}
		break;
	case 0x14:
		if (b2 >= 0x20 && b2 <= 0x2F)
			control(b2);
		break;
	case 0x17:
		if (b2 >= 0x21 && b2 <= 0x23)
		{
			m_col += b2 - 0x20; /* tab offset */
			if (m_col >= COLS)
				m_col = COLS - 1;
		}
		break;
	default: /* 0x15/0x16 misc controls belong to field 2 - ignore */
		break;
	}
}

std::string eCea608Decoder::buildText() const
{
	std::string out;
	for (int r = 0; r < ROWS; r++)
	{
		std::string row;
		int pending_spaces = 0;
		for (int c = 0; c < COLS; c++)
		{
			const std::string &cell = m_disp[r][c];
			if (cell.empty() || cell == " ")
			{
				if (!row.empty())
					pending_spaces++;
				continue;
			}
			for (; pending_spaces > 0; pending_spaces--)
				row += ' ';
			row += cell;
		}
		if (!row.empty())
		{
			if (!out.empty())
				out += '\n';
			out += row;
		}
	}
	return out;
}

bool eCea608Decoder::takeDisplayIfChanged(std::string &text)
{
	if (!m_changed)
		return false;
	m_changed = false;
	text = buildText();
	if (!m_force_emit && text == m_last_emitted)
		return false;
	m_force_emit = false;
	m_last_emitted = text;
	return true;
}

void eCea608Decoder::extractField1Pairs(int payload_type, const uint8_t *data, size_t size, std::vector<uint16_t> &pairs)
{
	if (!data || !size)
		return;
	switch (payload_type)
	{
	case PAYLOAD_CEA608_RAW:
		for (size_t i = 0; i + 2 <= size; i += 2)
			pairs.push_back((uint16_t)((data[i] << 8) | data[i + 1]));
		break;
	case PAYLOAD_CEA608_S334_1A:
		for (size_t i = 0; i + 3 <= size; i += 3)
			if (data[i] & 0x80) /* field 1 */
				pairs.push_back((uint16_t)((data[i + 1] << 8) | data[i + 2]));
		break;
	case PAYLOAD_CEA708_RAW:
		for (size_t i = 0; i + 3 <= size; i += 3)
		{
			uint8_t hdr = data[i];
			if ((hdr & 0x04) && (hdr & 0x03) == 0) /* cc_valid && cc_type == 608 field 1 */
				pairs.push_back((uint16_t)((data[i + 1] << 8) | data[i + 2]));
		}
		break;
	case PAYLOAD_CEA708_CDP:
	{
		if (size < 8 || data[0] != 0x96 || data[1] != 0x69)
			return;
		size_t i = 7; /* cdp_identifier(2) length(1) frame_rate(1) flags(1) sequence(2) */
		while (i < size)
		{
			uint8_t section = data[i];
			if (section == 0x71) /* time code section */
				i += 5;
			else if (section == 0x72) /* cc data section */
			{
				if (i + 2 > size)
					return;
				size_t count = data[i + 1] & 0x1F;
				i += 2;
				for (size_t n = 0; n < count && i + 3 <= size; n++, i += 3)
				{
					uint8_t hdr = data[i];
					if ((hdr & 0x04) && (hdr & 0x03) == 0)
						pairs.push_back((uint16_t)((data[i + 1] << 8) | data[i + 2]));
				}
			}
			else if (section == 0x73) /* service info section */
			{
				if (i + 2 > size)
					return;
				i += 2 + (size_t)(data[i + 1] & 0x0F) * 7;
			}
			else /* footer (0x74) or unknown - stop */
				break;
		}
		break;
	}
	default:
		break;
	}
}
