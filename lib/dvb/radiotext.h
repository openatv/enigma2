#ifndef __lib_dvb_radiotext_h
#define __lib_dvb_radiotext_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/gdi/gpixmap.h>

class eDVBRdsDecoder: public iObject, public ePESParser, public Object
{
	DECLARE_REF(eDVBRdsDecoder);
	int msgPtr, bsflag, qdar_pos, t_ptr, qdarmvi_show;
	unsigned char message[66], lastmessage[66], datamessage[256], rtp_buf[5], leninfo, text_len, text_len2, state;
	unsigned char rtp_item[64][64], rtplus_osd[64]; //rtp
	unsigned char qdar[60*1024]; //60 kB for holding Rass qdar archive
	unsigned short crc16, crc;
	long part, parts, partcnt;
	unsigned char rass_picture_mask[5];  // 40 bits... (10 * 4 pictures)
	void addToPictureMask(int id);
	void removeFromPictureMask(int id);
public:
	enum { RadioTextChanged, RtpTextChanged, RassInteractivePicMaskChanged, RecvRassSlidePic };
	eDVBRdsDecoder(iDVBDemux *demux);
	~eDVBRdsDecoder();
	int start(int pid);
	void connectEvent(const Slot1<void, int> &slot, ePtr<eConnection> &connection);
	const char *getRadioText() { return (const char*)message; }
	const char *getRtpText() { return (const char*)rtplus_osd; }
	ePyObject getRassPictureMask();
	std::string getRassPicture(int page, int subpage);
	std::string getRassSlideshowPicture() { return "/tmp/RassLast.mvi"; }
private:
	void abortNonAvail();
	void processPESPacket(__u8 *pkt, int len);
	inline void gotAncillaryData(__u8 *data, int len);
	void process_qdar(unsigned char*);
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
	Signal1<void, int> m_event;
	eTimer m_abortTimer;
};

#endif
