#include <lib/dvb/dvbtime.h>
#include <lib/dvb/dvb.h>
#include <lib/base/esimpleconfig.h>

#include <sys/ioctl.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

// Defines for DM7000 / DM7020.
#define FP_IOCTL_SET_RTC 0x101
#define FP_IOCTL_GET_RTC 0x102

#define TIME_UPDATE_INTERVAL (15 * 60 * 1000)

static time_t prev_time;

void setRTC(time_t time, bool debug)
{
	if (debug)
		eDebug("[eDVBLocalTimerHandler] Set RTC time.");
	FILE *f = fopen("/proc/stb/fp/rtc", "w");
	if (f)
	{
		if (fprintf(f, "%u", (unsigned int)time))
		{
#ifdef HAVE_NO_RTC
			prev_time = 0; // Sorry no RTC
#else
			prev_time = time;
#endif
		}
		else
			eDebug("[eDVBLocalTimeHandler] Write /proc/stb/fp/rtc failed: %m");
		fclose(f);
	}
	else
	{
		int fd = open("/dev/dbox/fp0", O_RDWR);
		if (fd >= 0)
		{
			if (::ioctl(fd, FP_IOCTL_SET_RTC, (void *)&time) < 0)
				eDebug("[eDVBLocalTimeHandler] FP_IOCTL_SET_RTC failed: %m");
			else
				prev_time = time;
			close(fd);
		}
	}
}

time_t getRTC()
{
	time_t rtc_time = 0;
	FILE *f = fopen("/proc/stb/fp/rtc", "r");
	if (f)
	{
		// Sanity check to detect corrupt atmel firmware.
		unsigned int tmp;
		if (fscanf(f, "%u", &tmp) != 1)
			eDebug("[eDVBLocalTimeHandler] Read /proc/stb/fp/rtc failed: %m");
		else
#ifdef HAVE_NO_RTC
			rtc_time = 0; // Sorry no RTC
#else
			rtc_time = tmp;
#endif
		fclose(f);
	}
	else
	{
		int fd = open("/dev/dbox/fp0", O_RDWR);
		if (fd >= 0)
		{
			if (::ioctl(fd, FP_IOCTL_GET_RTC, (void *)&rtc_time) < 0)
				eDebug("[eDVBLocalTimeHandler] FP_IOCTL_GET_RTC failed: %m");
			close(fd);
		}
	}
	return rtc_time != prev_time ? rtc_time : 0;
}

static void parseDVBdate(tm &t, int mjd)
{
	int k;
	// When MJD epoch is before Unix epoch use Unix epoch.
	// The value 40587 is the number of days between the MJD epoch (1858-11-17) and the Unix epoch (1970-01-01).
	if (mjd < 40587)
	{
		mjd = 40587;
	}
	t.tm_year = (int)((mjd - 15078.2) / 365.25);
	t.tm_mon = (int)((mjd - 14956.1 - (int)(t.tm_year * 365.25)) / 30.6001);
	t.tm_mday = (int)(mjd - 14956 - (int)(t.tm_year * 365.25) - (int)(t.tm_mon * 30.6001));
	k = (t.tm_mon == 14 || t.tm_mon == 15) ? 1 : 0;
	t.tm_year = t.tm_year + k;
	t.tm_mon = t.tm_mon - 1 - k * 12;
	t.tm_mon--;
	t.tm_isdst = 0;
	t.tm_gmtoff = 0;
}

static inline void parseDVBtime_impl(tm &t, const uint8_t *data)
{
	parseDVBdate(t, (data[0] << 8) | data[1]);
	t.tm_hour = fromBCD(data[2]);
	t.tm_min = fromBCD(data[3]);
	t.tm_sec = fromBCD(data[4]);
}

time_t parseDVBtime(uint16_t mjd, uint32_t stime_bcd)
{
	tm t = {0};
	parseDVBdate(t, mjd);
	t.tm_hour = fromBCD(stime_bcd >> 16);
	t.tm_min = fromBCD((stime_bcd >> 8) & 0xFF);
	t.tm_sec = fromBCD(stime_bcd & 0xFF);
	return timegm(&t);
}

time_t parseDVBtime(const uint8_t *data)
{
	tm t = {0};
	parseDVBtime_impl(t, data);
	return timegm(&t);
}

