#include <lib/base/eerror.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/idemux.h>
#include <lib/gdi/gpixmap.h>

// G0 and G2 national option table
// see table 33 in ETSI EN 300 706
// use it with (triplet 1 bits 14-11)*(ctrl bits C12-14)

unsigned char NationalOptionSubsetsLookup[16*8] =
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

unsigned char NationalReplaceMap[128] =
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

// national option subsets (UTF8)
// see table 36 in ETSI EN 300 706

unsigned int NationalOptionSubsets[13*14] = {
	0, 0x0023, 0xc5af, 0xc48d, 0xc5a3, 0xc5be, 0xc3bd, 0xc3ad, 0xc599, 0xc3a9, 0xc3a1, 0xc49b, 0xc3ba, 0xc5a1, // Slovak/Czech
	0, 0xc2a3, 0x0024, 0x0040, 0xe28690, 0xc2bd, 0xe28692, 0xe28691, 0x0023, 0x002d, 0xc2bc, 0xc781, 0xc2be, 0xc3b7, // English
	0, 0x0023, 0xc3b5, 0xc5A0, 0xc384, 0xc396, 0xc5bd, 0xc39c, 0xc395, 0xc5a1, 0xc3a4, 0xc3b6, 0xc5be, 0xc3bc, // Estonian
	0, 0xc3a9, 0xc3af, 0xc3a0, 0xc3ab, 0xc3aa, 0xc3b9, 0xc3ae, 0x0023, 0xc3a8, 0xc3a2, 0xc3b4, 0xc3bb, 0xc3a7, // French
	0, 0x0023, 0x0024, 0xc2a7, 0xc384, 0xc396, 0xc39c, 0x005e, 0x005f, 0xcb9a, 0xc3a4, 0xc3b6, 0xc3bc, 0xc39f, // German
	0, 0xc2a3, 0x0024, 0xc3a9, 0xcb9a, 0xc3a7, 0xe28692, 0xe28691, 0x0023, 0xc3b9, 0xc3a0, 0xc3b2, 0xc3a8, 0xc3ac, // Italian
	0, 0x0023, 0x0024, 0xc5a0, 0xc497, 0xc8a9, 0xc5bd, 0xc48d, 0xc5ab, 0xc5a1, 0xc485, 0xc5b3, 0xc5be, 0xc4af/*FIXMEE*/, // Lithuanian/Lettish
	0, 0x0023, 0xc584, 0xc485, 0xc6b5, 0xc59a, 0xc581, 0xc487, 0xc3b3, 0xc499, 0xc5bc, 0xc59b, 0xc582, 0xc5ba, // Polish
	0, 0xc3a7, 0x0024, 0xc2a1, 0xc3a1, 0xc3a9, 0xc3ad, 0xc3b3, 0xc3ba, 0xc2bf, 0xc3bc, 0xc3b1, 0xc3a8, 0xc3a0, // Spanish/Portuguese
	0, 0x0023, 0xc2a4, 0xc5a2, 0xc382, 0xc59e, 0xc78d, 0xc38e, 0xc4b1, 0xc5a3, 0xc3a2, 0xc59f, 0xc78e, 0xc3ae, // Rumanian
	0, 0x0023, 0xc38b, 0xc48c, 0xc486, 0xc5bd, 0xc490, 0xc5a0, 0xc3ab, 0xc48d, 0xc487, 0xc5be, 0xc491, 0xc5a1, // Slovenian/Serbian/Croation
	0, 0x0023, 0xc2a4, 0xc389, 0xc384, 0xc396, 0xc385, 0xc39c, 0x005f, 0xc3a9, 0xc3a4, 0xc3b6, 0xc3a5, 0xc3bc, // Finnish/Hungarian/Swedish
	0, 0xee8080/*FIXME*/, 0xc7a7, 0xc4b0, 0xc59e, 0xc396, 0xc387, 0xc39c, 0xc7a6, 0xc4b1, 0xc59f, 0xc3b6, 0xc3a7, 0xc3bc  // Turkish
};

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
	
	setPageAndMagazine(0,0);
	
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
		
