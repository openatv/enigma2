#ifndef __LIB_DVB_DVBTIME_H_
#define __LIB_DVB_DVBTIME_H_

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

time_t parseDVBtime(__u8 t1, __u8 t2, __u8 t3, __u8 t4, __u8 t5);

class TDT: public eGTable
{
	eDVBChannel *chan;
	ePtr<iDVBDemux> demux;
	eTimer m_interval_timer;
	int createTable(int nr, const __u8 *data, unsigned int max);
	void ready(int);
public:
	TDT(eDVBChannel *chan);
	void start();
	void startTimer(int interval);
};

class eDVBLocalTimeHandler: public Object
{
	struct channel_data
	{
		TDT *tdt;
		ePtr<eDVBChannel> channel;
		ePtr<eConnection> m_stateChangedConn;
	};
	friend class TDT;
	DECLARE_REF(eDVBLocalTimeHandler)
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
	void updateTime(time_t tp_time, eDVBChannel*);
	static eDVBLocalTimeHandler *instance;
public:
	PSignal0<void> m_timeUpdated;
	eDVBLocalTimeHandler();
	~eDVBLocalTimeHandler();
	bool ready() const { return m_time_ready; }
	int difference() const { return m_time_difference; }
	static eDVBLocalTimeHandler *getInstance() { return instance; }
};

#endif // __LIB_DVB_DVBTIME_H_
