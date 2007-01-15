#include <lib/dvb/dvbtime.h>
#include <lib/dvb/dvb.h>

#include <sys/ioctl.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

// defines for DM7000 / DM7020
#define FP_IOCTL_SET_RTC         0x101
#define FP_IOCTL_GET_RTC         0x102

static time_t prev_time;

void setRTC(time_t time)
{
	int fd = open("/dev/dbox/fp0", O_RDWR);
	if ( fd >= 0 )
	{
		if ( ::ioctl(fd, FP_IOCTL_SET_RTC, (void*)&time ) < 0 )
			eDebug("FP_IOCTL_SET_RTC failed(%m)");
		else
			prev_time = time;
		close(fd);
	}
}

time_t getRTC()
{
	time_t rtc_time=0;
	int fd = open("/dev/dbox/fp0", O_RDWR);
	if ( fd >= 0 )
	{
		if ( ::ioctl(fd, FP_IOCTL_GET_RTC, (void*)&rtc_time ) < 0 )
			eDebug("FP_IOCTL_GET_RTC failed(%m)");
		close(fd);
	}
	return rtc_time != prev_time ? rtc_time : 0;
}

time_t parseDVBtime(__u8 t1, __u8 t2, __u8 t3, __u8 t4, __u8 t5)
{
	tm t;
	t.tm_sec=fromBCD(t5);
	t.tm_min=fromBCD(t4);
	t.tm_hour=fromBCD(t3);
	int mjd=(t1<<8)|t2;
	int k;

	t.tm_year = (int) ((mjd - 15078.2) / 365.25);
	t.tm_mon = (int) ((mjd - 14956.1 - (int)(t.tm_year * 365.25)) / 30.6001);
	t.tm_mday = (int) (mjd - 14956 - (int)(t.tm_year * 365.25) - (int)(t.tm_mon * 30.6001));
	k = (t.tm_mon == 14 || t.tm_mon == 15) ? 1 : 0;
	t.tm_year = t.tm_year + k;
	t.tm_mon = t.tm_mon - 1 - k * 12;
	t.tm_mon--;

	t.tm_isdst =  0;
	t.tm_gmtoff = 0;

	return timegm(&t);
}

TDT::TDT(eDVBChannel *chan, int update_count)
	:chan(chan), update_count(update_count)
{
	CONNECT(tableReady, TDT::ready);
	CONNECT(m_interval_timer.timeout, TDT::start);
	if (chan)
		chan->getDemux(demux, 0);
}

void TDT::ready(int error)
{
	eDVBLocalTimeHandler::getInstance()->updateTime(error, chan, ++update_count);
}

int TDT::createTable(unsigned int nr, const __u8 *data, unsigned int max)
{
	if ( data && data[0] == 0x70 || data[0] == 0x73 )
	{
		int length = ((data[1] & 0x0F) << 8) | data[2];
		if ( length >= 5 )
		{
			time_t tptime = parseDVBtime(data[3], data[4], data[5], data[6], data[7]);
			if (tptime && tptime != -1)
				eDVBLocalTimeHandler::getInstance()->updateTime(tptime, chan, update_count);
			error=0;
			return 1;
		}
	}
	return 0;
}

void TDT::start()
{
	if ( chan )
	{
		eDVBTableSpec spec;
		spec.pid = TimeAndDateSection::PID;
		spec.tid = TimeAndDateSection::TID;
		spec.tid_mask = 0xFC;
		spec.timeout = TimeAndDateSection::TIMEOUT;
		spec.flags= eDVBTableSpec::tfAnyVersion |
					eDVBTableSpec::tfHaveTID |
					eDVBTableSpec::tfHaveTIDMask |
					eDVBTableSpec::tfHaveTimeout;
		if ( demux )
			eGTable::start( demux, spec );
	}
}

void TDT::startTimer( int interval )
{
	m_interval_timer.start(interval, true);
}