//		if (data_unit_id != 0x03)
//		{
//			/* eDebug("non subtitle data unit id %d", data_unit_id); */
//			break;
//		}
		
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
			if ((serial_mode || m_M == m_page_M) && m_page_open)
			{
				handlePageEnd(have_pts, pts);
				m_page_open = 0;
			}
			
			m_X = decode_hamming_84(data+1) * 0x10 + decode_hamming_84(data);
			
			if ((m_C & (1<<6)) && (m_X != 0xFF)) /* scan for pages with subtitle bit set */
			{
				eDVBServicePMTHandler::subtitleStream s;
				s.pid = m_pid;
				s.subtitling_type = 0x01; // ebu teletext subtitle
				s.teletext_page_number = m_X & 0xFF;
				s.teletext_magazine_number = m_M & 7;
				m_found_subtitle_pages.insert(s);
			}

				/* correct page on correct magazine? open page. */
			if (m_M == m_page_M && m_X == m_page_X)
			{
				handlePageStart();
				m_page_open = 1;
				handleLine(data + 8, 32);
			}
		} else if (m_Y < 26) // directly displayable packet
		{
			/* data for the selected page ? */
			if (m_M == m_page_M && m_page_open)
				handleLine(data, 40);
		}
/*		else
		{
			if (m_M == m_page_M && m_page_open)
				eDebug("ignore packet %d, disgnation code %d", m_Y, decode_hamming_84(data));
		}*/
	}
}

int eDVBTeletextParser::start(int pid)
{
	m_page_open = 0;

	if (m_pes_reader)
	{
		m_pid = pid;
		return m_pes_reader->start(pid);
	}
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
	if (m_page_X != 0)
		sendSubtitlePage();  /* send assembled subtitle page to display */
}

void eDVBTeletextParser::setPageAndMagazine(int page, int magazine)
{
	if (page > 0)
		eDebug("enable teletext subtitle page %x%02x", magazine, page);
	else
		eDebug("disable teletext subtitles");
	m_page_M = magazine&7; /* magazine to look for */
	m_page_X = page&0xFF;  /* page number */
}

void eDVBTeletextParser::connectNewPage(const Slot1<void, const eDVBTeletextSubtitlePage&> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_new_subtitle_page.connect(slot));
}

void eDVBTeletextParser::addSubtitleString(int color, std::string string)
{
//	eDebug("add subtitle string: %s, col %d", string.c_str(), color);
	static unsigned char out[512];
	int force_cell = 0;

	if (string.substr(0, 2) == "- ")
	{
		string = string.substr(2);
		force_cell = 1;
	}

	int len = string.length(),
		idx = 0,
		outidx = 0,
		Gtriplet = 0,
		nat_opts = (m_C >> 11) & 0x7,
		nat_subset = NationalOptionSubsetsLookup[Gtriplet*8+nat_opts];
	while (idx < len)
	{
		unsigned char c = string[idx];
		if (c >= 0x20)
		{
			if (NationalReplaceMap[c])
			{
				unsigned int utf8_code =
					NationalOptionSubsets[nat_subset*14+c];
				if (utf8_code > 0xFFFFFF)
					out[outidx++]=(utf8_code&0xFF000000)>>24;
				if (utf8_code > 0xFFFF)
					out[outidx++]=(utf8_code&0xFF0000)>>16;
				if (utf8_code > 0xFF)
					out[outidx++]=(utf8_code&0xFF00)>>8;
				out[outidx++]=utf8_code&0xFF;
			}
			else
				out[outidx++] = c;
		}
		++idx;
	}

//	eDebug("color %d, m_subtitle_color %d", color, m_subtitle_color);
	gRGB rgbcol((color & 1) ? 255 : 128, (color & 2) ? 255 : 128, (color & 4) ? 255 : 128);
	if ((color != m_subtitle_color || force_cell) && !m_subtitle_text.empty() && ((color == -2) || outidx))
	{
//		eDebug("add text |%s|: %d != %d || %d", m_subtitle_text.c_str(), color, m_subtitle_color, force_cell);
		m_subtitle_page.m_elements.push_back(eDVBTeletextSubtitlePageElement(rgbcol, m_subtitle_text));
		m_subtitle_text = "";
	} else if (!m_subtitle_text.empty() && m_subtitle_text[m_subtitle_text.size()-1] != ' ')
		m_subtitle_text += " ";
	
	if (outidx)
	{
//		eDebug("set %d as new color", color);
		m_subtitle_color = color;
		m_subtitle_text += std::string((const char*)out, outidx);
	}
}

void eDVBTeletextParser::sendSubtitlePage()
{
//	eDebug("subtitle page:");
	//for (unsigned int i = 0; i < m_subtitle_page.m_elements.size(); ++i)
	//	eDebug("%s", m_subtitle_page.m_elements[i].m_text.c_str());
	m_new_subtitle_page(m_subtitle_page);
}
