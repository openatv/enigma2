#ifndef __servicem2ts_h
#define __servicem2ts_h

#include <lib/service/servicedvb.h>

class eServiceFactoryM2TS: public iServiceHandler
{
	DECLARE_REF(eServiceFactoryM2TS);
public:
	eServiceFactoryM2TS();
	virtual ~eServiceFactoryM2TS();
	enum { id = 0x3 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
};

class eServiceM2TS: public eDVBServicePlay
{
	friend class eServiceFactoryM2TS;
protected:
	eServiceM2TS(const eServiceReference &ref);
	ePtr<iTsSource> createTsSource(eServiceReferenceDVB &ref);

	// iSeekableService
	RESULT isCurrentlySeekable();
};

#endif
