#ifndef __lib_dvb_tstools_h
#define __lib_dvb_tstools_h

#include <sys/types.h>

/*
 * Note: we're interested in PTS values, not STC values.
 * thus we're not evaluating PES headers, not adaption fields.
 */

class eDVBTSTools
{
public:
	typedef unsigned long long pts_t;
	eDVBTSTools();
	~eDVBTSTools();

	int openFile(const char *filename);
	void closeFile();
	
	void setSyncPID(int pid);
	void setSearchRange(int maxrange);
	
		/* get first PTS *after* the given offset. */
	int getPTS(off_t &offset, pts_t &pts);
	
	void calcBegin();
	void calcEnd();
	
	int calcLen(pts_t &len);
	
private:
	int m_fd, m_pid;
	int m_maxrange;
	
	int m_begin_valid, m_end_valid;
	pts_t m_pts_begin, m_pts_end;
	off_t m_offset_begin, m_offset_end;
};


#endif
