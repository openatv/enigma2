#include <stdio.h>
#include <libsig_comp.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>

#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/isection.h>
#include <lib/dvb/esection.h>
#include <lib/dvb_si/pmt.h>
#include <lib/dvb/specs.h>
#include <unistd.h>

class eMain: public eApplication, public Object
{
	ePtr<eDVBResourceManager> m_mgr;
	ePtr<iDVBChannel> m_channel;
	ePtr<iDVBDemux> m_demux;
	eAUTable<eTable<ProgramMapTable> > m_table;
	
	ePtr<eDVBDB> m_dvbdb;
	
	ePtr<eConnection> m_state_change_connection;
	int m_last_channel_state;
public:
	eMain()
	{
		eDebug("mich gibts nu!");
		
		m_mgr = new eDVBResourceManager();
		
		m_dvbdb = new eDVBDB();
		m_mgr->setChannelList(m_dvbdb);
		
		eDVBChannelID chid(1,2,3);
		
		eDVBFrontendParametersSatellite fesat;
		
		fesat.frequency = 12070000;
		fesat.symbol_rate = 27500000;
		fesat.polarisation = eDVBFrontendParametersSatellite::Polarisation::Horizontal;
		fesat.fec = eDVBFrontendParametersSatellite::FEC::f3_4;
		fesat.inversion = eDVBFrontendParametersSatellite::Inversion::Off;
		fesat.orbital_position = 192;

		eDVBFrontendParameters *fe = new eDVBFrontendParameters();
		
		fe->setDVBS(fesat);
		
		m_dvbdb->addChannelToList(chid, fe);
		
		if (m_mgr->allocateChannel(chid, m_channel))
			eDebug("shit it failed!");
		
		if (m_channel)
		{
			m_channel->connectStateChange(slot(*this, &eMain::channelStateChanged), m_state_change_connection);
			channelStateChanged(m_channel);
		}
	}
	
	void channelStateChanged(iDVBChannel *channel)
	{
		int state;
		channel->getState(state);
		eDebug("channel state is now %d", state);
		
		if ((m_last_channel_state != iDVBChannel::state_ok)
			 && (state == iDVBChannel::state_ok) && (!m_demux))
		{
			eDebug("we'll start tuning!");
			if (m_channel)
				if (m_channel->getDemux(m_demux))
					eDebug("shit it failed.. again.");
		
			if (m_demux)
			{
				CONNECT(m_table.tableReady, eMain::tableReady);
				m_table.begin(this, eDVBPMTSpec(0x20, 0x33f6), m_demux);
			}
		}
		
		m_last_channel_state = state;
	}
	
	void tableReady(int)
	{
		ePtr<eTable<ProgramMapTable> > ptr;
		if (!m_table.getCurrent(ptr))
		{
			ProgramMapTableConstIterator i;
			for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
			{
				const ProgramMapTable &pmt = **i;
				eDebug("pcr pid: %x", pmt.getPcrPid());
			}
			eDebug("program map ...");
			quit(0);
		}
		eDebug("table ready.");
	}
	
	~eMain()
	{
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