time_t parseDVBtime(const uint8_t *data, uint16_t *hash)
{
	tm t = {0};
	parseDVBtime_impl(t, data);
	*hash = t.tm_hour * 60 + t.tm_min;
	*hash |= t.tm_mday << 11;
	return timegm(&t);
}

TimeTable::TimeTable(eDVBChannel *chan, int update_count)
	: chan(chan), m_interval_timer(eTimer::create()), update_count(update_count)
{
	CONNECT(tableReady, TimeTable::ready);
	CONNECT(m_interval_timer->timeout, TimeTable::start);
	if (chan)
		chan->getDemux(demux, 0);
}

void TimeTable::ready(int error)
{
	eDVBLocalTimeHandler::getInstance()->updateTime(error, chan, ++update_count);
}

void TimeTable::startTable(eDVBTableSpec spec)
{
	if (chan && demux)
	{
		eGTable::start(demux, spec);
	}
}

void TimeTable::startTimer(int interval)
{
	m_interval_timer->start(interval, true);
}

TDT::TDT(eDVBChannel *chan, int update_count)
	: TimeTable(chan, update_count)
{
}

int TDT::createTable(unsigned int nr, const uint8_t *data, unsigned int max)
{
	if (data && (data[0] == TID_TDT || data[0] == TID_TOT))
	{
		int length = ((data[1] & 0x0F) << 8) | data[2];
		if (length >= 5)
		{
			time_t tptime = parseDVBtime(&data[3]);
			if (tptime && tptime != -1)
				eDVBLocalTimeHandler::getInstance()->updateTime(tptime, chan, update_count);
			error = 0;
			return 1;
		}
	}
	return 0;
}

void TDT::start()
{
	eDVBTableSpec spec;
	memset(&spec, 0, sizeof(spec));
	spec.pid = TimeAndDateSection::PID;
	spec.tid = TimeAndDateSection::TID;
	spec.tid_mask = 0xFC;
	spec.timeout = TimeAndDateSection::TIMEOUT;
	spec.flags = eDVBTableSpec::tfAnyVersion |
				 eDVBTableSpec::tfHaveTID |
				 eDVBTableSpec::tfHaveTIDMask |
				 eDVBTableSpec::tfHaveTimeout;
	TimeTable::startTable(spec);
}

STT::STT(eDVBChannel *chan, int update_count)
	: TimeTable(chan, update_count)
{
}

void STT::start()
{
	TimeTable::startTable(eDVBSTTSpec());
}

int STT::createTable(unsigned int nr, const uint8_t *data, unsigned int max)
{
	SystemTimeTableSection section(data);
	time_t tptime = section.getSystemTime() - (time_t)section.getGPSOffset() + (time_t)315964800; // ATSC GPS system time epoch is 00:00 Jan 6th 1980.
	eDVBLocalTimeHandler::getInstance()->updateTime(tptime, chan, update_count);
	error = 0;
	return 1;
}

eDVBLocalTimeHandler *eDVBLocalTimeHandler::instance;
DEFINE_REF(eDVBLocalTimeHandler);

eDVBLocalTimeHandler::eDVBLocalTimeHandler()
	: m_use_dvb_time(true), m_updateNonTunedTimer(eTimer::create(eApp)), m_time_ready(false), m_SyncTimeUsing(0)
{
	if (!instance)
		instance = this;
	ePtr<eDVBResourceManager> res_mgr;
	eDVBResourceManager::getInstance(res_mgr);
	if (!res_mgr)
		eDebug("[eDVBLocalTimerHandler] No resource manager!");
	else
	{
		res_mgr->connectChannelAdded(sigc::mem_fun(*this, &eDVBLocalTimeHandler::DVBChannelAdded), m_chanAddedConn);
		eDebug("[eDVBLocalTimeHandler] RTC not ready, wait for transponder time!");
	}
	CONNECT(m_updateNonTunedTimer->timeout, eDVBLocalTimeHandler::updateNonTuned);

	m_time_debug = eSimpleConfig::getBool("config.crash.debugDVBTime", false);
}

eDVBLocalTimeHandler::~eDVBLocalTimeHandler()
{
	instance = 0;
	if (ready())
	{
#ifdef HAVE_NO_RTC
		eDebug("Dont set RTC to previous valid time, Giga box!");
#else
		eDebug("[eDVBLocalTimeHandler] Set RTC to previous valid time.");
		setRTC(::time(0), m_time_debug);
#endif
	}
}

