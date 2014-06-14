#include <stdio.h>
#include <libsig_comp.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/isection.h>
#include <lib/dvb/esection.h>
#include <dvbsi++/program_map_section.h>
#include <lib/dvb/scan.h>
#include <unistd.h>

class eMain: public eApplication, public Object
{
	eInit init;

	eDVBScan *m_scan;

	ePtr<eDVBResourceManager> m_mgr;
	ePtr<iDVBChannel> m_channel;
	ePtr<eDVBDB> m_dvbdb;

	void scanEvent(int evt)
	{
		eDebug("scan event %d!", evt);
		if (evt == eDVBScan::evtFinish)
		{
			m_scan->insertInto(m_dvbdb);
			quit(0);
		}
	}
	ePtr<eConnection> m_scan_event_connection;
public:
	eMain()
	{
		m_dvbdb = new eDVBDB();
		m_mgr = new eDVBResourceManager();

		eDVBFrontendParametersSatellite fesat;

		fesat.frequency = 11817000; // 12070000;
		fesat.symbol_rate = 27500000;
		fesat.polarisation = eDVBFrontendParametersSatellite::Polarisation_Vertical;
		fesat.fec = eDVBFrontendParametersSatellite::FEC_3_4;
		fesat.inversion = eDVBFrontendParametersSatellite::Inversion_Off;
		fesat.orbital_position = 192;

		eDVBFrontendParameters *fe = new eDVBFrontendParameters();

		fe->setDVBS(fesat);

		if (m_mgr->allocateRawChannel(m_channel))
			eDebug("shit it failed!");

//		init.setRunlevel(eAutoInitNumbers::main);
		eDebug("starting scan...");

		std::list<ePtr<iDVBFrontendParameters> > list;

		list.push_back(fe);

		m_scan = new eDVBScan(m_channel);
		m_scan->start(list);

		m_scan->connectEvent(slot(*this, &eMain::scanEvent), m_scan_event_connection);
	}

	~eMain()
	{
		delete m_scan;
		eDebug("... nicht mehr.");
	}
};

#ifdef OBJECT_DEBUG
int object_total_remaining;

void object_dump()
{
	printf("%d items left\n", object_total_remaining);
}
#endif

int main()
{
#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif
	eMain app;
	return app.exec();
}
