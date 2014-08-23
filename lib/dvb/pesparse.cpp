#include <lib/base/eerror.h>
#include <lib/dvb/pesparse.h>
#include <memory.h>

ePESParser::ePESParser()
{
	m_pes_position = 0;
	m_pes_length = 0;
	m_header[0] = 0;
	m_header[1] = 0;
	m_header[2] = 1;
	setStreamID(0); /* must be overridden */
}

void ePESParser::setStreamID(unsigned char id, unsigned char id_mask)
{
	m_header[3] = id;
	m_stream_id_mask = id_mask;
}

void ePESParser::processData(const uint8_t *p, int len)
{
		/* this is a state machine, handling arbitary amounts of pes-formatted data. */
	while (len)
	{
		if (m_pes_position >= 6) // length ok?
		{
			int max = m_pes_length - m_pes_position;
			if (max > len)
				max = len;
			memcpy(m_pes_buffer + m_pes_position, p, max);
			m_pes_position += max;
			p += max;

			len -= max;

			if (m_pes_position == m_pes_length)
			{
				processPESPacket(m_pes_buffer, m_pes_position);
				m_pes_position = 0;
			}
		} else
		{
			if (m_pes_position < 4)
			{
				unsigned char ch = *p;
				if (m_pes_position == 3)
					ch &= m_stream_id_mask;
				if (ch != m_header[m_pes_position])
				{
//					eDebug("sync lost at %d (%02x)", m_pes_position, *p);
					m_pes_position = 0;
					while (m_header[m_pes_position] == ch) /* guaranteed to stop at the old m_pes_position */
						m_pes_position++;
					p++;
					len--;
					continue;
				}
			}
			m_pes_buffer[m_pes_position++] = *p++; len--;
			if (m_pes_position == 6)
			{
				m_pes_length = ((m_pes_buffer[4] << 8) | m_pes_buffer[5]) + 6;
			}
		}
	}
}
