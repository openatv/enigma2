#include <lib/nav/core.h>
#include <lib/base/eerror.h>
#include <lib/python/python.h>

eNavigation* eNavigation::instance;

void eNavigation::serviceEvent(iPlayableService* service, int event)
{
	if (m_runningService && service != m_runningService)
	{
		eDebug("nav: event %d for other service", event);
		return;
	}
	m_event(event);
}

void eNavigation::recordEvent(iRecordableService* service, int event)
{
	if (m_recordings.find(service) == m_recordings.end())
	{
		eDebug("nav: event for non registered recording service");
		return;
	}
	m_record_event(service, event);
}

RESULT eNavigation::playService(const eServiceReference &service)
{
	stopService();

	ASSERT(m_servicehandler);
	RESULT res = m_servicehandler->play(service, m_runningService);
	if (m_runningService)
	{
		m_runningService->setTarget(m_decoder);
		m_runningService->connectEvent(slot(*this, &eNavigation::serviceEvent), m_service_event_conn);
		res = m_runningService->start();
	}
	return res;
}

RESULT eNavigation::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(event));
	return 0;
}

RESULT eNavigation::connectRecordEvent(const Slot2<void,ePtr<iRecordableService>,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_record_event.connect(event));
	return 0;
}

RESULT eNavigation::getCurrentService(ePtr<iPlayableService> &service)
{
	service = m_runningService;
	return 0;
}

RESULT eNavigation::stopService(void)
{
		/* check if there is a running service... */
	if (!m_runningService)
		return 1;

	ePtr<iPlayableService> tmp = m_runningService;
	m_runningService=0;
	tmp->stop();

	/* send stop event */
	m_event(iPlayableService::evEnd);

		/* kill service. */
	m_service_event_conn = 0;
	return 0;
}

RESULT eNavigation::recordService(const eServiceReference &ref, ePtr<iRecordableService> &service, bool simulate)
{
	ASSERT(m_servicehandler);
	RESULT res = m_servicehandler->record(ref, service);
	if (res)
	{
		eDebug("record: %d", res);
		service = 0;
	}
	else
	{
		if (simulate)
			m_simulate_recordings.insert(service);
		else
		{
			ePtr<eConnection> conn;
			service->connectEvent(slot(*this, &eNavigation::recordEvent), conn);
			m_recordings[service]=conn;
			m_recordings_services[service]=ref;
		}
	}
	return res;
}

RESULT eNavigation::stopRecordService(ePtr<iRecordableService> &service)
{
	service->stop();
	std::set<ePtr<iRecordableService> >::iterator it =
		m_simulate_recordings.find(service);
	if (it != m_simulate_recordings.end())
	{
		m_simulate_recordings.erase(it);
		return 0;
	}
	else
	{
		std::map<ePtr<iRecordableService>, ePtr<eConnection> >::iterator it =
			m_recordings.find(service);
		if (it != m_recordings.end())
		{
			m_recordings.erase(it);
			/* send stop event */
			m_record_event(service, iRecordableService::evEnd);
			std::map<ePtr<iRecordableService>, eServiceReference >::iterator it =
				m_recordings_services.find(service);
			if (it != m_recordings_services.end())
			{
				m_recordings_services.erase(it);
			}
			return 0;
		}
	}

	eDebug("try to stop non running recording!!");  // this should not happen
	return -1;
}

void eNavigation::getRecordings(std::vector<ePtr<iRecordableService> > &recordings, bool simulate)
{
	if (simulate)
		for (std::set<ePtr<iRecordableService> >::iterator it(m_simulate_recordings.begin()); it != m_simulate_recordings.end(); ++it)
			recordings.push_back(*it);
	else
		for (std::map<ePtr<iRecordableService>, ePtr<eConnection> >::iterator it(m_recordings.begin()); it != m_recordings.end(); ++it)
			recordings.push_back(it->first);
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

eNavigation::eNavigation(iServiceHandler *serviceHandler, int decoder)
{
	ASSERT(serviceHandler);
	m_servicehandler = serviceHandler;
	m_decoder = decoder;
	instance = this;
}

eNavigation::~eNavigation()
{
	stopService();
	instance=NULL;
}

DEFINE_REF(eNavigation);
