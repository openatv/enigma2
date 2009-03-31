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
	eMPEGStreamInformation();
	~eMPEGStreamInformation();
		/* we order by off_t here, since the timestamp may */
		/* wrap around. */
		/* we only record sequence start's pts values here. */
	std::map<off_t, pts_t> m_access_points;
		/* timestampDelta is in fact the difference between */
		/* the PTS in the stream and a real PTS from 0..max */
	std::map<off_t, pts_t> m_timestamp_deltas;

		/* these are non-fixed up pts value (like m_access_points), just used to accelerate stuff. */
	std::multimap<pts_t, off_t> m_pts_to_offset; 

	int startSave(const char *filename);
	int stopSave(void);
	int load(const char *filename);
	
		/* recalculates timestampDeltas */
	void fixupDiscontinuties();
	
		/* get delta at specific offset */
	pts_t getDelta(off_t offset);
	
		/* fixup timestamp near offset, i.e. convert to zero-based */
	int fixupPTS(const off_t &offset, pts_t &ts);

		/* get PTS before offset */	
	int getPTS(off_t &offset, pts_t &pts);
	
		/* inter/extrapolate timestamp from offset */
	pts_t getInterpolated(off_t offset);
	
	off_t getAccessPoint(pts_t ts, int marg=0);
	
	int getNextAccessPoint(pts_t &ts, const pts_t &start, int direction);
	
	bool empty();
	
	typedef unsigned long long structure_data;
		/* this is usually:
			sc | (other_information << 8)
			but is really specific to the used video encoder.
		*/
	void writeStructureEntry(off_t offset, structure_data data);

		/* get a structure entry at given offset (or previous one, if no exact match was found).
		   optionall, return next element. Offset will be returned. this allows you to easily 
		   get previous and next structure elements. */
	int getStructureEntry(off_t &offset, unsigned long long &data, int get_next);

	std::string m_filename;
	int m_structure_cache_valid;
	unsigned long long m_structure_cache[1024];
	FILE *m_structure_read, *m_structure_write;
};

	/* Now we define the parser's state: */
class eMPEGStreamParserTS
{
public:
	eMPEGStreamParserTS(eMPEGStreamInformation &streaminfo);
	void parseData(off_t offset, const void *data, unsigned int len);
	void setPid(int pid, int streamtype);
	int getLastPTS(pts_t &last_pts);
private:
	eMPEGStreamInformation &m_streaminfo;
	unsigned char m_pkt[188];
	int m_pktptr;
	int processPacket(const unsigned char *pkt, off_t offset);
	inline int wantPacket(const unsigned char *hdr) const;
	int m_pid, m_streamtype;
	int m_need_next_packet;
	int m_skip;
	int m_last_pts_valid;
	pts_t m_last_pts;
};

#endif
