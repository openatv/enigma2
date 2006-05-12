#ifndef __dvb_idemux_h
#define __dvb_idemux_h

#include <lib/dvb/idvb.h>

#ifndef DMX_FILTER_SIZE
#define DMX_FILTER_SIZE   16
#endif

struct eDVBSectionFilterMask
{
	int pid;
		/* mode is 0 for positive, 1 for negative filtering */
	__u8 data[DMX_FILTER_SIZE], mask[DMX_FILTER_SIZE], mode[DMX_FILTER_SIZE];
	enum {
		rfCRC=1,
		rfNoAbort=2
	};
	int flags;
};

struct eDVBTableSpec
{
	int pid, tid, tidext, tid_mask, tidext_mask;
	int version;
	int timeout;        /* timeout in ms */
	enum
	{
		tfInOrder=1,
		/*
			tfAnyVersion      filter ANY version
			0                 filter all EXCEPT given version (negative filtering)
			tfThisVersion     filter only THIS version
		*/
		tfAnyVersion=2,
		tfThisVersion=4,
		tfHaveTID=8,
		tfHaveTIDExt=16,
		tfCheckCRC=32,
		tfHaveTimeout=64,
		tfHaveTIDMask=128,
		tfHaveTIDExtMask=256
	};
	int flags;
};

class iDVBSectionReader: public iObject
{
public:
	virtual RESULT start(const eDVBSectionFilterMask &mask)=0;
	virtual RESULT stop()=0;
	virtual RESULT connectRead(const Slot1<void,const __u8*> &read, ePtr<eConnection> &conn)=0;
	virtual ~iDVBSectionReader() { };
};

class iDVBPESReader: public iObject
{
public:
	virtual RESULT start(int pid)=0;
	virtual RESULT stop()=0;
	virtual RESULT connectRead(const Slot2<void,const __u8*, int> &read, ePtr<eConnection> &conn)=0;
	virtual ~iDVBPESReader() { };
};

	/* records a given set of pids into a file descriptor. */
	/* the FD must not be modified between start() and stop() ! */
class iDVBTSRecorder: public iObject
{
public:
	virtual RESULT start() = 0;
	virtual RESULT addPID(int pid) = 0;
	virtual RESULT removePID(int pid) = 0;
	
	virtual RESULT setTimingPID(int pid) = 0;
	
	virtual RESULT setTargetFD(int fd) = 0;
		/* for saving additional meta data. */
	virtual RESULT setTargetFilename(const char *filename) = 0;
	virtual RESULT setBoundary(off_t max) = 0;
	
	virtual RESULT stop() = 0;
	
	enum {
		eventWriteError,
				/* a write error has occured. data won't get lost if fd is writable after return. */
				/* you MUST respond with either stop() or fixing the problems, else you get the error */
				/* again. */
		eventReachedBoundary,
				/* the programmed boundary was reached. you might set a new target fd. you can close the */
				/* old one. */
	};
	virtual RESULT connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &conn)=0;
};

#endif
