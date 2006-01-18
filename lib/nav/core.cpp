#include <lib/nav/core.h>
#include <lib/base/eerror.h>

void eNavigation::serviceEvent(iPlayableService* service, int event)
{
	if (service != m_runningService)
	{
		eDebug("nav: event for other service");
		return;
	}

	switch (event)
	{	
	case iPlayableService::evEnd:
//		m_event(this, ev);
		break;
	case iPlayableService::evStart:
		m_event(this, evNewService);
		break;
	case iPlayableService::evUpdatedEventInfo:
		m_event(this, evUpdatedEventInfo);
		break;
	case iPlayableService::evUpdatedInfo:
		m_event(this, evUpdatedInfo);
		break;
	case iPlayableService::evSeekableStatusChanged:
		m_event(this, evSeekableStatusChanged);
		break;
	default:
		break;
	}
}

RESULT eNavigation::playService(const eServiceReference &service)
{
	stopService();
	
	assert(m_servicehandler);
	RESULT res = m_servicehandler->play(service, m_runningService);
	if (m_runningService)
	{
		m_runningService->connectEvent(slot(*this, &eNavigation::serviceEvent), m_service_event_conn);
		res = m_runningService->start();
	}
	return res;
}

RESULT eNavigation::connectEvent(const Slot2<void,eNavigation*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(event));
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
			/* send stop event */
	m_event(this, evStopService);

		/* kill service. */
	m_runningService = 0;
	m_service_event_conn = 0;
	return 0;
}

RESULT eNavigation::recordService(const eServiceReference &ref, ePtr<iRecordableService> &service)
{
	assert(m_servicehandler);
	RESULT res = m_servicehandler->record(ref, service);
	eDebug("record: %d", res);
	if (res)
		service = 0;
	return res;
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

eNavigation::eNavigation(iServiceHandler *serviceHandler)
{
	assert(serviceHandler);
	m_servicehandler = serviceHandler;
}

eNavigation::~eNavigation()
{
}

DEFINE_REF(eNavigation);
