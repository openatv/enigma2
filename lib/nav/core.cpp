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
		assert(m_playlist); /* we need to have a playlist */
		
		/* at first, kill the running service */
		stopService();
		
		/* our running main service stopped. identify what to do next. */
			
			/* unless the playlist current position is invalid (because there was */
			/* playlist, for example when the service was engaged with playService */
		if (m_playlist->m_current != m_playlist->end())
			++m_playlist->m_current;
			
			/* was the current service the last one? */
		if (m_playlist->m_current == m_playlist->end())
		{
			m_event(this, evPlaylistDone);
			break;
		}

			/* there is another service in the playlist. play it. */
		RESULT res;
		res = playService(*m_playlist->m_current);
		if (res)
			m_event(this, evPlayFailed);
		break;
	case iPlayableService::evStart:
		m_event(this, evNewService);
		break;
	case iPlayableService::evUpdatedEventInfo:
		m_event(this, evUpdatedEventInfo);
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

RESULT eNavigation::enqueueService(const eServiceReference &service)
{
	assert(m_playlist);
		/* check if we need to play after the service was enqueued. */
	int doplay = m_playlist->m_current == m_playlist->end();
	
		/* add the service to the playlist. the playlist's m_current */
		/* points either to a service before the last or 'doplay' is set. */
	m_playlist->push_back(service);

	if (doplay)
	{
		m_playlist->m_current = m_playlist->end();
		--m_playlist->m_current;
		return playService(*m_playlist->m_current);
	}
	return 0;
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

RESULT eNavigation::getPlaylist(ePtr<ePlaylist> &playlist)
{
	if (!m_playlist)
		return -1;
	playlist = m_playlist;
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
	m_playlist = new ePlaylist;

		/* start with no current selection */
	m_playlist->m_current = m_playlist->end();
}

eNavigation::~eNavigation()
{
}

DEFINE_REF(eNavigation);
