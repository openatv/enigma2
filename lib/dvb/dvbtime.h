#ifndef __LIB_DVB_DVBTIME_H_
#define __LIB_DVB_DVBTIME_H_

#include <lib/base/eerror.h>
#include <lib/dvb/esection.h>
#include <lib/dvb_si/tdt.h>

class eDVBChannel;

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
	friend class TDT;
	DECLARE_REF(eDVBLocalTimeHandler)
	std::map<iDVBChannel*, TDT*> m_active_tables;
	std::map<eDVBChannelID,int> m_timeOffsetMap;
	ePtr<eConnection> m_chanAddedConn;
	ePtr<eConnection> m_chanRemovedConn;
	ePtr<eConnection> m_chanRunningConn;
	bool m_time_ready;
	int m_time_difference;
	int m_last_tp_time_difference;
	void DVBChannelAdded(eDVBChannel*);
	void DVBChannelRemoved(eDVBChannel*);
	void DVBChannelRunning(iDVBChannel*);
	void readTimeOffsetData(const char*);
	void writeTimeOffsetData(const char*);
	void updateTime(time_t tp_time, eDVBChannel*);
	static eDVBLocalTimeHandler *instance;
public:
	PSignal0<void> m_timeUpdated;
	eDVBLocalTimeHandler();
	~eDVBLocalTimeHandler();
	bool ready() { return m_time_ready; }
	int difference() { return m_time_difference; }
	static eDVBLocalTimeHandler *getInstance() { return instance; }
};

#endif // __LIB_DVB_DVBTIME_H_
