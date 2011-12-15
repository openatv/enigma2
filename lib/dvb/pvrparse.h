#ifndef __include_lib_dvb_pvrparse_h
#define __include_lib_dvb_pvrparse_h

#include <lib/dvb/idvb.h>
#include <map>
#include <set>
#include <deque>

	/* This module parses TS data and collects valuable information  */
	/* about it, like PTS<->offset correlations and sequence starts. */

class eMPEGStreamInformation
{
public:
	eMPEGStreamInformation();
	~eMPEGStreamInformation();

	int load(const char *filename);
	
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
	
	bool hasAccessPoints() { return !m_access_points.empty(); }
	bool hasStructure() { return m_structure_read != NULL; }
	
		/* get a structure entry at given offset (or previous one, if no exact match was found).
		   optionally, return next element. Offset will be returned. this allows you to easily 
		   get previous and next structure elements. */
	int getStructureEntry(off_t &offset, unsigned long long &data, int get_next);

private:
	/* recalculates timestampDeltas */
	void fixupDiscontinuties();
	/* we order by off_t here, since the timestamp may */
	/* wrap around. */
	/* we only record sequence start's pts values here. */
	std::map<off_t, pts_t> m_access_points;
	/* timestampDelta is in fact the difference between */
	/* the PTS in the stream and a real PTS from 0..max */
	std::map<off_t, pts_t> m_timestamp_deltas;
	/* these are non-fixed up pts value (like m_access_points), just used to accelerate stuff. */
	std::multimap<pts_t, off_t> m_pts_to_offset;

	int m_structure_cache_entries;
	unsigned long long m_structure_cache[2048];
	FILE *m_structure_read;
};

class eMPEGStreamInformationWriter
{
public:
	eMPEGStreamInformationWriter();
	~eMPEGStreamInformationWriter();
	/* Used by parser */
	int startSave(const std::string& filename);
	int stopSave(void);
	void addAccessPoint(off_t offset, pts_t pts) { m_access_points.push_back(AccessPoint(offset, pts)); }
	void writeStructureEntry(off_t offset, unsigned long long data);
private:
	struct AccessPoint
	{
		off_t off;
		pts_t pts;
		AccessPoint(off_t o, pts_t p): off(o), pts(p) {}
	};
	std::deque<AccessPoint> m_access_points;
	std::string m_filename;
	FILE *m_structure_write;
};


class eMPEGStreamParserTS
{
public:
	eMPEGStreamParserTS(eMPEGStreamInformationWriter &streaminfo);
	void parseData(off_t offset, const void *data, unsigned int len);
	void setPid(int pid, int streamtype);
	int getLastPTS(pts_t &last_pts);
private:
	eMPEGStreamInformationWriter &m_streaminfo;
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
