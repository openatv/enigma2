#include <lib/base/eerror.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/idemux.h>
#include <lib/gdi/gpixmap.h>

/*
 This is a very simple en300 706 telext decoder.
 
 It can only decode a single page at a time, thus it's only used
 for subtitles.
 
 */

DEFINE_REF(eDVBTeletextParser);

	/* we asumme error free transmission! */
static inline unsigned char decode_odd_parity(unsigned char *b)
{
	int i;
	unsigned char res = 0;
	for (i=0; i<7; ++i)
		if (*b & (0x80 >> i))
			res |= 1<<i;
	return res;
}

static inline unsigned char decode_hamming_84(unsigned char *b)
{
	unsigned char res = 0;
	res |= (*b << 3) & 8;
	res |= (*b     ) & 4;
	res |= (*b >> 3) & 2;
	res |= (*b >> 6) & 1;
	return res;
}

static inline unsigned long decode_hamming_2418(unsigned char *b)
{
	unsigned long h24 = b[0] | (b[1] << 8) | (b[2] << 16);
	
	return
		((h24 & 0x000004) >> 2) |
		((h24 & 0x000070) >> 3) |
		((h24 & 0x007f00) >> 4) |
		((h24 & 0x7f0000) >> 5);
}

eDVBTeletextParser::eDVBTeletextParser(iDVBDemux *demux)
{
	setStreamID(0xBD); /* as per en 300 472 */
	
	setPage(0x150);
	
	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("failed to create PES reader!");
	else
		m_pes_reader->connectRead(slot(*this, &eDVBTeletextParser::processData), m_read_connection);
}

eDVBTeletextParser::~eDVBTeletextParser()
{
}

void eDVBTeletextParser::processPESPacket(__u8 *pkt, int len)
{
	unsigned char *p = pkt;
	
	p += 4; len -= 4; /* start code, already be verified by pes parser */
	p += 2; len -= 2; /* length, better use the argument */	
	
	p += 3; len -= 3; /* pes header */
	
	p += 0x24; len -= 0x24; /* skip header */
	
//	eDebug("data identifier: %02x", *p);
	
	p++; len--;
	
	while (len > 2)
	{
		unsigned char data_unit_id = *p++;
		unsigned char data_unit_length = *p++;
		len -= 2;
		
		if (len < data_unit_length)
		{
			eDebug("data_unit_length > len");
			break;
		}
		
		if (data_unit_length != 44)
		{
			eDebug("illegal data unit length %d", data_unit_length);
			break;
		}
		
		unsigned char line_offset = *p++; len--;
		unsigned char framing_code = *p++; len--;

		int magazine_and_packet_address = decode_hamming_84(p++); len--;
		magazine_and_packet_address |= decode_hamming_84(p++)<<4; len--;
		
		unsigned char *data = p; p += 40; len -= 40;
		
		if (framing_code != 0xe4) /* no teletxt data */
			continue;
		
		m_M = magazine_and_packet_address & 7;
		m_Y = magazine_and_packet_address >> 3;
//		eDebug("line %d, framing code: %02x, M=%02x, Y=%02x", line_offset, framing_code, M, Y);
		
		if (m_Y == 0) /* page header */
		{
			m_C = 0;
			
			m_S1 = decode_hamming_84(data + 2); /* S1 */
			int S2C4 = decode_hamming_84(data + 3);
			
			m_S2 = S2C4 & 7;
			m_C |= (S2C4 & 8) ? (1<<4) : 0;
			
			m_S3 = decode_hamming_84(data + 4);
			
			int S4C5C6 = decode_hamming_84(data + 5);
			
			m_S4 = S4C5C6 & 3;
			m_C |= (S4C5C6 & 0xC) << 3;
			
			m_C |= decode_hamming_84(data + 6) << 7;
			m_C |= decode_hamming_84(data + 7) << 11;
			
				/* page on the same magazine? end current page. */
			if ((m_M == m_page_M) && (m_page_open))
			{
				handlePageEnd();
				m_page_open = 0;
			}
			
			m_X = decode_hamming_84(data+1) * 0x10 + decode_hamming_84(data);
			
				/* correct page on correct magazine? open page. */
			if ((m_M == m_page_M) && (m_X == m_page_X))
			{
				handlePageStart();
				m_page_open = 1;
				handleLine(data + 8, 32);
			}
		} else
		{
			/* data for the selected page? */
			if ((m_M == m_page_M) && m_page_open)
				handleLine(data, 40);
		}
	}
}

int eDVBTeletextParser::start(int pid)
{
	m_page_open = 0;

	if (m_pes_reader)
		return m_pes_reader->start(pid);
	else
		return -1;
}

void eDVBTeletextParser::handlePageStart()
{
	if (m_C & (1<<4)) /* erase flag set */
		m_subtitle_page.clear();
}

void eDVBTeletextParser::handleLine(unsigned char *data, int len)
{
	if (!m_Y) /* first line is page header, we don't need that. */
		return;

	int last_was_white = 1, color = -1;
	
	std::string text;
	
	for (int i=0; i<len; ++i)
	{
		unsigned char b = decode_odd_parity(data + i);
	
		if (b < 0x10) /* spacing attribute */
		{
			if (b < 8) /* colors */
			{
				if (b != color) /* new color is split into a new string */
				{
					if (color != -1)
						addSubtitleString(color, text);
					text = "";
					color = b;
				}
			}
				/* ignore other attributes */
		} else
		{
				/* no more than one whitespace, only printable chars */
			if (((!last_was_white) || (b != ' ')) && (b >= 0x20))
			{
				text += b;
				last_was_white = b == ' ';
			}
		}
	}
	addSubtitleString(color, text);
}

void eDVBTeletextParser::handlePageEnd()
{
	addSubtitleString(-1, ""); /* end last line */ 
	sendSubtitlePage();  /* send assembled subtitle page to display */
}

void eDVBTeletextParser::setPage(int page)
{
	m_page_M = (page >> 8) & 7; /* magazine to look for */
	m_page_X = page & 0xFF;     /* page number */
}

void eDVBTeletextParser::addSubtitleString(int color, const std::string &string)
{
	if ((color != m_subtitle_color) && !m_subtitle_text.empty())
	{
		m_subtitle_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(gRGB(0, 0xff, 0), m_subtitle_text));
		m_subtitle_text = "";
	} else if (!m_subtitle_text.empty() && m_subtitle_text[m_subtitle_text.size()-1] != ' ')
		m_subtitle_text += " ";
	
	m_subtitle_color = color;
	m_subtitle_text += string;
}

void eDVBTeletextParser::sendSubtitlePage()
{
	eDebug("subtitle page:");
	for (unsigned int i = 0; i < m_subtitle_page.m_elements.size(); ++i)
		eDebug("%s", m_subtitle_page.m_elements[i].m_text.c_str());
}
