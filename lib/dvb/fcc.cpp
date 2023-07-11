#include <lib/dvb/fcc.h>
#include <lib/nav/core.h>
#include <lib/base/nconfig.h>
#include <lib/base/eerror.h>
#include <lib/python/python.h>

//#define FCC_DEBUG

void FCCServiceChannels::addFCCService(const eServiceReference &service)
{
	eDVBChannelID fcc_chid;

	((const eServiceReferenceDVB&)service).getChannelID(fcc_chid);

	if (m_fcc_chids.find(fcc_chid) != m_fcc_chids.end())
		m_fcc_chids[fcc_chid] += 1;
	else
		m_fcc_chids[fcc_chid] = 1;
}

void FCCServiceChannels::removeFCCService(const eServiceReference &service)
{
	eDVBChannelID fcc_chid;
	((const eServiceReferenceDVB&)service).getChannelID(fcc_chid);

	if (m_fcc_chids.find(fcc_chid) != m_fcc_chids.end())
	{
		m_fcc_chids[fcc_chid] -= 1;

		if (m_fcc_chids[fcc_chid] == 0)
			m_fcc_chids.erase(fcc_chid);
	}
}

int FCCServiceChannels::getFCCChannelID(std::map<eDVBChannelID, int> &fcc_chids)
{
	if (!m_fcc_chids.size()) return -1;

	fcc_chids = m_fcc_chids;
	return 0;
}

eFCCServiceManager *eFCCServiceManager::m_instance = (eFCCServiceManager*)0;

eFCCServiceManager* eFCCServiceManager::getInstance()
{
	return m_instance;
}

eFCCServiceManager::eFCCServiceManager(eNavigation *navptr)
	:m_core(navptr), m_fcc_enable(false)
{
	if (!m_instance)
	{
		m_instance = this;
	}
}

eFCCServiceManager::~eFCCServiceManager()
{
	if (m_instance == this)
	{
		m_instance = 0;
	}
}

RESULT eFCCServiceManager::playFCCService(const eServiceReference &ref, ePtr<iPlayableService> &service)
{
	std::map< ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.begin();
	for (;it != m_FCCServices.end();++it)
	{
		ASSERT (ref != it->second.m_service_reference);
	}

	ASSERT(m_core->m_servicehandler);
	RESULT res = m_core->m_servicehandler->play(ref, service);
	if (res)
		service = 0;
	else
	{
		ePtr<eConnection> conn;
		service->connectEvent(sigc::mem_fun(*this, &eFCCServiceManager::FCCEvent), conn);

		FCCServiceElem elem = {ref, conn, fcc_state_preparing, false};
		m_FCCServices[service] = elem;

		res = service->start();
	}

	printFCCServices();

	return res;
}

void eFCCServiceManager::FCCEvent(iPlayableService* service, int event)
{
	std::map<ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.find(service);
	if (it == m_FCCServices.end())
	{
		eDebug("[eFCCServiceManager] Event for non registered FCC service");
		return;
	}

	switch (event)
	{
		case iPlayableService::evStart:
		{
			m_fccServiceChannels.addFCCService(it->second.m_service_reference);
			break;
		}
		case iPlayableService::evStopped:
		{
			m_fccServiceChannels.removeFCCService(it->second.m_service_reference);
			break;
		}
		case iPlayableService::evTuneFailed:
		case iPlayableService::evFccFailed:
		{
			eDebug("[eFCCServiceManager] FCCEvent [%s] set service to state failed.", it->second.m_service_reference.toString().c_str());
			it->second.m_state = fcc_state_failed;
			break;
		}
	}
	m_fcc_event(event);
}

RESULT eFCCServiceManager::cleanupFCCService()
{
	if (m_FCCServices.size())
	{
		std::map<ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.begin();
		for (;it != m_FCCServices.end();++it)
		{
			eDebug("[eFCCServiceManager] Stop FCC service sref : %s", it->second.m_service_reference.toString().c_str());
			it->first->stop();
		}

		m_FCCServices.clear();
	}
	return 0;
}

RESULT eFCCServiceManager::stopFCCService(const eServiceReference &sref)
{
	if (m_FCCServices.size())
	{
		std::map<ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.begin();
		for (; it != m_FCCServices.end();)
		{
			if (it->second.m_service_reference == sref)
			{
				eDebug("[eFCCServiceManager] Stop FCC service sref : %s", it->second.m_service_reference.toString().c_str());
				it->first->stop();
				m_FCCServices.erase(it++);
			}
			else
			{
				++it;
			}
		}
		printFCCServices();
	}
	return 0;
}

RESULT eFCCServiceManager::stopFCCService()
{
	if (m_FCCServices.size())
	{
		std::map<ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.begin();
		for (; it != m_FCCServices.end();)
		{
			if (it->second.m_state == fcc_state_failed)
			{
				eDebug("[eFCCServiceManager] Stop FCC service sref : %s", it->second.m_service_reference.toString().c_str());
				it->first->stop();
				m_FCCServices.erase(it++);
			}
			else
			{
				++it;
			}
		}

		printFCCServices();
	}
	return 0;
}

