#ifndef __dvb_isection_h
#define __dvb_isection_h

#include <lib/dvb/idvb.h>

class iDVBSectionReader: public iObject
{
public:
	virtual RESULT start(const eDVBSectionFilterMask &mask)=0;
	virtual RESULT stop()=0;
	virtual RESULT connectRead(const sigc::slot1<void,const uint8_t*> &read, ePtr<eConnection> &conn)=0;
	virtual ~iDVBSectionReader() { };
};

#endif
