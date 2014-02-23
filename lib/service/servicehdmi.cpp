#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/base/nconfig.h>
#include <lib/base/object.h>
#include <lib/dvb/decoder.h>
#include <lib/service/servicehdmi.h>
#include <lib/service/service.h>

#include <string>

eServiceFactoryHDMI::eServiceFactoryHDMI()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		sc->addServiceFactory(eServiceFactoryHDMI::id, this, extensions);
	}

	m_service_info = new eStaticServiceHDMIInfo();
}

eServiceFactoryHDMI::~eServiceFactoryHDMI()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		sc->removeServiceFactory(eServiceFactoryHDMI::id);
	}
}

DEFINE_REF(eServiceFactoryHDMI)

RESULT eServiceFactoryHDMI::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	ptr = new eServiceHDMI(ref);
	return 0;
}

RESULT eServiceFactoryHDMI::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr = 0;
	return -1;
}

RESULT eServiceFactoryHDMI::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr = 0;
	return -1;
}

RESULT eServiceFactoryHDMI::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_info;
	return 0;
}

RESULT eServiceFactoryHDMI::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
}

DEFINE_REF(eStaticServiceHDMIInfo)

eStaticServiceHDMIInfo::eStaticServiceHDMIInfo()
{
}

RESULT eStaticServiceHDMIInfo::getName(const eServiceReference &ref, std::string &name)
{
	if (ref.name.length())
	{
		name = ref.name;
	}
	else
	{
		name = "HDMI IN";
	}
	return 0;
}

int eStaticServiceHDMIInfo::getLength(const eServiceReference &ref)
{
	return -1;
}

int eStaticServiceHDMIInfo::getInfo(const eServiceReference &ref, int w)
{
	return iServiceInformation::resNA;
}

long long eStaticServiceHDMIInfo::getFileSize(const eServiceReference &ref)
{
	return 0;
}

eServiceHDMI::eServiceHDMI(eServiceReference ref)
 : m_ref(ref), m_decoder_index(0)
{

}

eServiceHDMI::~eServiceHDMI()
{
}

DEFINE_REF(eServiceHDMI);

RESULT eServiceHDMI::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceHDMI::start()
{
	m_decoder = new eTSMPEGDecoder(NULL, m_decoder_index);
	m_decoder->setVideoPID(1, 0);
	m_decoder->setAudioPID(1, 0);
	m_decoder->play();
	m_event(this, evStart);
	return 0;
}

RESULT eServiceHDMI::stop()
{
	m_decoder = NULL;
	m_event(this, evStopped);
	return 0;
}

RESULT eServiceHDMI::setTarget(int target)
{
	m_decoder_index = target;
	return 0;
}

RESULT eServiceHDMI::info(ePtr<iServiceInformation> &i)
{
	i = this;
	return 0;
}

RESULT eServiceHDMI::getName(std::string &name)
{
	if (m_ref.name.length())
	{
		name = m_ref.name;
	}
	else
	{
		name = "HDMI IN";
	}
	return 0;
}

int eServiceHDMI::getInfo(int w)
{
	return resNA;
}

std::string eServiceHDMI::getInfoString(int w)
{
	return "";
}

ePtr<iServiceInfoContainer> eServiceHDMI::getInfoObject(int w)
{
	return NULL;
}

eAutoInitPtr<eServiceFactoryHDMI> init_eServiceFactoryHDMI(eAutoInitNumbers::service + 1, "eServiceFactoryHDMI");
