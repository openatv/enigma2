#include <lib/base/eerror.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/idemux.h>
#include <lib/gdi/gpixmap.h>

// Try to map teletext characters into ISO-8859-1 charset
// Use similar looking or similar meaning characters when possible.

// G0 and G2 national option table
// see table 33 in ETSI EN 300 706
// use it with (triplet 1 bits 14-11)*(ctrl bits C12-14)

unsigned char LatinNationalOptionSubsetsLookup[16*8] =
{
	1, 4, 11, 5, 3, 8, 0, 1,
	7, 4, 11, 5, 3, 1, 0, 1,
	1, 4, 11, 5, 3, 8, 12, 1,
	1, 1, 1, 1, 1, 10, 1, 9,
	1, 4, 2, 6, 1, 1, 0, 1,
	1, 1, 1, 1, 1, 1, 1, 1, // reserved
	1, 1, 1, 1, 1, 1, 12, 1,
	1, 1, 1, 1, 1, 1, 1, 1, // reserved
	1, 1, 1, 1, 3, 1, 1, 1,
	1, 1, 1, 1, 1, 1, 1, 1, // reserved
	1, 1, 1, 1, 1, 1, 1, 1,
	1, 1, 1, 1, 1, 1, 1, 1, // reserved
	1, 1, 1, 1, 1, 1, 1, 1, // reserved
	1, 1, 1, 1, 1, 1, 1, 1, // reserved
	1, 1, 1, 1, 1, 1, 1, 1, // reserved
	1, 1, 1, 1, 1, 1, 1, 1  // reserved
};

unsigned char LatinNationalReplaceMap[128] =
{
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 5, 6, 7, 8,
	9, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
	0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 11, 12, 13, 0
};

// latin national option subsets
// see table 36 in ETSI EN 300 706

unsigned char LatinNationalOptionSubsets[13*14] = {
	0, '#', 'u', 'c', 't', 'z', 'ý', 'í', 'r', 'é', 'á', 'e', 'ú', 's', // Slovak/Czech
	0, '£', '$', '@', '-', '½', '-', '|', '#', '-', '¼', '#', '¾', '÷', // English
	0, '#', 'õ', 'S', 'Ä', 'Ö', 'Z', 'Ü', 'Õ', 's', 'ä', 'ö', 'z', 'ü', // Estonian
	0, 'é', 'ï', 'à', 'ë', 'ê', 'ù', 'î', '#', 'è', 'â', 'ô', 'û', 'ç', // French
	0, '#', '$', '§', 'Ä', 'Ö', 'Ü', '^', '_', 'º', 'ä', 'ö', 'ü', 'ß', // German
	0, '£', '$', 'é', 'º', 'ç', '-', '|', '#', 'ù', 'à', 'ò', 'è', 'ì', // Italian
	0, '#', '$', 'S', 'e', 'e', 'Z', 'c', 'u', 's', 'a', 'u', 'z', 'i', // Lithuanian/Lettish
	0, '#', 'n', 'a', 'Z', 'S', 'L', 'c', 'ó', 'e', 'z', 's', 'l', 'z', // Polish
	0, 'ç', '$', 'i', 'á', 'é', 'í', 'ó', 'ú', '¿', 'ü', 'ñ', 'è', 'à', // Spanish/Portuguese
	0, '#', '¤', 'T', 'Â', 'S', 'A', 'Î', 'i', 't', 'â', 's', 'a', 'î', // Rumanian
	0, '#', 'Ë', 'C', 'C', 'Z', 'D', 'S', 'ë', 'c', 'c', 'z', 'd', 's', // Slovenian/Serbian/Croation
	0, '#', '¤', 'É', 'Ä', 'Ö', 'Å', 'Ü', '_', 'é', 'ä', 'ö', 'å', 'ü', // Finnish/Hungarian/Swedish
	0, 'T', 'g', 'I', 'S', 'Ö', 'Ç', 'Ü', 'G', 'i', 's', 'ö', 'ç', 'ü'  // Turkish
};

unsigned char MapTeletextG0Latin1Char(int Gtriplet, int NatOpts, unsigned char inchar)
{
	int num = LatinNationalOptionSubsetsLookup[(Gtriplet&0xf)*(NatOpts&0x7)];
	unsigned char c = inchar&0x7f;
	unsigned char cc = LatinNationalReplaceMap[c];
	if(cc)
		return LatinNationalOptionSubsets[num*cc];
	else
		return c;
}

// This is a very simple en300 706 telext decoder.
// It can only decode a single page at a time, thus it's only used
// for subtitles.
 
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

static int extractPTS(pts_t &pts, unsigned char *pkt)
{
	pkt += 7;
	int flags = *pkt++;
	
	pkt++; // header length
	
	if (flags & 0x80) /* PTS present? */
	{
			/* damn gcc bug */
		pts  = ((unsigned long long)(((pkt[0] >> 1) & 7))) << 30;
		pts |=   pkt[1] << 22;
		pts |=  (pkt[2]>>1) << 15;
		pts |=   pkt[3] << 7;
		pts |=  (pkt[5]>>1);
		
		return 0;
	} else
		return -1;
}

eDVBTeletextParser::eDVBTeletextParser(iDVBDemux *demux)
{
	setStreamID(0xBD); /* as per en 300 472 */
	
	setPage(-1);
	
	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("failed to create teletext subtitle PES reader!");
	else
		m_pes_reader->connectRead(slot(*this, &eDVBTeletextParser::processData), m_read_connection);
}

eDVBTeletextParser::~eDVBTeletextParser()
{
}

