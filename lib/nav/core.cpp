#include <lib/nav/core.h>

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
			/* our running main service stopped. */
		if (!m_playlist.empty())
			m_playlist.erase(m_playlist.begin());
		if (!m_playlist.empty())
		{
			RESULT res;
			res = playService(m_playlist.front());
			if (res)
				m_event(this, evPlayFailed);
		} else
			m_event(this, evPlaylistDone);
		break;
	case iPlayableService::evStart:
		m_event(this, evNewService);
		break;
	default:
		break;
	}
}

RESULT eNavigation::playService(const eServiceReference &service)
{
	RESULT res = m_servicehandler->play(service, m_runningService);
	if (m_runningService)
	{
		m_runningService->connectEvent(slot(*this, &eNavigation::serviceEvent), m_service_event_conn);
		res = m_runningService->start();
	}
	return res;
}

RESULT eNavigation::enqueueService(const eServiceReference &service)
{
	int doplay = m_playlist.empty();
	m_playlist.push_back(service);
	if (doplay)
		return playService(m_playlist.front());
	return 0;
}

RESULT eNavigation::connectEvent(const Slot2<void,eNavigation*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(m_event.connect(event));
	return 0;
}

RESULT eNavigation::getCurrentService(ePtr<iPlayableService> &service)
{
	service = m_runningService;
	return 0;
}

RESULT eNavigation::pause(int dop)
{
	if (!m_runningService)
		return -1;
	ePtr<iPauseableService> p;
	if (m_runningService->getIPausableService(p))
		return -2;
	if (dop)
		return p->pause();
	else
		return p->unpause();
}

eNavigation::eNavigation(iServiceHandler *serviceHandler)
{
	m_servicehandler = serviceHandler;
}

eNavigation::~eNavigation()
{
}

DEFINE_REF(eNavigation);
