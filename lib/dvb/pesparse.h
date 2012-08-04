#ifndef __lib_dvb_pesparse_h
#define __lib_dvb_pesparse_h

#include <asm/types.h>

class ePESParser
{
public:
	ePESParser();
	void setStreamID(unsigned char id, unsigned char id_mask=0xff);
	void processData(const __u8 *data, int len);
	virtual void processPESPacket(__u8 *pkt, int len) = 0;
	virtual ~ePESParser() { }
private:
	unsigned char m_pes_buffer[65536+6];  // max pes packetlength + pes header
	int m_pes_position, m_pes_length;
	unsigned char m_header[4];
	unsigned char m_stream_id_mask;
};

#endif