void eDVBTeletextParser::processPESPacket(__u8 *pkt, int len)
{
	unsigned char *p = pkt;
	
	pts_t pts;
	int have_pts = extractPTS(pts, pkt);
	
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
			/* eDebug("illegal data unit length %d", data_unit_length); */
			break;
		}
		
		if (data_unit_id != 0x03)
		{
			/* eDebug("non subtitle data unit id %d", data_unit_id); */
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

//			eDebug("line %d, framing code: %02x, M=%02x, Y=%02x", line_offset, framing_code, m_M, m_Y);
		
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
			
			int serial_mode = m_C & (1<<11);
			
				/* page on the same magazine? end current page. */
			if ((serial_mode || (m_M == m_page_M)) && (m_page_open))
			{
				handlePageEnd(have_pts, pts);
				m_page_open = 0;
			}
			
			m_X = decode_hamming_84(data+1) * 0x10 + decode_hamming_84(data);
			
			if ((m_C & (1<<6)) && (m_X != 0xFF)) /* scan for pages with subtitle bit set */
				m_found_subtitle_pages.insert((m_M << 8) | m_X);
			
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
//	if (m_C & (1<<4)) /* erase flag set */

		/* we are always erasing the page, 
		   even when the erase flag is not set. */
	m_subtitle_page.clear();
}

void eDVBTeletextParser::handleLine(unsigned char *data, int len)
{
/* // hexdump
	for (int i=0; i<len; ++i)
		eDebugNoNewLine("%02x ", decode_odd_parity(data + i));
	eDebug(""); */
	if (!m_Y) /* first line is page header, we don't need that. */
	{
		m_double_height = -1;
		return;
	}
		
	if (m_double_height == m_Y)
	{
		m_double_height = -1;
		return;
	}

	int last_was_white = 1, color = 7; /* start with whitespace. start with color=white. (that's unrelated.) */
	
	std::string text;
	
//	eDebug("handle subtitle line: %d len", len);
	for (int i=0; i<len; ++i)
	{
		unsigned char b = decode_odd_parity(data + i);
	
		if (b < 0x10) /* spacing attribute */
		{
			if (b < 8) /* colors */
			{
				if (b != color) /* new color is split into a new string */
				{
					addSubtitleString(color, text);
					text = "";
					color = b;
				}
			} else if (b == 0xd)
			{
				m_double_height = m_Y + 1;
			} else if (b != 0xa && b != 0xb) /* box */
				eDebug("[ignore %x]", b);
				/* ignore other attributes */
		} else
		{
			//eDebugNoNewLine("%c", b);
				/* no more than one whitespace, only printable chars */
			if (((!last_was_white) || (b != ' ')) && (b >= 0x20))
			{
				text += b;
				last_was_white = b == ' ';
			}
		}
	}
	//eDebug("");
	addSubtitleString(color, text);
}

void eDVBTeletextParser::handlePageEnd(int have_pts, const pts_t &pts)
{
//	eDebug("handle page end");
	addSubtitleString(-2, ""); /* end last line */ 
	
	m_subtitle_page.m_have_pts = have_pts;
	m_subtitle_page.m_pts = pts;
	m_subtitle_page.m_timeout = 90000 * 20; /* 20s */
	if (m_page_number != -1)
		sendSubtitlePage();  /* send assembled subtitle page to display */
}

void eDVBTeletextParser::setPage(int page)
{
	if (page > 0)
		eDebug("enable teletext subtitle page %d", page);
	else
		eDebug("disable teletext subtitles");
	m_page_number = page;
	m_page_M = (page >> 8) & 7; /* magazine to look for */
	m_page_X = page & 0xFF;     /* page number */
}

void eDVBTeletextParser::connectNewPage(const Slot1<void, const eDVBTeletextSubtitlePage&> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_new_subtitle_page.connect(slot));
}

void eDVBTeletextParser::addSubtitleString(int color, std::string string)
{
//	eDebug("add subtitle string: %s, col %d", string.c_str(), color);

	int force_cell = 0;

	if (string.substr(0, 2) == "- ")
	{
		string = string.substr(2);
		force_cell = 1;
	}

	int len = string.length();
	int idx = 0;

	while (idx < len)
	{
		if (string[idx] >= 0x20)
			string[idx] = MapTeletextG0Latin1Char(0, (m_C >> 11), string[idx]);
		++idx;
	}

//	eDebug("color %d, m_subtitle_color %d", color, m_subtitle_color);
	gRGB rgbcol((color & 1) ? 255 : 128, (color & 2) ? 255 : 128, (color & 4) ? 255 : 128);
	if ((color != m_subtitle_color || force_cell) && !m_subtitle_text.empty() && ((color == -2) || !string.empty()))
	{
//		eDebug("add text |%s|: %d != %d || %d", m_subtitle_text.c_str(), color, m_subtitle_color, force_cell);
		m_subtitle_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(rgbcol, m_subtitle_text));
		m_subtitle_text = "";
	} else if (!m_subtitle_text.empty() && m_subtitle_text[m_subtitle_text.size()-1] != ' ')
		m_subtitle_text += " ";
	
	if (!string.empty())
	{
//		eDebug("set %d as new color", color);
		m_subtitle_color = color;
		m_subtitle_text += string;
	}
}

void eDVBTeletextParser::sendSubtitlePage()
{
//	eDebug("subtitle page:");
	//for (unsigned int i = 0; i < m_subtitle_page.m_elements.size(); ++i)
	//	eDebug("%s", m_subtitle_page.m_elements[i].m_text.c_str());
	m_new_subtitle_page(m_subtitle_page);
}
