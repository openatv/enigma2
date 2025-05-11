#include <lib/nav/core.h>
#include <lib/base/eerror.h>
#include <lib/python/python.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/fcc.h>

eNavigation *eNavigation::instance;

void eNavigation::serviceEvent(iPlayableService *service, int event)
{
	if (m_runningService && service != m_runningService)
	{
		eDebug("[eNavigation] event %d for other service", event);
		return;
	}
	m_event(event);
}

void eNavigation::recordEvent(iRecordableService *service, int event)
{
	if (m_recordings.find(service) == m_recordings.end())
	{
		eDebug("[eNavigation] event for non registered recording service");
		return;
	}
	m_record_event(service, event);
}

RESULT eNavigation::playService(const eServiceReference &service)
{
	RESULT res = -1;

#if defined(HAVE_FCC)
	if (!m_fccmgr || m_fccmgr->tryFCCService(service, m_runningService) == -1)
	{
		stopService();
		ASSERT(m_servicehandler);
		res = m_servicehandler->play(service, m_runningService);
	}
#else
	stopService();
	ASSERT(m_servicehandler);
	res = m_servicehandler->play(service, m_runningService);
#endif

	if (m_runningService)
	{
		m_runningService->setTarget(m_decoder);
		m_runningService->connectEvent(sigc::mem_fun(*this, &eNavigation::serviceEvent), m_service_event_conn);
		res = m_runningService->start();
	}
	m_runningServiceRef = service;
	return res;
}

RESULT eNavigation::setPiPService(const eServiceReference &service)
{
	m_runningPiPServiceRef = service;
	return 0;
}

RESULT eNavigation::connectEvent(const sigc::slot<void(int)> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(event));
	return 0;
}

RESULT eNavigation::connectRecordEvent(const sigc::slot<void(ePtr<iRecordableService>,int)> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_record_event.connect(event));
	return 0;
}

RESULT eNavigation::getCurrentService(ePtr<iPlayableService> &service)
{
	service = m_runningService;
	return 0;
}

RESULT eNavigation::getCurrentServiceReference(eServiceReference &service)
{
	service = m_runningServiceRef;
	return 0;
}

RESULT eNavigation::getCurrentPiPServiceReference(eServiceReference &service)
{
	service = m_runningPiPServiceRef;
	return 0;
}

RESULT eNavigation::stopService(void)
{
	/* check if there is a running service... */
	if (!m_runningService)
		return 1;

	ePtr<iPlayableService> tmp = m_runningService;
	m_runningService = 0;
	m_runningServiceRef = eServiceReference();
	tmp->stop();

	/* send stop event */
	m_event(iPlayableService::evEnd);

	/* kill service. */
	m_service_event_conn = 0;

#if defined(HAVE_FCC)
	m_fccmgr && m_fccmgr->cleanupFCCService();
#endif
	return 0;
}

RESULT eNavigation::clearPiPService(void)
{
	m_runningPiPServiceRef = eServiceReference();
	return 0;
}

RESULT eNavigation::recordService(const eServiceReference &ref, ePtr<iRecordableService> &service, bool simulate, pNavigation::RecordType type)
{
	ASSERT(m_servicehandler);
	RESULT res = m_servicehandler->record(ref, service);
	if (res)
	{
		eDebug("[eNavigation] record: %d", res);
		service = 0;
	}
	else
	{
		if (simulate)
			m_simulate_recordings.insert(service);
		else
		{
			ePtr<eConnection> conn;
			service->connectEvent(sigc::mem_fun(*this, &eNavigation::recordEvent), conn);
			m_recordings[service] = conn;
			m_recordings_services[service] = ref;
			m_recordings_types[service] = type;
		}
	}
	return res;
}

RESULT eNavigation::stopRecordService(ePtr<iRecordableService> &service)
{
	service->stop();
	std::set<ePtr<iRecordableService>>::iterator it =
		m_simulate_recordings.find(service);
	if (it != m_simulate_recordings.end())
	{
		m_simulate_recordings.erase(it);
		return 0;
	}
	else
	{
		std::map<ePtr<iRecordableService>, ePtr<eConnection>>::iterator it =
			m_recordings.find(service);
		if (it != m_recordings.end())
		{
			m_recordings.erase(it);
			/* send stop event */
			m_record_event(service, iRecordableService::evEnd);
			std::map<ePtr<iRecordableService>, eServiceReference>::iterator it_services =
				m_recordings_services.find(service);
			if (it_services != m_recordings_services.end())
			{
				m_recordings_services.erase(it_services);
			}
			std::map<ePtr<iRecordableService>, pNavigation::RecordType>::iterator it_types =
				m_recordings_types.find(service);
			if (it_types != m_recordings_types.end())
			{
				m_recordings_types.erase(it_types);
			}
			return 0;
		}
	}

	eDebug("[eNavigation] try to stop non running recording!!"); // this should not happen
	return -1;
}

