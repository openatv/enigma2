#ifndef __lib_dvb_pesparse_h
#define __lib_dvb_pesparse_h

class ePESParser
{
public:
	ePESParser();
	void setStreamID(unsigned char id);
	void processData(unsigned char *data, int len);
	virtual void processPESPacket(unsigned char *pkt, int len) = 0;
private:
	unsigned char m_pes_buffer[65536];
	int m_pes_position, m_pes_length;
	unsigned char m_header[4];
};

#endif
