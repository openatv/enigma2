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
	
		/* fixup timestamp near offset, i.e. convert to zero-based */
	int fixupPTS(const off_t &offset, pts_t &ts);

		/* get PTS before offset */	
	int getPTS(off_t &offset, pts_t &pts);
	
	
	off_t getAccessPoint(pts_t ts, int marg=0);
	
	int getNextAccessPoint(pts_t &ts, const pts_t &start, int direction);
	
	bool hasAccessPoints() { return !m_access_points.empty(); }
	bool hasStructure() { return m_structure_read_fd >= 0; }
	
		/* get a structure entry at given offset (or previous one, if no exact match was found).
		   optionally, return next element. Offset will be returned. this allows you to easily 
		   get previous and next structure elements. */
	int getStructureEntryFirst(off_t &offset, unsigned long long &data);
	int getStructureEntryNext(off_t &offset, unsigned long long &data, int delta);

	// Get first or last PTS value and offset.
	int getFirstFrame(off_t &offset, pts_t& pts);
	int getLastFrame(off_t &offset, pts_t& pts);
	
private:
	void close();
	int loadCache(int index);
	int moveCache(int index);
	/* inter/extrapolate timestamp from offset */
	pts_t getInterpolated(off_t offset);
	/* get delta at specific offset */
	pts_t getDelta(off_t offset);
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

	int m_structure_read_fd;

	int m_cache_index;   // Location of cache
	int m_current_entry; // For getStructureEntryNext
	int m_structure_cache_entries;
	int m_structure_file_entries; // Also to detect changes to file

	unsigned long long* m_structure_cache;
	int m_cache_end_index;
	unsigned long long* m_structure_cache_end;
	bool m_streamtime_accesspoints;
};

class eMPEGStreamInformationWriter
{
public:
	eMPEGStreamInformationWriter();
	~eMPEGStreamInformationWriter();
	/* Used by parser */
	int startSave(const std::string& filename);
	int stopSave(void);
	virtual void addAccessPoint(off_t offset, pts_t pts, bool streamtime);
	void writeStructureEntry(off_t offset, unsigned long long data);
private:
	void close();
	void unmap();
	void map();
	struct AccessPoint
	{
		off_t off;
		pts_t pts;
		AccessPoint(off_t o, pts_t p): off(o), pts(p) {}
	};
	std::deque<AccessPoint> m_access_points, m_streamtime_access_points;
	std::string m_filename;
	int m_structure_write_fd;
	void* m_write_buffer;
	size_t m_buffer_filled;
};


class eMPEGStreamParserTS: public eMPEGStreamInformationWriter
{
public:
	eMPEGStreamParserTS(int packetsize = 188);
	void parseData(off_t offset, const void *data, unsigned int len);
	void setPid(int pid, int streamtype);
	int getLastPTS(pts_t &last_pts);
private:
	unsigned char m_pkt[192];
	int m_pktptr;
	int processPacket(const unsigned char *pkt, off_t offset);
	inline int wantPacket(const unsigned char *pkt) const;
	void addAccessPoint(off_t offset, pts_t pts, bool streamtime = false);
	void addAccessPoint(off_t offset, pts_t pts, timespec &now, bool streamtime = false);
	int m_pid;
	int m_streamtype;
	int m_need_next_packet;
	int m_skip;
	int m_last_pts_valid; /* m_last_pts contains a valid value */
	pts_t m_last_pts; /* last pts value, either from mpeg stream, or measured in streamtime */
	bool m_pts_found; /* 'real' mpeg pts has been found, no longer measuring streamtime */
	bool m_has_accesspoints;
	int m_packetsize;
	int m_header_offset;
	timespec m_last_access_point; /* timespec at which the previous access point was reported */
};

#endif
