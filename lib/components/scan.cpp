#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/components/scan.h>
#include <lib/base/eerror.h>
#include <lib/dvb/scan.h>

DEFINE_REF(eComponentScan);

void eComponentScan::scanEvent(int evt)
{
	eDebug("scan event %d!", evt);
	
	if (evt == eDVBScan::evtFinish)
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
			eDebug("scan done!");
		}
	}
	
	if (evt == eDVBScan::evtFail)
	{
		eDebug("scan failed.");
		m_failed = 1;
		m_done = 1;
	}
	
	statusChanged();
}

eComponentScan::eComponentScan(): m_done(-1), m_failed(0)
{
}

eComponentScan::~eComponentScan()
{
}

int eComponentScan::start()
{
	if (m_done != -1)
		return -1;
	
	m_done = 0;
	ePtr<eDVBResourceManager> mgr;
	
	eDVBResourceManager::getInstance(mgr);

	eDVBFrontendParameters *fe = new eDVBFrontendParameters();
#if 1
	eDVBFrontendParametersSatellite fesat;
		
	fesat.frequency = 11817000; // 12070000;
	fesat.symbol_rate = 27500000;
	fesat.polarisation = eDVBFrontendParametersSatellite::Polarisation::Vertical;
	fesat.fec = eDVBFrontendParametersSatellite::FEC::f3_4;
	fesat.inversion = eDVBFrontendParametersSatellite::Inversion::Off;
	fesat.orbital_position = 192;

	
	fe->setDVBS(fesat);

#else
	eDVBFrontendParametersTerrestrial fet;
	fet.frequency = 626000000;
	fet.inversion = eDVBFrontendParametersTerrestrial::Inversion::Unknown;
	fet.bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth::Bw8MHz;
	fet.code_rate_HP = fet.code_rate_LP = eDVBFrontendParametersTerrestrial::FEC::fAuto;
	fet.modulation = eDVBFrontendParametersTerrestrial::Modulation::QAM16;
	fet.transmission_mode = eDVBFrontendParametersTerrestrial::TransmissionMode::TM8k;
	fet.guard_interval = eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_32;
	fet.hierarchy = eDVBFrontendParametersTerrestrial::Hierarchy::HNone;
	fe->setDVBT(fet);
#endif
	ePtr<iDVBChannel> channel;

	if (mgr->allocateRawChannel(channel))
	{
		eDebug("scan: allocating raw channel failed!");
		return -1;
	}

	std::list<ePtr<iDVBFrontendParameters> > list;
		
	list.push_back(fe);
	
	m_scan = new eDVBScan(channel);
	m_scan->connectEvent(slot(*this, &eComponentScan::scanEvent), m_scan_event_connection);
	m_scan->start(list);
	
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
