#ifndef __lib_dvb_radiotext_h
#define __lib_dvb_radiotext_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/gdi/gpixmap.h>

class eDVBRdsDecoder: public iObject, public ePESParser, public sigc::trackable
{
	DECLARE_REF(eDVBRdsDecoder);
	int msgPtr, bsflag, qdar_pos, t_ptr, qdarmvi_show;
	unsigned char m_message_buffer[66], lastmessage[66], datamessage[256], rtp_buf[5], leninfo, text_len, text_len2, state;
	std::string m_rt_message;     // radiotext message
	std::string m_rtplus_message; // radiotext plus message
	unsigned char rtp_item[64][64], rtplus_osd[128]; //rtp
	short m_rtp_togglebit, m_rtp_runningbit;
	unsigned char qdar[60*1024]; //60 kB for holding Rass qdar archive
	unsigned short crc16, crc;
	long part, parts, partcnt;
	unsigned char rass_picture_mask[5];  // 40 bits... (10 * 4 pictures)
	void addToPictureMask(int id);
	void removeFromPictureMask(int id);
	int m_mode;
	int m_pid;
	int m_audio_type;
public:
	enum { RadioTextChanged, RtpTextChanged, RassInteractivePicMaskChanged, RecvRassSlidePic };
	eDVBRdsDecoder(iDVBDemux *demux, int mode, int audio_type);
	~eDVBRdsDecoder();
	int start(int pid);
	void connectEvent(const sigc::slot<void(int)> &slot, ePtr<eConnection> &connection);
	std::string getRadioText() { return m_rt_message; }
	std::string getRtpText() { return m_rtplus_message; }
	ePyObject getRassPictureMask();
	std::string getRassPicture(int page, int subpage);
	std::string getRassSlideshowPicture() { return "/tmp/RassLast.mvi"; }
	int getPid() { return m_pid; }
private:
	void abortNonAvail();
	void processPESPacket(uint8_t *pkt, int len);
	void processPESAACPacket(uint8_t *pkt, int pos, int len);
	void processAACFrame(uint8_t *data, int len);
	void processPESMPEGPacket(uint8_t *pkt, int pos, int len);
	void gotAncillaryData(const uint8_t *data, int len);
	void process_qdar(unsigned char*);
	void convertRdsMessageToUTF8(unsigned char* buffer, std::string& message);
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
	sigc::signal<void(int)> m_event;
	ePtr<eTimer> m_abortTimer;
};

#endif
