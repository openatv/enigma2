#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <string>
#include <lib/service/servicemp3.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>

// eServiceFactoryMP3

eServiceFactoryMP3::eServiceFactoryMP3()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryMP3::id, this);

	m_service_info = new eStaticServiceMP3Info();
}

eServiceFactoryMP3::~eServiceFactoryMP3()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryMP3::id);
}

DEFINE_REF(eServiceFactoryMP3)

	// iServiceHandler
RESULT eServiceFactoryMP3::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
		// check resources...
	ptr = new eServiceMP3(ref.path.c_str());
	return 0;
}

RESULT eServiceFactoryMP3::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryMP3::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryMP3::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_info;
	return 0;
}

// eStaticServiceMP3Info


// eStaticServiceMP3Info is seperated from eServiceMP3 to give information
// about unopened files.

// probably eServiceMP3 should use this class as well, and eStaticServiceMP3Info
// should have a database backend where ID3-files etc. are cached.
// this would allow listing the mp3 database based on certain filters.

DEFINE_REF(eStaticServiceMP3Info)

eStaticServiceMP3Info::eStaticServiceMP3Info()
{
}

RESULT eStaticServiceMP3Info::getName(const eServiceReference &ref, std::string &name)
{
	name = "MP3 file: " + ref.path;
	return 0;
}

// eServiceMP3

void eServiceMP3::test_end()
{
	eDebug("end of mp3!");
	stop();
}

eServiceMP3::eServiceMP3(const char *filename): filename(filename), test(eApp)
{
	m_state = stIdle;
	eDebug("SERVICEMP3 construct!");
}

eServiceMP3::~eServiceMP3()
{
	eDebug("SERVICEMP3 destruct!");
	if (m_state == stRunning)
		stop();
}

DEFINE_REF(eServiceMP3);	

RESULT eServiceMP3::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceMP3::start()
{
	assert(m_state == stIdle);
	
	m_state = stRunning;

	printf("mp3 starts\n");
	printf("MP3: %s start\n", filename.c_str());
	test.start(1000, 1);
	CONNECT(test.timeout, eServiceMP3::test_end);
	m_event(this, evStart);
	return 0;
}

RESULT eServiceMP3::stop()
{
	assert(m_state != stIdle);
	if (m_state == stStopped)
		return -1;
	test.stop();
	printf("MP3: %s stop\n", filename.c_str());
	m_state = stStopped;
	m_event(this, evEnd);
	return 0;
}

RESULT eServiceMP3::pause(ePtr<iPauseableService> &ptr) { ptr=this; return 0; }

		// iPausableService
RESULT eServiceMP3::pause() { printf("mp3 pauses!\n"); return 0; }
RESULT eServiceMP3::unpause() { printf("mp3 unpauses!\n"); return 0; }

RESULT eServiceMP3::info(ePtr<iServiceInformation>&i) { i = this; return 0; }

RESULT eServiceMP3::getName(std::string &name)
{
	name = "MP3 File: " + filename;
	return 0;
}

eAutoInitPtr<eServiceFactoryMP3> init_eServiceFactoryMP3(eAutoInitNumbers::service+1, "eServiceFactoryMP3");
