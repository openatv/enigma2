#ifndef __dvb_idemux_h
#define __dvb_idemux_h

#include <lib/dvb/idvb.h>

class iDVBSectionReader: public iObject
{
public:
	virtual RESULT setBufferSize(int size)=0;
	virtual RESULT start(const eDVBSectionFilterMask &mask)=0;
	virtual RESULT stop()=0;
	virtual RESULT connectRead(const Slot1<void,const uint8_t*> &read, ePtr<eConnection> &conn)=0;
	virtual ~iDVBSectionReader() { };
};

class iDVBPESReader: public iObject
{
public:
	virtual RESULT setBufferSize(int size)=0;
	virtual RESULT start(int pid)=0;
	virtual RESULT stop()=0;
	virtual RESULT connectRead(const Slot2<void,const uint8_t*, int> &read, ePtr<eConnection> &conn)=0;
	virtual ~iDVBPESReader() { };
};

	/* records a given set of pids into a file descriptor. */
	/* the FD must not be modified between start() and stop() ! */
class iDVBTSRecorder: public iObject
{
public:
	virtual RESULT setBufferSize(int size) = 0;
	virtual RESULT start() = 0;
	virtual RESULT addPID(int pid) = 0;
	virtual RESULT removePID(int pid) = 0;

	enum timing_pid_type { none = -1, video_pid, audio_pid };
	virtual RESULT setTimingPID(int pid, timing_pid_type pidtype, int streamtype) = 0;

	virtual RESULT setTargetFD(int fd) = 0;
		/* for saving additional meta data. */
	virtual RESULT setTargetFilename(const std::string& filename) = 0;
	virtual RESULT setBoundary(off_t max) = 0;
	virtual RESULT enableAccessPoints(bool enable) = 0;

	virtual RESULT stop() = 0;

	virtual RESULT getCurrentPCR(pts_t &pcr) = 0;
	virtual RESULT getFirstPTS(pts_t &pts) = 0;

	enum {
		eventWriteError,
				/* a write error has occurred. data won't get lost if fd is writable after return. */
				/* you MUST respond with either stop() or fixing the problems, else you get the error */
				/* again. */
		eventReachedBoundary,
				/* the programmed boundary was reached. you might set a new target fd. you can close the */
				/* old one. */
	};
	virtual RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn)=0;
};

#endif