void eDVBLocalTimeHandler::readTimeOffsetData(const char *filename)
{
	m_timeOffsetMap.clear();
	FILE *f = fopen(filename, "r");
	if (!f)
		return;
	char line[256];
	[[maybe_unused]] char *ret = fgets(line, 256, f);
	while (true)
	{
		if (!fgets(line, 256, f))
			break;
		if (strstr(line, "Transponder UTC Time Offsets\n"))
			continue;
		int dvbnamespace, tsid, onid, offs;
		if (sscanf(line, "%08x,%04x,%04x:%d\n", &dvbnamespace, &tsid, &onid, &offs) == 4)
			m_timeOffsetMap[eDVBChannelID(dvbnamespace, tsid, onid)] = offs;
	}
	fclose(f);
}

void eDVBLocalTimeHandler::writeTimeOffsetData(const char *filename)
{
	FILE *f = fopen(filename, "w+");
	if (f)
	{
		fprintf(f, "Transponder UTC Time Offsets\n");
		for (std::map<eDVBChannelID, int>::iterator it(m_timeOffsetMap.begin()); it != m_timeOffsetMap.end(); ++it)
			fprintf(f, "%08x,%04x,%04x:%d\n",
					it->first.dvbnamespace.get(),
					it->first.transport_stream_id.get(), it->first.original_network_id.get(), it->second);
		fclose(f);
	}
}

void eDVBLocalTimeHandler::setDVBTimeMode(int mode)
{
	m_SyncTimeUsing = (mode <= 2 && mode >= 0) ? mode : 0;
	setUseDVBTime(mode != 1);
}

void eDVBLocalTimeHandler::setUseDVBTime(bool b)
{
	if (m_use_dvb_time != b)
	{
		if (!b)
		{
			time_t now = time(0);
			if (now < 1072224000) // 01.01.2004.
			{
				eDebug("[eDVBLocalTimeHandler] Invalid system time, refusing to disable transponder time sync!");
				return;
			}
			else
				m_time_ready = true;
		}
		if (m_use_dvb_time)
		{
			eDebug("[eDVBLocalTimeHandler] Sync local time with transponder time disabled.");
			std::map<iDVBChannel *, channel_data>::iterator it = m_knownChannels.begin();
			for (; it != m_knownChannels.end(); ++it)
			{
				if (it->second.m_prevChannelState == iDVBChannel::state_ok)
					it->second.timetable = NULL;
			}
		}
		else
		{
			eDebug("[eDVBLocalTimeHandler] Sync local time with transponder time enabled.");
			std::map<iDVBChannel *, channel_data>::iterator it = m_knownChannels.begin();
			for (; it != m_knownChannels.end(); ++it)
			{
				if (it->second.m_prevChannelState == iDVBChannel::state_ok)
				{
					int system = iDVBFrontend::feSatellite;
					ePtr<iDVBFrontendParameters> parms;
					it->second.channel->getCurrentFrontendParameters(parms);
					if (parms)
						parms->getSystem(system);
					it->second.timetable = NULL;
					if (system == iDVBFrontend::feATSC)
						it->second.timetable = new STT(it->second.channel);
					else
						it->second.timetable = new TDT(it->second.channel);
					it->second.timetable->start();
				}
			}
		}
		m_use_dvb_time = b;
	}
}

void eDVBLocalTimeHandler::syncDVBTime()
{
	eDebug("[eDVBLocalTimeHandler] Sync local time with transponder time.");
	std::map<iDVBChannel *, channel_data>::iterator it = m_knownChannels.begin();
	for (; it != m_knownChannels.end(); ++it)
	{
		if (it->second.m_prevChannelState == iDVBChannel::state_ok)
		{
			int system = iDVBFrontend::feSatellite;
			ePtr<iDVBFrontendParameters> parms;
			it->second.channel->getCurrentFrontendParameters(parms);
			if (parms)
				parms->getSystem(system);
			it->second.timetable = NULL;
			if (system == iDVBFrontend::feATSC)
				it->second.timetable = new STT(it->second.channel);
			else
				it->second.timetable = new TDT(it->second.channel);
			it->second.timetable->start();
		}
	}
}

void eDVBLocalTimeHandler::updateNonTuned()
{
	if (m_SyncTimeUsing == 2)
		return;
	updateTime(-1, 0, 0);
	m_updateNonTunedTimer->start(TIME_UPDATE_INTERVAL, true);
}