eDVBLocalTimeHandler *eDVBLocalTimeHandler::instance;
DEFINE_REF(eDVBLocalTimeHandler);

eDVBLocalTimeHandler::eDVBLocalTimeHandler()
	:m_time_ready(false), m_time_difference(0)
{
	if ( !instance )
		instance=this;
	ePtr<eDVBResourceManager> res_mgr;
	eDVBResourceManager::getInstance(res_mgr);
	if (!res_mgr)
		eDebug("[eDVBLocalTimerHandler] no resource manager !!!!!!!");
	else
	{
		res_mgr->connectChannelAdded(slot(*this,&eDVBLocalTimeHandler::DVBChannelAdded), m_chanAddedConn);
		time_t now = time(0);
		if ( now < 1072224000 ) // 01.01.2004
			eDebug("RTC not ready... wait for transponder time");
		else // inform all who's waiting for valid system time..
		{
			eDebug("Use valid Linux Time :) (RTC?)");
			m_time_ready = true;
			/*emit*/ m_timeUpdated();
		}
	}
}

eDVBLocalTimeHandler::~eDVBLocalTimeHandler()
{
	instance=0;
	for (std::map<iDVBChannel*, channel_data>::iterator it=m_knownChannels.begin(); it != m_knownChannels.end(); ++it)
		delete it->second.tdt;
}

void eDVBLocalTimeHandler::readTimeOffsetData( const char* filename )
{
	m_timeOffsetMap.clear();
	FILE *f=fopen(filename, "r");
	if (!f)
		return;
	char line[256];
	fgets(line, 256, f);
	while (true)
	{
		if (!fgets( line, 256, f ))
			break;
		if (strstr(line, "Transponder UTC Time Offsets\n"))
			continue;
		int dvbnamespace,tsid,onid,offs;
		if ( sscanf( line, "%08x,%04x,%04x:%d\n",&dvbnamespace,&tsid,&onid,&offs ) == 4 )
			m_timeOffsetMap[eDVBChannelID(dvbnamespace,tsid,onid)]=offs;
	}
	fclose(f);
}

void eDVBLocalTimeHandler::writeTimeOffsetData( const char* filename )
{
	FILE *f=fopen(filename, "w+");
	if ( f )
	{
		fprintf(f, "Transponder UTC Time Offsets\n");
		for ( std::map<eDVBChannelID,int>::iterator it ( m_timeOffsetMap.begin() ); it != m_timeOffsetMap.end(); ++it )
			fprintf(f, "%08x,%04x,%04x:%d\n",
				it->first.dvbnamespace.get(),
				it->first.transport_stream_id.get(), it->first.original_network_id.get(), it->second );
		fclose(f);
	}
}

