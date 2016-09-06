#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/components/scan.h>
#include <lib/base/eerror.h>
#include <lib/dvb/scan.h>

DEFINE_REF(eComponentScan);

void eComponentScan::scanEvent(int evt)
{
//	eDebug("scan event %d!", evt);

	switch(evt)
	{
		case eDVBScan::evtFinish:
		{
			m_done = 1;
			ePtr<iDVBChannelList> db;
			ePtr<eDVBResourceManager> res;

			int err;
			if ((err = eDVBResourceManager::getInstance(res)) != 0)
			{
				eDebug("no resource manager");
				m_failed = 2;
			} else if ((err = res->getChannelList(db)) != 0)
			{
				m_failed = 3;
				eDebug("no channel list");
			} else
			{
				m_scan->insertInto(db);
				db->flush();
				eDebug("scan done!");
			}
			break;
		}
		case eDVBScan::evtNewService:
			newService();
			return;
		case eDVBScan::evtFail:
			eDebug("scan failed.");
			m_failed = 1;
			m_done = 1;
			break;
		case eDVBScan::evtUpdate:
			break;
	}
	statusChanged();
	if (m_failed > 0)
		m_done = 1;
}

eComponentScan::eComponentScan(): m_done(-1), m_failed(0)
{
}

eComponentScan::~eComponentScan()
{
}

void eComponentScan::clear()
{
	m_initial.clear();
}

void eComponentScan::addInitial(const eDVBFrontendParametersSatellite &p)
{
	ePtr<eDVBFrontendParameters> parm = new eDVBFrontendParameters();
	parm->setDVBS(p);
	m_initial.push_back(parm);
}

void eComponentScan::addInitial(const eDVBFrontendParametersCable &p)
{
	ePtr<eDVBFrontendParameters> parm = new eDVBFrontendParameters();
	parm->setDVBC(p);
	m_initial.push_back(parm);
}

void eComponentScan::addInitial(const eDVBFrontendParametersTerrestrial &p)
{
	ePtr<eDVBFrontendParameters> parm = new eDVBFrontendParameters();
	parm->setDVBT(p);
	m_initial.push_back(parm);
}

void eComponentScan::addInitial(const eDVBFrontendParametersATSC &p)
{
	ePtr<eDVBFrontendParameters> parm = new eDVBFrontendParameters();
	parm->setATSC(p);
	m_initial.push_back(parm);
}

int eComponentScan::start(int feid, int flags, int networkid)
{
	if (m_initial.empty())
		return -2;

	if (m_done != -1)
		return -1;

	m_done = 0;
	ePtr<eDVBResourceManager> mgr;

	eDVBResourceManager::getInstance(mgr);

	eUsePtr<iDVBChannel> channel;

	if (mgr->allocateRawChannel(channel, feid))
	{
		eDebug("scan: allocating raw channel (on frontend %d) failed!", feid);
		return -1;
	}

	std::list<ePtr<iDVBFrontendParameters> > list;
	m_scan = new eDVBScan(channel);
	m_scan->connectEvent(slot(*this, &eComponentScan::scanEvent), m_scan_event_connection);

	if (!(flags & scanRemoveServices))
	{
		ePtr<iDVBChannelList> db;
		ePtr<eDVBResourceManager> res;
		int err;
		if ((err = eDVBResourceManager::getInstance(res)) != 0)
			eDebug("no resource manager");
		else if ((err = res->getChannelList(db)) != 0)
			eDebug("no channel list");
		else
		{
			if (m_initial.size() > 1)
			{
				ePtr<iDVBFrontendParameters> tp = m_initial.first();
				int type;
				if (tp && !tp->getSystem(type))
				{
					switch(type)
					{
						case iDVBFrontend::feSatellite:
						{
							eDVBFrontendParametersSatellite parm;
							tp->getDVBS(parm);
							db->removeFlags(eDVBService::dxNewFound, -1, -1, -1, parm.orbital_position);
							break;
						}
						case iDVBFrontend::feCable:
							db->removeFlags(eDVBService::dxNewFound, 0xFFFF0000, -1, -1, -1);
							break;
						case iDVBFrontend::feTerrestrial:
							db->removeFlags(eDVBService::dxNewFound, 0xEEEE0000, -1, -1, -1);
							break;
						case iDVBFrontend::feATSC:
							eDVBFrontendParametersATSC parm;
							tp->getATSC(parm);
							int ns = parm.system == eDVBFrontendParametersATSC::System_ATSC ? 0xEEEE0000 : 0xFFFF0000;
							db->removeFlags(eDVBService::dxNewFound, ns, -1, -1, -1);
							break;
					}
				}
			}
		}
	}
	m_scan->start(m_initial, flags, networkid);

	return 0;
}

int eComponentScan::getProgress()
{
	if (!m_scan)
		return 0;
	int done, total, services;
	m_scan->getStats(done, total, services);
	if (!total)
		return 0;
	return done * 100 / total;
}

int eComponentScan::getNumServices()
{
	if (!m_scan)
		return 0;
	int done, total, services;
	m_scan->getStats(done, total, services);
	return services;
}

int eComponentScan::isDone()
{
	return m_done;
}

int eComponentScan::getError()
{
	return m_failed;
}

void eComponentScan::getLastServiceName(std::string &string)
{
	if (!m_scan)
		return;
	m_scan->getLastServiceName(string);
}

void eComponentScan::getLastServiceRef(std::string &string)
{
	if (!m_scan)
		return;
	m_scan->getLastServiceRef(string);
}

RESULT eComponentScan::getFrontend(ePtr<iDVBFrontend> &fe)
{
	if (m_scan)
		return m_scan->getFrontend(fe);
	fe = 0;
	return -1;
}

RESULT eComponentScan::getCurrentTransponder(ePtr<iDVBFrontendParameters> &tp)
{
	if (m_scan)
		return m_scan->getCurrentTransponder(tp);
	tp = 0;
	return -1;
}