void eDVBLocalTimeHandler::updateTime(time_t tp_time, eDVBChannel *chan, int update_count)
{

	if (m_time_debug)
		eDebug("[eDVBLocalTimerHandler] updateTime : %ld", tp_time);

	if (m_SyncTimeUsing == 2)
	{
		if (tp_time != 0 && tp_time != -1)
		{ // -1 can be removed later
			tm tp_dt;
			localtime_r(&tp_time, &tp_dt);
			if (m_time_debug)
				eDebug("[eDVBLocalTimerHandler] Transponder time is %02d/%02d/%04d %02d:%02d:%02d",
					   tp_dt.tm_mday,
					   tp_dt.tm_mon + 1,
					   tp_dt.tm_year + 1900,
					   tp_dt.tm_hour,
					   tp_dt.tm_min,
					   tp_dt.tm_sec);

			// compare with system time
			time_t linuxTime = time(0);
			int time_difference = tp_time - linuxTime;
			int atime_difference = abs(time_difference);

			if (atime_difference > 30)
			{ // diff higher than 30 seconds
				timeval tdelta, tolddelta;
				tdelta.tv_sec = time_difference;
				int rc = adjtime(&tdelta, &tolddelta);
				if (rc != -1)
				{
					if (errno == EINVAL)
					{
						timeval tnow;
						gettimeofday(&tnow, 0);
						tnow.tv_sec = tp_time;
						settimeofday(&tnow, 0);
					}
					else
					{
						if (m_time_debug)
							eDebug("[eDVBLocalTimerHandler] Slewing Linux time by %d seconds FAILED! (%d) %m", time_difference, errno);
						return;
					}
				}
				/*emit*/ m_timeUpdated();

				m_use_dvb_time = false;

				std::map<iDVBChannel *, channel_data>::iterator it = m_knownChannels.begin();
				for (; it != m_knownChannels.end(); ++it)
				{
					if (it->second.m_prevChannelState == iDVBChannel::state_ok)
						it->second.timetable = NULL;
				}
			}
		}
		return;
	}

	int time_difference;
	bool restart_tdt = false;
	if (!tp_time)
		restart_tdt = true;
	else if (tp_time == -1)
	{
		restart_tdt = true;
		/* if (eSystemInfo::getInstance()->getHwType() == eSystemInfo::DM7020 ||
			(eSystemInfo::getInstance()->getHwType() == eSystemInfo::DM7000 &&
			eSystemInfo::getInstance()->hasStandbyWakeupTimer())) // TODO !!!!!!! */
		{
			if (m_time_debug)
				eDebug("[eDVBLocalTimerHandler] No transponder tuned, or no TDT/TOT available, try to use RTC.");
			time_t rtc_time = getRTC();
			if (rtc_time) // RTC Ready?
			{
				tm now;
				localtime_r(&rtc_time, &now);
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] RTC time is %02d:%02d:%02d.",
						   now.tm_hour,
						   now.tm_min,
						   now.tm_sec);
				time_t linuxTime = time(0);
				localtime_r(&linuxTime, &now);
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Receiver time is %02d:%02d:%02d.",
						   now.tm_hour,
						   now.tm_min,
						   now.tm_sec);
				time_difference = rtc_time - linuxTime;
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] RTC to receiver time difference is %ld seconds.", linuxTime - rtc_time);
				if (time_difference)
				{
					if (m_time_debug)
						eDebug("[eDVBLocalTimerHandler] set Linux Time to RTC Time");
					timeval tnow;
					gettimeofday(&tnow, 0);
					tnow.tv_sec = rtc_time;
					settimeofday(&tnow, 0);
				}
				else if (!time_difference)
				{
					if (m_time_debug)
						eDebug("[eDVBLocalTimerHandler] No change needed.");
				}
				else
				{
					if (m_time_debug)
						eDebug("[eDVBLocalTimerHandler] Set to RTC time.");
				}
				/*emit*/ m_timeUpdated();
			}
			else
			{
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Warning: getRTC returned time=0, RTC problem?");
			}
		}
	}
	else
	{
		std::map<eDVBChannelID, int>::iterator it(m_timeOffsetMap.find(chan->getChannelID()));
		// Current Linux time.
		time_t linuxTime = time(0);
#ifdef DEBUG
		// Current transponder time.
		tm tp_now;
		localtime_r(&tp_time, &tp_now);
		if (m_time_debug)
			eDebug("[eDVBLocalTimerHandler] Transponder time is %02d/%02d/%04d %02d:%02d:%02d.",
				   tp_now.tm_mday,
				   tp_now.tm_mon + 1,
				   tp_now.tm_year + 1900,
				   tp_now.tm_hour,
				   tp_now.tm_min,
				   tp_now.tm_sec);
#endif
		// Difference between current enigma time and transponder time.
		int enigma_diff = tp_time - linuxTime;
		int new_diff = 0;
		bool updated = m_time_ready;
		if (m_time_ready) // Ref time ready?
		{
			// Difference between reference time (current enigma time) and the transponder time.
			if (m_time_debug)
				eDebug("[eDVBLocalTimerHandler] Difference is %d.", enigma_diff);
			if (abs(enigma_diff) < 120)
			{
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Difference less than 120, use transponder time.");
				m_timeOffsetMap[chan->getChannelID()] = 0;
				new_diff = enigma_diff;
			}
			else if (it != m_timeOffsetMap.end()) // Correction saved?
			{
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] We have correction %d.", it->second);
				time_t CorrectedTpTime = tp_time + it->second;
				int ddiff = CorrectedTpTime - linuxTime;
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Difference after correction is %d.", ddiff);
				if (abs(it->second) < 300) // Stored correction < 5 min.
				{
					if (m_time_debug)
						eDebug("[eDVBLocalTimerHandler] Use stored correction (<5 min).");
					new_diff = ddiff;
				}
				else if (getRTC())
				{
					time_t rtc = getRTC();
					m_timeOffsetMap[chan->getChannelID()] = rtc - tp_time;
					new_diff = rtc - linuxTime; // Set enigma time to RTC.
					if (m_time_debug)
						eDebug("[eDVBLocalTimerHandler] Update stored correction to %ld.  (Calculated against RTC time.)", rtc - tp_time);
				}
				else if (abs(ddiff) <= 120)
				{
					// Stored correction calculated time difference is less than 2 minutes.
					// This doesn't help when a transponder has a clock running too slow or too fast.
					// Then it's better to have a DM7020 with always running RTC.
					if (m_time_debug)
						eDebug("[eDVBLocalTimerHandler] Use stored correction.  (Correction < 2 min.)");
					new_diff = ddiff;
				}
				else // Big change in calculated correction, hold current time and update correction.
				{
					if (m_time_debug)
						eDebug("[eDVBLocalTimerHandler] Update stored correction to %d.", -enigma_diff);
					m_timeOffsetMap[chan->getChannelID()] = -enigma_diff;
				}
			}
			else
			{
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] No correction found, store calculated correction.  (%d)", -enigma_diff);
				m_timeOffsetMap[chan->getChannelID()] = -enigma_diff;
			}
		}
		else // No time set yet.
		{
			if (it != m_timeOffsetMap.end())
			{
				enigma_diff += it->second;
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] We have correction (%d) to use.", it->second);
			}
			else
			{
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] We don't have correction, set transponder difference.");
			}
			new_diff = enigma_diff;
			m_time_ready = true;
		}
		time_t t = linuxTime + new_diff;
		m_last_tp_time_difference = tp_time - t;
		if (!new_diff && updated) // Override this check on first received TDT.
		{
			if (m_time_debug)
				eDebug("[eDVBLocalTimerHandler] Not changed.");
			return;
		}
		if (!update_count)
		{
			// Set RTC to calculated transponder time when the first TDT is received on this transponder.
			setRTC(t, m_time_debug);
			if (m_time_debug)
				eDebug("[eDVBLocalTimerHandler] Update RTC.");
		}
		else if (getRTC())
		{
			if (abs(getRTC() - t) > 60)
			{
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Difference between Linux time and RTC time is > 60 sec, transponder time looks bad, use RTC time.");
				t = getRTC();
			}
			else
			{
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Difference between Linux time and RTC time is < 60 sec, transponder time looks okay.");
			}
		}
		else
		{
			if (m_time_debug)
				eDebug("[eDVBLocalTimerHandler] No RTC available.");
		}
		tm now;
		localtime_r(&t, &now);
		if (m_time_debug)
		{
			eDebug("[eDVBLocalTimerHandler] Time updated to %02d:%02d:%02d.",
				   now.tm_hour,
				   now.tm_min,
				   now.tm_sec);
		}
		time_difference = t - linuxTime; // Calculate our new linux_time -> enigma_time correction.
		if (m_time_debug)
			eDebug("[eDVBLocalTimerHandler] Time difference is %d.", time_difference);

		if (time_difference)
		{
			if ((time_difference >= -15) && (time_difference <= 15))
			{
				// Slew small differences.
				// Even good transponders can differ by 0-5 sec, if we would step these
				// the system clock would permanently jump around when zapping.
				timeval tdelta, tolddelta;
				tdelta.tv_sec = time_difference;
				int rc = adjtime(&tdelta, &tolddelta);
				if (m_time_debug)
				{
					if (rc == 0)
						eDebug("[eDVBLocalTimerHandler] Slewing Linux time by %d seconds.", time_difference);
					else
						eDebug("[eDVBLocalTimerHandler] Slewing Linux time by %d seconds FAILED!", time_difference);
				}
			}
			else
			{
				// Only step larger differences.
				timeval tnow;
				gettimeofday(&tnow, 0);
				tnow.tv_sec = t;
				settimeofday(&tnow, 0);
				linuxTime = time(0);
				localtime_r(&linuxTime, &now);
				if (m_time_debug)
				{
					eDebug("[eDVBLocalTimerHandler] Stepped Linux time to %02d:%02d:%02d.",
						   now.tm_hour,
						   now.tm_min,
						   now.tm_sec);
				}
			}
		}
		/*emit*/ m_timeUpdated();
	}

	if (restart_tdt)
	{
		std::map<iDVBChannel *, channel_data>::iterator it = m_knownChannels.find(chan);
		if (it != m_knownChannels.end())
		{
			int system = iDVBFrontend::feSatellite;
			ePtr<iDVBFrontendParameters> parms;
			chan->getCurrentFrontendParameters(parms);
			if (parms)
				parms->getSystem(system);
			int updateCount = it->second.timetable->getUpdateCount();
			it->second.timetable = NULL;
			if (system == iDVBFrontend::feATSC)
				it->second.timetable = new STT(chan, updateCount);
			else
				it->second.timetable = new TDT(chan, updateCount);
			it->second.timetable->startTimer(TIME_UPDATE_INTERVAL); // Restart TDT for this transponder in 30min.
		}
	}
}

