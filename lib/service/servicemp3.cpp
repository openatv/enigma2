#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <string>
#include <lib/service/servicemp3.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>

// eServiceFactoryMP3

eServiceFactoryMP3::eServiceFactoryMP3(): ref(0)
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryMP3::id, this);
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
	RESULT res;
		// check resources...
	ptr = new eServiceMP3(ref.path.c_str());
	res = ptr->start();
	if (res)
	{
		ptr = 0;
		return res;
	}
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

// eServiceMP3

eServiceMP3::eServiceMP3(const char *filename): filename(filename), ref(0)
{
	printf("MP3: %s start\n", filename);
}

eServiceMP3::~eServiceMP3()
{
	printf("MP3: %s stop\n", filename.c_str());
}
	
void eServiceMP3::AddRef()
{
	++ref;
}

void eServiceMP3::Release()
{
	if (!--ref)
		delete this;
}

RESULT eServiceMP3::start() { printf("mp3 starts\n"); return 0; }
RESULT eServiceMP3::getIPausableService(ePtr<iPauseableService> &ptr) { ptr=this; return 0; }

		// iPausableService
RESULT eServiceMP3::pause() { printf("mp3 pauses!\n"); return 0; }
RESULT eServiceMP3::unpause() { printf("mp3 unpauses!\n"); return 0; }


eAutoInitP0<eServiceFactoryMP3> init_eServiceFactoryMP3(eAutoInitNumbers::service+1, "eServiceFactoryMP3");
