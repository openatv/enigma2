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

class eServiceMP3: public virtual iPlayableService, public virtual iPauseableService, public virtual iServiceInformation, public virtual iObject, public Object
{
DECLARE_REF;
private:
	friend class eServiceFactoryMP3;
	std::string filename;
	eServiceMP3(const char *filename);	
	eTimer test;
	void test_end();
	Signal2<void,iPlayableService*,int> m_event;
	enum
	{
		stIdle, stRunning, stStopped,
	};
	int m_state;
public:
	virtual ~eServiceMP3();

		// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT getIPausableService(ePtr<iPauseableService> &ptr);

		// iPausableService
	RESULT pause();
	RESULT unpause();
	
	RESULT getIServiceInformation(ePtr<iServiceInformation>&);
	
		// iServiceInformation
	RESULT getName(eString &name);
};

#endif