void eNavigation::getRecordings(std::vector<ePtr<iRecordableService>> &recordings, bool simulate, pNavigation::RecordType type)
{
	if (simulate)
		for (std::set<ePtr<iRecordableService>>::iterator it(m_simulate_recordings.begin()); it != m_simulate_recordings.end(); ++it)
			recordings.push_back(*it);
	else
		for (std::map<ePtr<iRecordableService>, ePtr<eConnection>>::iterator it(m_recordings.begin()); it != m_recordings.end(); ++it)
		{
			if (m_recordings_types[it->first] & type)
			{
				recordings.push_back(it->first);
			}
		}
}

void eNavigation::getRecordingsServicesOnly(std::vector<eServiceReference> &services, pNavigation::RecordType type)
{
	for (std::map<ePtr<iRecordableService>, eServiceReference>::iterator it(m_recordings_services.begin()); it != m_recordings_services.end(); ++it)
	{
		if (m_recordings_types[it->first] & type)
		{
			services.push_back(it->second);
		}
	}
}

void eNavigation::getRecordingsTypesOnly(std::vector<pNavigation::RecordType> &returnedTypes, pNavigation::RecordType type)
{
	for (std::map<ePtr<iRecordableService>, pNavigation::RecordType>::iterator it(m_recordings_types.begin()); it != m_recordings_types.end(); ++it)
	{
		if (m_recordings_types[it->first] & type)
		{
			returnedTypes.push_back(it->second);
		}
	}
}

void eNavigation::getRecordingsSlotIDsOnly(std::vector<int> &slotids, pNavigation::RecordType type)
{
	for (std::map<ePtr<iRecordableService>, eServiceReference>::iterator it(m_recordings_services.begin()); it != m_recordings_services.end(); ++it)
	{
		if (m_recordings_types[it->first] & type)
		{
			ePtr<iFrontendInformation> fe_info;
			it->first->frontendInfo(fe_info);
			if (fe_info)
				slotids.push_back(fe_info->getFrontendInfo(iFrontendInformation_ENUMS::frontendNumber));
			else
				slotids.push_back(-1);
		}
	}
}

std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService *>> eNavigation::getRecordingsServices(pNavigation::RecordType type)
{
	std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService *>> m_recordings_services_filtered;

	for (std::map<ePtr<iRecordableService>, eServiceReference>::iterator it(m_recordings_services.begin()); it != m_recordings_services.end(); ++it)
	{
		if (m_recordings_types[it->first] & type)
		{
			m_recordings_services_filtered[it->first] = m_recordings_services[it->first];
		}
	}
	return m_recordings_services_filtered;
}

RESULT eNavigation::pause(int dop)
{
	if (!m_runningService)
		return -1;
	ePtr<iPauseableService> p;
	if (m_runningService->pause(p))
		return -2;
	if (dop)
		return p->pause();
	else
		return p->unpause();
}

void eNavigation::addStreamService(const std::string ref)
{
	std::vector<std::string>::iterator it = std::find(m_streamservices.begin(), m_streamservices.end(), ref);
	if (it == m_streamservices.end())
		m_streamservices.push_back(ref);
}

void eNavigation::removeStreamService(const std::string ref)
{
	std::vector<std::string>::iterator it = std::find(m_streamservices.begin(), m_streamservices.end(), ref);
	if (it != m_streamservices.end())
		m_streamservices.erase(it);
}

std::vector<std::string> eNavigation::getStreamServiceList()
{
	return m_streamservices;
}

eNavigation::eNavigation(iServiceHandler *serviceHandler, int decoder)
{
	ASSERT(serviceHandler);
	m_servicehandler = serviceHandler;
	m_decoder = decoder;
#if defined(HAVE_FCC)
	if (decoder == 0)
	{
		m_fccmgr = eFCCServiceManager::getInstance();
		// don't create eFCCServiceManager twice, last eNavigation for decoder 0 wins
		if (m_fccmgr)
		{
			m_fccmgr->setNav(this);
		}
		else
			m_fccmgr = new eFCCServiceManager(this);
	}
#endif
	instance = this;
}

eNavigation::~eNavigation()
{
	stopService();
	instance = NULL;
}

DEFINE_REF(eNavigation);
