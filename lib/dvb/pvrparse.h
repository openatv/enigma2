#ifndef __include_lib_dvb_pvrparse_h
#define __include_lib_dvb_pvrparse_h

#include <lib/dvb/idvb.h>
#include <map>
#include <set>

	/* This module parses TS data and collects valuable information  */
	/* about it, like PTS<->offset correlations and sequence starts. */

	/* At first, we define the collector class: */
class eMPEGStreamInformation
{
public:
		/* we order by off_t here, since the timestamp may */
		/* wrap around. */
		/* we only record sequence start's pts values here. */
	std::map<off_t, pts_t> m_access_points;
		/* timestampDelta is in fact the difference between */
		/* the PTS in the stream and a real PTS from 0..max */
	std::map<off_t, pts_t> m_timestamp_deltas;
	
	int save(const char *filename);
	int load(const char *filename);
	
		/* recalculates timestampDeltas */
	void fixupDiscontinuties();
	
		/* get delta at specific offset */
	pts_t getDelta(off_t offset);
	
		/* fixup timestamp near offset */
	pts_t fixuppts_t(off_t offset, pts_t ts);
	
		/* inter/extrapolate timestamp from offset */
	pts_t getInterpolated(off_t offset);
	
	off_t getAccessPoint(pts_t ts);
	
	bool empty();
};

	/* Now we define the parser's state: */
class eMPEGStreamParserTS
{
public:
	eMPEGStreamParserTS(eMPEGStreamInformation &streaminfo);
	void parseData(off_t offset, const void *data, unsigned int len);
	void setPid(int pid);
private:
	eMPEGStreamInformation &m_streaminfo;
	unsigned char m_pkt[188];
	int m_pktptr;
	int processPacket(const unsigned char *pkt, off_t offset);
	inline int wantPacket(const unsigned char *hdr) const;
	int m_pid;
	int m_need_next_packet;
	int m_skip;
};

#endif
