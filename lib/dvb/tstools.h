#ifndef __lib_dvb_tstools_h
#define __lib_dvb_tstools_h

#include <sys/types.h>
#include <lib/dvb/pvrparse.h>
#include <lib/base/rawfile.h>
#include <lib/base/elock.h>

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

	void setSource(ePtr<iTsSource> &source, const char *streaminfo_filename=NULL);
	void closeSource();

	int openFile(const char *filename, int nostreaminfo = 0);
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
	int getOffset(off_t &offset, pts_t &pts, int marg=0);
	
	int getNextAccessPoint(pts_t &ts, const pts_t &start, int direction);
	
	void calcBegin();
	void calcEnd();
	
	int calcLen(pts_t &len);
	
	int calcBitrate(); /* in bits/sec */
	
	void takeSamples();
	int takeSample(off_t off, pts_t &p);
	
	int findPMT(int &pmt_pid, int &service_id);
	
	enum { 
		frametypeI = 1, 
		frametypeP = 2, 
		frametypeB = 4, 
		frametypeAll = frametypeI | frametypeP | frametypeB
	};
	/** findFrame: finds a specific frame at a given position
	
	findFrame will look for the specified frame type starting at the given position, moving forward
	(when direction is >0) or backward (when direction is <0). (direction=0 is a special case and also moves
	forward, but starts with the last frame.)
	
	return values are the new offset, the length of the found frame (both unaligned), and the (signed) 
	number of frames skipped. */
	int findFrame(off_t &offset, size_t &len, int &direction, int frame_types = frametypeI);
	int findNextPicture(off_t &offset, size_t &len, int &distance, int frame_types = frametypeAll);
private:
	int m_pid;
	int m_maxrange;

	ePtr<iTsSource> m_source;

	int m_begin_valid, m_end_valid;
	pts_t m_pts_begin, m_pts_end;
	off_t m_offset_begin, m_offset_end;
	
		/* for simple linear interpolation */
	std::map<pts_t, off_t> m_samples;
	int m_samples_taken;
	
	eMPEGStreamInformation m_streaminfo;
	int m_use_streaminfo;
	off_t m_last_filelength;
	int m_futile;
};

#endif
