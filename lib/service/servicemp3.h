#ifndef __servicemp3_h
#define __servicemp3_h

#include <lib/service/iservice.h>

class eServiceFactoryMP3: public virtual iServiceHandler, public virtual iObject
{
DECLARE_REF;
public:
	eServiceFactoryMP3();
	virtual ~eServiceFactoryMP3();
	enum { id = 0x1001 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
};

class eServiceMP3: public virtual iPlayableService, public virtual iPauseableService, public virtual iObject
{
	friend class eServiceFactoryMP3;
	std::string filename;
	eServiceMP3(const char *filename);	
	int ref;
public:
	virtual ~eServiceMP3();

		// iObject
	void AddRef();
	void Release();

		// iPlayableService
	RESULT start();
	RESULT getIPausableService(ePtr<iPauseableService> &ptr);

		// iPausableService
	RESULT pause();
	RESULT unpause();
};

#endif
