#ifndef __dvb_isection_h
#define __dvb_isection_h

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
	int pid, tid, tidext;
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
	};
	int flags;
};

class iDVBSectionReader: public virtual iObject
{
public:
	virtual RESULT start(const eDVBSectionFilterMask &mask)=0;
	virtual RESULT stop()=0;
	virtual RESULT connectRead(const Slot1<void,const __u8*> &read, ePtr<eConnection> &conn)=0;
};

#endif
