#ifndef __service_h
#define __service_h

#include <map>
#include <lib/base/object.h>
#include <lib/service/iservice.h>

class eServiceCenter;

#ifndef SWIG
typedef ePtr<eServiceCenter> eServiceCenterPtr;
#endif

class eServiceCenter: public iServiceHandler
{
	DECLARE_REF(eServiceCenter);
	std::map<int,ePtr<iServiceHandler> > handler;
	std::map<std::string, int> extensions_r;
	static eServiceCenter *instance;
#ifdef SWIG
	eServiceCenter();
	~eServiceCenter();
#endif
public:
#ifndef SWIG
	eServiceCenter();
	virtual ~eServiceCenter();

	int getServiceTypeForExtension(const char *str);
	int getServiceTypeForExtension(const std::string &str);

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);

		// eServiceCenter
	static RESULT getPrivInstance(ePtr<eServiceCenter> &ptr) { ptr = instance; return 0; }
	RESULT addServiceFactory(int id, iServiceHandler *hnd, std::list<std::string> &extensions);
	RESULT removeServiceFactory(int id);
	RESULT addFactoryExtension(int id, const char *extension);
	RESULT removeFactoryExtension(int id, const char *extension);
#endif
	static SWIG_VOID(RESULT) getInstance(ePtr<iServiceHandler> &SWIG_NAMED_OUTPUT(ptr)) { ptr = instance; return 0; }
};

#endif