RESULT eFCCServiceManager::tryFCCService(const eServiceReference &sref, ePtr<iPlayableService> &service)
{
	if (!isEnable())
		return -1;

	ePtr<iPlayableService> new_service = 0;

	printFCCServices();

	int get_fcc_decoding = 0;

	/* stop previous decoding service */
	std::map< ePtr<iPlayableService>, FCCServiceElem >::iterator it;
	for (it = m_FCCServices.begin();it != m_FCCServices.end();++it)
	{
		if (it->second.m_state == fcc_state_decoding)
		{
			ASSERT(get_fcc_decoding == 0);
			get_fcc_decoding = 1;

			/* send end event */
			m_core->m_event(iPlayableService::evEnd);

			/* kill service and event */
			m_core->m_service_event_conn = 0;
			m_core->m_runningService = 0;

			if (it->second.m_useNormalDecode)
			{
				/* stop service */
				it->first->stop();
				m_FCCServices.erase(it++);
			}
			else
			{
				/* connect to fcc event */
				ePtr<eConnection> conn;
				it->first->connectEvent(sigc::mem_fun(*this, &eFCCServiceManager::FCCEvent), conn);
				it->second.m_service_event_conn = conn;
				it->second.m_state = fcc_state_preparing;

				/* switch to FCC prepare state */
				it->first->start();

				/* update FCCServiceChannels */
				m_fccServiceChannels.addFCCService(it->second.m_service_reference);
			}
			break;
		}
	}

	/* search new service */
	for (it = m_FCCServices.begin();it != m_FCCServices.end();++it)
	{
		if (it->second.m_service_reference == sref)
		{
			eDebug("[eFCCServiceManager] Use FCC service sref : %s", it->second.m_service_reference.toString().c_str());
			it->second.m_service_event_conn = 0; /* disconnect FCC event */
			it->second.m_state = fcc_state_decoding;
			new_service = it->first;
			m_fccServiceChannels.removeFCCService(it->second.m_service_reference);
			break;
		}
	}

	if (new_service)
	{
		service = new_service;
	}

	else /* If new service is not found in FCC service list, cleanup all FCC prepared services and get new FCC service. */
	{
		cleanupFCCService();
		m_core->stopService();
		if (eFCCServiceManager::checkAvailable(sref))
		{
			ASSERT(m_core->m_servicehandler);
			m_core->m_servicehandler->play(sref, service);

			if (service)
			{
				FCCServiceElem elem = {sref, 0, fcc_state_decoding, false};
				m_FCCServices[service] = elem;
				service->start(); // do FCC preparing
			}
		}
		else
		{
			return -1;
		}
	}

	printFCCServices();

	return 0;
}

PyObject *eFCCServiceManager::getFCCServiceList()
{
	ePyObject dest = PyDict_New();
	if (dest)
	{
		std::map< ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.begin();
		for (;it != m_FCCServices.end();++it)
		{
			ePyObject tplist = PyList_New(0);
			PyList_Append(tplist, PyLong_FromLong((long)it->second.m_state));
			PyList_Append(tplist, PyLong_FromLong((long)isLocked(it->first)));
			PyDict_SetItemString(dest, it->second.m_service_reference.toString().c_str(), tplist);
			Py_DECREF(tplist);
		}
	}

	else
		Py_RETURN_NONE;
	return dest;
}

int eFCCServiceManager::isLocked(ePtr<iPlayableService> service)
{
	ePtr<iFrontendInformation> ptr;
	service->frontendInfo(ptr);
	return ptr->getFrontendInfo(iFrontendInformation_ENUMS::lockState);
}

void eFCCServiceManager::printFCCServices()
{
#ifdef FCC_DEBUG
	eDebug("[eFCCServiceManager] printFCCServices [*] total size : %d", m_FCCServices.size());

	std::map< ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.begin();
	for (;it != m_FCCServices.end();++it)
	{
		int isLocked = isLocked(it->first);
		eDebug("[eFCCServiceManager] printFCCServices [*] sref : %s, state : %d, tune : %d, useNormalDecode : %d", it->second.m_service_reference.toString().c_str(), it->second.m_state, isLocked, it->second.m_useNormalDecode);
	}
#else
	;
#endif
}

int eFCCServiceManager::getFCCChannelID(std::map<eDVBChannelID, int> &fcc_chids)
{
	eFCCServiceManager *fcc_mng = eFCCServiceManager::getInstance();
	if (!fcc_mng) return -1;
	return fcc_mng->m_fccServiceChannels.getFCCChannelID(fcc_chids);
}

bool eFCCServiceManager::checkAvailable(const eServiceReference &ref)
{
	int serviceType = ref.getData(0);
	eFCCServiceManager *fcc_mng = eFCCServiceManager::getInstance();

	if ((ref.type == 1) && ref.path.empty() && (serviceType != 2) && (serviceType != 10) && fcc_mng) // no PVR, streaming, radio channel..
		return fcc_mng->isEnable();
	return false;
}

bool eFCCServiceManager::isStateDecoding(iPlayableService* service)
{
	std::map<ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.find(service);
	if (it != m_FCCServices.end())
	{
		return (it->second.m_state == fcc_state_decoding);
	}
	else
	{
		eDebug("[eFCCServiceManager] Non registered FCC service");
	}

	return false;
}

void eFCCServiceManager::setNormalDecoding(iPlayableService* service)
{
	std::map<ePtr<iPlayableService>, FCCServiceElem >::iterator it = m_FCCServices.find(service);
	if (it != m_FCCServices.end())
	{
		eDebug("[eFCCServiceManager] setNormalDecoding [%s] set to use normal decoding.", it->second.m_service_reference.toString().c_str());
		it->second.m_useNormalDecode = true;
	}
	else
	{
		eDebug("[eFCCServiceManager] Non registered FCC service");
	}
}

DEFINE_REF(eFCCServiceManager);

