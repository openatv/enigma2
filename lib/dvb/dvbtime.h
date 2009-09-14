#ifndef __LIB_DVB_DVBTIME_H_
#define __LIB_DVB_DVBTIME_H_

#ifndef SWIG

#include <lib/base/eerror.h>
#include <lib/dvb/esection.h>
#include <dvbsi++/time_date_section.h>

class eDVBChannel;

inline int fromBCD(int bcd)
{
	if ((bcd&0xF0)>=0xA0)
		return -1;
	if ((bcd&0xF)>=0xA)
		return -1;
	return ((bcd&0xF0)>>4)*10+(bcd&0xF);
}

inline int toBCD(int dec)
{
	if (dec >= 100)
		return -1;
	return int(dec/10)*0x10 + dec%10;
}

time_t parseDVBtime(__u8 t1, __u8 t2, __u8 t3, __u8 t4, __u8 t5, __u16 *hash=0);

class TDT: public eGTable
{
	eDVBChannel *chan;
	ePtr<iDVBDemux> demux;
	ePtr<eTimer> m_interval_timer;
	int createTable(unsigned int nr, const __u8 *data, unsigned int max);
	void ready(int);
	int update_count;
public:
	TDT(eDVBChannel *chan, int update_count=0);
	void start();
	void startTimer(int interval);
	int getUpdateCount() { return update_count; }
};

#endif  // SWIG

class eDVBLocalTimeHandler: public Object
{
	DECLARE_REF(eDVBLocalTimeHandler);
	struct channel_data
	{
		ePtr<TDT> tdt;
		ePtr<eDVBChannel> channel;
		ePtr<eConnection> m_stateChangedConn;
		int m_prevChannelState;
	};
	bool m_use_dvb_time;
	ePtr<eTimer> m_updateNonTunedTimer;
	friend class TDT;
	std::map<iDVBChannel*, channel_data> m_knownChannels;
	std::map<eDVBChannelID,int> m_timeOffsetMap;
	ePtr<eConnection> m_chanAddedConn;
	bool m_time_ready;
	int m_time_difference;
	int m_last_tp_time_difference;
	void DVBChannelAdded(eDVBChannel*);
	void DVBChannelStateChanged(iDVBChannel*);
	void readTimeOffsetData(const char*);
	void writeTimeOffsetData(const char*);
	void updateTime(time_t tp_time, eDVBChannel*, int updateCount);
	void updateNonTuned();
	static eDVBLocalTimeHandler *instance;
#ifdef SWIG
	eDVBLocalTimeHandler();
	~eDVBLocalTimeHandler();
#endif
public:
#ifndef SWIG
	eDVBLocalTimeHandler();
	~eDVBLocalTimeHandler();
#endif
	bool getUseDVBTime() { return m_use_dvb_time; }
	void setUseDVBTime(bool b);
	PSignal0<void> m_timeUpdated;
	time_t nowTime() const { return m_time_ready ? ::time(0)+m_time_difference : -1; }
	bool ready() const { return m_time_ready; }
	static eDVBLocalTimeHandler *getInstance() { return instance; }
};

#endif // __LIB_DVB_DVBTIME_H_