void eDVBLocalTimeHandler::DVBChannelAdded(eDVBChannel *chan)
{
	if (chan)
	{
		// eDebug("[eDVBLocalTimerHandler] Add channel %p.", chan);
		std::pair<std::map<iDVBChannel *, channel_data>::iterator, bool> tmp =
			m_knownChannels.insert(std::pair<iDVBChannel *, channel_data>(chan, channel_data()));
		tmp.first->second.timetable = NULL;
		tmp.first->second.channel = chan;
		tmp.first->second.m_prevChannelState = -1;
		chan->connectStateChange(sigc::mem_fun(*this, &eDVBLocalTimeHandler::DVBChannelStateChanged), tmp.first->second.m_stateChangedConn);
	}
}

void eDVBLocalTimeHandler::DVBChannelStateChanged(iDVBChannel *chan)
{
	std::map<iDVBChannel *, channel_data>::iterator it = m_knownChannels.find(chan);
	if (it != m_knownChannels.end())
	{
		int state = 0;
		chan->getState(state);
		if (state != it->second.m_prevChannelState)
		{
			int system = iDVBFrontend::feSatellite;
			ePtr<iDVBFrontendParameters> parms;
			it->second.channel->getCurrentFrontendParameters(parms);
			if (parms)
				parms->getSystem(system);
			switch (state)
			{
			case iDVBChannel::state_ok:
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Channel %p running.", chan);
				m_updateNonTunedTimer->stop();
				if (m_use_dvb_time)
				{
					it->second.timetable = NULL;
					if (system == iDVBFrontend::feATSC)
						it->second.timetable = new STT(it->second.channel);
					else
						it->second.timetable = new TDT(it->second.channel);
					it->second.timetable->start();
				}
				break;
			case iDVBChannel::state_release:
				if (m_time_debug)
					eDebug("[eDVBLocalTimerHandler] Remove channel %p.", chan);
				m_knownChannels.erase(it);
				if (m_SyncTimeUsing != 2)
				{
					if (m_knownChannels.empty())
						m_updateNonTunedTimer->start(TIME_UPDATE_INTERVAL, true);
				}
				return;
			default: // Ignore all other events.
				return;
			}
			it->second.m_prevChannelState = state;
		}
	}
}
