#ifndef __lib_dvb_tstools_h
#define __lib_dvb_tstools_h

#include <sys/types.h>
#include <lib/dvb/pvrparse.h>

/*
 * Note: we're interested in PTS values, not STC values.
 * thus we're evaluating PES headers, not adaption fields.
 */

typedef long long pts_t;

class eDVBTSTools
{
public:
	eDVBTSTools();
	~eDVBTSTools();

	int openFile(const char *filename);
	void closeFile();
	
	void setSyncPID(int pid);
	void setSearchRange(int maxrange);
	
		/* get first PTS *after* the given offset. */
		/* pts values are zero-based. */
	int getPTS(off_t &offset, pts_t &pts, int fixed=0);
	
		/* this fixes up PTS to end up in a [0..len) range.
		   discontinuities etc. are handled here.
		
		  input: 	
		    offset - approximate offset in file to resolve ambiguities
		    pts - video-pts (i.e. current STC of video decoder)
		  output:
		    pts - zero-based PTS value
		*/
	int fixupPTS(const off_t &offset, pts_t &pts);
	
		/* get (approximate) offset corresponding to PTS */
	int getOffset(off_t &offset, pts_t &pts);
	
	int getNextAccessPoint(pts_t &ts, const pts_t &start, int direction);
	
	void calcBegin();
	void calcEnd();
	
	int calcLen(pts_t &len);
	
	int calcBitrate(); /* in bits/sec */
	
private:
	int m_fd, m_pid;
	int m_maxrange;
	
	int m_begin_valid, m_end_valid;
	pts_t m_pts_begin, m_pts_end;
	off_t m_offset_begin, m_offset_end;
	
	eMPEGStreamInformation m_streaminfo;
	int m_use_streaminfo;
};

#endif