void eDVBLocalTimeHandler::updateTime( time_t tp_time, eDVBChannel *chan, int update_count )
{
	bool restart_tdt = false;
	if (!tp_time)
		restart_tdt = true;
	else if (tp_time == -1)
	{
		restart_tdt = true;
		/*if ( eSystemInfo::getInstance()->getHwType() == eSystemInfo::DM7020 ||
		( eSystemInfo::getInstance()->getHwType() == eSystemInfo::DM7000
			&& eSystemInfo::getInstance()->hasStandbyWakeupTimer() ) )     TODO !!!!!!! */
		{
			eDebug("[eDVBLocalTimerHandler] no transponder tuned... or no TDT/TOT avail .. try to use RTC :)");
			time_t rtc_time = getRTC();
			if ( rtc_time ) // RTC Ready?
			{
				tm now;
				localtime_r(&rtc_time, &now);
				eDebug("[eDVBLocalTimerHandler] RTC time is %02d:%02d:%02d",
					now.tm_hour,
					now.tm_min,
					now.tm_sec);
				time_t linuxTime=time(0);
				time_t nowTime=linuxTime+m_time_difference;
				localtime_r(&nowTime, &now);
				eDebug("[eDVBLocalTimerHandler] Receiver time is %02d:%02d:%02d",
					now.tm_hour,
					now.tm_min,
					now.tm_sec);
				m_time_difference = rtc_time - linuxTime;
				eDebug("[eDVBLocalTimerHandler] RTC to Receiver time difference is %ld seconds", nowTime - rtc_time );
				if ( abs(m_time_difference) > 59 )
				{
					eDebug("[eDVBLocalTimerHandler] set Linux Time to RTC Time");
					timeval tnow;
					gettimeofday(&tnow,0);
					tnow.tv_sec=rtc_time;
					settimeofday(&tnow,0);
					eMainloop::addTimeOffset(m_time_difference);
					m_time_difference=0;
				}
				else if ( !m_time_difference )
					eDebug("[eDVBLocalTimerHandler] no change needed");
				else
					eDebug("[eDVBLocalTimerHandler] set to RTC time");
				/*emit*/ m_timeUpdated();
			}
			else
				eDebug("[eDVBLocalTimerHandler] shit RTC not ready :(");
		}
	}
	else
	{
		std::map< eDVBChannelID, int >::iterator it( m_timeOffsetMap.find( chan->getChannelID() ) );

 // current linux time
		time_t linuxTime = time(0);

 // current enigma time
		time_t nowTime=linuxTime+m_time_difference;

	// difference between current enigma time and transponder time
		int enigma_diff = tp_time-nowTime;

		int new_diff=0;

		bool updated = m_time_ready;

		if ( m_time_ready )  // ref time ready?
		{
			// difference between reference time (current enigma time)
			// and the transponder time
			eDebug("[eDVBLocalTimerHandler] diff is %d", enigma_diff);
			if ( abs(enigma_diff) < 120 )
			{
				eDebug("[eDVBLocalTimerHandler] diff < 120 .. use Transponder Time");
				m_timeOffsetMap[chan->getChannelID()] = 0;
				new_diff = enigma_diff;
			}
			else if ( it != m_timeOffsetMap.end() ) // correction saved?
			{
				eDebug("[eDVBLocalTimerHandler] we have correction %d", it->second);
				time_t CorrectedTpTime = tp_time+it->second;
				int ddiff = CorrectedTpTime-nowTime;
				eDebug("[eDVBLocalTimerHandler] diff after add correction is %d", ddiff);
				if ( abs(it->second) < 300 ) // stored correction < 5 min
				{
					eDebug("[eDVBLocalTimerHandler] use stored correction(<5 min)");
					new_diff = ddiff;
				}
				else if ( /*eSystemInfo::getInstance()->getHwType() == eSystemInfo::DM7020 &&  TODO !!!*/
						getRTC() )
				{
					time_t rtc=getRTC();
					m_timeOffsetMap[chan->getChannelID()] = rtc-tp_time;
					new_diff = rtc-nowTime;  // set enigma time to rtc
					eDebug("[eDVBLocalTimerHandler] update stored correction to %ld (calced against RTC time)", rtc-tp_time );
				}
				else if ( abs(ddiff) <= 120 )
				{
// with stored correction calced time difference is lower 2 min
// this don't help when a transponder have a clock running to slow or to fast
// then its better to have a DM7020 with always running RTC
					eDebug("[eDVBLocalTimerHandler] use stored correction(corr < 2 min)");
					new_diff = ddiff;
				}
				else  // big change in calced correction.. hold current time and update correction
				{
					eDebug("[eDVBLocalTimerHandler] update stored correction to %d", -enigma_diff);
					m_timeOffsetMap[chan->getChannelID()] = -enigma_diff;
				}
			}
			else
			{
				eDebug("[eDVBLocalTimerHandler] no correction found... store calced correction(%d)",-enigma_diff);
				m_timeOffsetMap[chan->getChannelID()] = -enigma_diff;
			}
		}
		else  // no time setted yet
		{
			if ( it != m_timeOffsetMap.end() )
			{
				enigma_diff += it->second;
				eDebug("[eDVBLocalTimerHandler] we have correction (%d)... use", it->second );
			}
			else
				eDebug("[eDVBLocalTimerHandler] dont have correction.. set Transponder Diff");
			new_diff=enigma_diff;
			m_time_ready=true;
		}

		time_t t = nowTime+new_diff;
		m_last_tp_time_difference=tp_time-t;

		if (!new_diff &&
			updated) // overrride this check on first received TDT
		{
			eDebug("[eDVBLocalTimerHandler] not changed");
			return;
		}

		tm now;
		localtime_r(&t, &now);
		eDebug("[eDVBLocalTimerHandler] time update to %02d:%02d:%02d",
			now.tm_hour,
			now.tm_min,
			now.tm_sec);

		m_time_difference = t - linuxTime;   // calc our new linux_time -> enigma_time correction
		eDebug("[eDVBLocalTimerHandler] m_time_difference is %d", m_time_difference );

//		if ( eSystemInfo::getInstance()->getHwType() == eSystemInfo::DM7020 )  TODO !!
		if ( !update_count )
		{
			// set rtc to calced transponder time when the first tdt is received on this
			// transponder
			setRTC(t);
			eDebug("[eDVBLocalTimerHandler] update RTC");
		}
		else
			eDebug("[eDVBLocalTimerHandler] don't update RTC");

		if ( abs(m_time_difference) > 59 )
		{
			eDebug("[eDVBLocalTimerHandler] set Linux Time");
			timeval tnow;
			gettimeofday(&tnow,0);
			tnow.tv_sec=t;
			settimeofday(&tnow,0);
			eMainloop::addTimeOffset(m_time_difference);
			m_time_difference=0;
		}

 		 /*emit*/ m_timeUpdated();
	}

	if ( restart_tdt )
	{
		std::map<iDVBChannel*, channel_data>::iterator it =
			m_knownChannels.find(chan);
		if ( it != m_knownChannels.end() )
		{
			TDT *prev_tdt = it->second.tdt;
			it->second.tdt = new TDT(chan, prev_tdt->getUpdateCount());
			it->second.tdt->startTimer(60*60*1000);  // restart TDT for this transponder in 60min
			delete prev_tdt;
		}
	}
}

