#include <lib/nav/pcore.h>
#include <lib/service/service.h>

DEFINE_REF(pNavigation);

pNavigation::pNavigation()
{
	ePtr<eServiceCenter> service_center;
	eServiceCenter::getInstance(service_center);

	assert(service_center);
	m_core = new eNavigation(service_center);
}

RESULT pNavigation::playService(const eServiceReference &service)
{
	return m_core->playService(service);
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
