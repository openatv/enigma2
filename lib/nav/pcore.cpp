#include <lib/nav/pcore.h>
#include <lib/service/service.h>
#include <lib/service/event.h>
#include <lib/base/eerror.h>

DEFINE_REF(pNavigation);

pNavigation::pNavigation()
{
	ePtr<eServiceCenter> service_center;
	eServiceCenter::getInstance(service_center);

	assert(service_center);
	m_core = new eNavigation(service_center);
	
	m_core->connectEvent(slot(*this, &pNavigation::navEvent), m_nav_event_connection);
}

RESULT pNavigation::playService(const eServiceReference &service)
{
	return m_core->playService(service);
}

RESULT pNavigation::recordService(const eServiceReference &ref, ePtr<iRecordableService> &service)
{
	return m_core->recordService(ref, service);
}

RESULT pNavigation::enqueueService(const eServiceReference &service)
{
	return m_core->enqueueService(service);
}

RESULT pNavigation::getCurrentService(ePtr<iPlayableService> &service)
{
	return m_core->getCurrentService(service);
}

RESULT pNavigation::getPlaylist(ePtr<ePlaylist> &playlist)
{
	return m_core->getPlaylist(playlist);
}

RESULT pNavigation::pause(int p)
{
	return m_core->pause(p);
}

void pNavigation::navEvent(eNavigation *nav, int event)
{
		/* just relay the events here. */
	switch (event)
	{
	case eNavigation::evStopService:
		m_event(evStopService);
		break;
	case eNavigation::evNewService:
		m_event(evNewService);
		break;
	case eNavigation::evPlayFailed:
		m_event(evPlayFailed);
		break;
	case eNavigation::evPlaylistDone:
		m_event(evPlaylistDone);
		break;
	case eNavigation::evUpdatedEventInfo:
		m_event(evUpdatedEventInfo);
		break;
	}
}
