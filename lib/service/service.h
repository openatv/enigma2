#ifndef __service_h
#define __service_h

#include <map>
#include <lib/base/object.h>
#include <lib/service/iservice.h>

class eServiceCenter: public virtual iServiceHandler, public virtual iObject
{
DECLARE_REF;
private:
	std::map<int,ePtr<iServiceHandler> > handler;
	static eServiceCenter *instance;
public:
	eServiceCenter();
	virtual ~eServiceCenter();

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	
		// eServiceCenter
	static RESULT getInstance(ePtr<eServiceCenter> &ptr) { ptr = instance; return 0; }
	RESULT addServiceFactory(int id, iServiceHandler *hnd);
	RESULT removeServiceFactory(int id);
};

#endif