void eDVBLocalTimeHandler::DVBChannelAdded(eDVBChannel *chan)
{
	if ( chan )
	{
//		eDebug("[eDVBLocalTimerHandler] add channel %p", chan);
		std::pair<std::map<iDVBChannel*, channel_data>::iterator, bool> tmp =
			m_knownChannels.insert( std::pair<iDVBChannel*, channel_data>(chan, channel_data()) );
		tmp.first->second.tdt = NULL;
		tmp.first->second.channel = chan;
		tmp.first->second.m_prevChannelState = -1;
		chan->connectStateChange(slot(*this, &eDVBLocalTimeHandler::DVBChannelStateChanged), tmp.first->second.m_stateChangedConn);
	}
}

void eDVBLocalTimeHandler::DVBChannelStateChanged(iDVBChannel *chan)
{
	std::map<iDVBChannel*, channel_data>::iterator it =
		m_knownChannels.find(chan);
	if ( it != m_knownChannels.end() )
	{
		int state=0;
		chan->getState(state);
		if ( state != it->second.m_prevChannelState )
		{
			switch (state)
			{
				case iDVBChannel::state_ok:
					eDebug("[eDVBLocalTimerHandler] channel %p running", chan);
					it->second.tdt = new TDT(it->second.channel);
					it->second.tdt->start();
					break;
				case iDVBChannel::state_release:
					eDebug("[eDVBLocalTimerHandler] remove channel %p", chan);
					delete it->second.tdt;
					m_knownChannels.erase(it);
					break;
				default: // ignore all other events
					return;
			}
			it->second.m_prevChannelState = state;
		}
	}
}
