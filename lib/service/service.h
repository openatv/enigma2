#ifndef __service_h
#define __service_h

#include <map>
#include <lib/base/object.h>
#include <lib/service/iservice.h>

class eServiceCenter;

typedef ePtr<eServiceCenter> eServiceCenterPtr;

class eServiceCenter: public iServiceHandler
{
DECLARE_REF;
private:
	std::map<int,iServiceHandlerPtr> handler;
	static eServiceCenter *instance;
public:
	eServiceCenter();
	virtual ~eServiceCenter();

		// iServiceHandler
	RESULT play(const eServiceReference &, iPlayableServicePtr &ptr);
	RESULT record(const eServiceReference &, iRecordableServicePtr &ptr);
	RESULT list(const eServiceReference &, iListableServicePtr &ptr);
	RESULT info(const eServiceReference &, ePtr<iServiceInformation> &ptr);
	
		// eServiceCenter
	static RESULT getInstance(eServiceCenterPtr &ptr) { ptr = instance; return 0; }
	RESULT addServiceFactory(int id, iServiceHandler *hnd);
	RESULT removeServiceFactory(int id);
};

#endif
