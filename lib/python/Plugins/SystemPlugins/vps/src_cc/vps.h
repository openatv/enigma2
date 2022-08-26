#ifndef INCLUDED_E2_PLUGIN_VPS_H
#define INCLUDED_E2_PLUGIN_VPS_H

/**
 * VPS (monitoring DVB running-status)
 *
 * Martin Gauk
 * mart-g@web.de
 * 
 *
 * Aufruf mit vps [demux] [mode] [onid] [tsid] [sid] [Event-ID] 
 *  [PDC-Time day] [PDC-Time month] [PDC-Time hour] [PDC-Time min]
 * 
 **/

#include <linux/dvb/dmx.h>
#include <time.h>
#include <set>
#include <byteswap.h>
#include <endian.h>
#include <inttypes.h>


#define READ_BUF_SIZE (4*1024)

int main(int argc, char *argv[]);
void abort_program(int signal);

class Monitoring_epg
{
	protected:
		char *f_demux;
		int fd_demux = 0;
		uint8_t buf[READ_BUF_SIZE];
		uint8_t *b = nullptr;
		uint16_t onid;
		uint16_t tsid;
		uint16_t sid;
		uint16_t event_id;
		int pdc_time = 0;
		int timeout = 0;
		uint16_t pid = 0;
		uint8_t table_id = 0;
		uint8_t table_mask = 0;
		struct dmx_sct_filter_params demux_filter;
		time_t received_event_last_time = 0;
		uint16_t section_length = 0;
		uint8_t section_number = 0;
		bool only_header = false;
		
		void virtual process() = 0;
		bool openDemux();
		void checkTable();
	
	public:
		Monitoring_epg(int argc, char *argv[]);
		~Monitoring_epg();
		int start(uint16_t pid_, uint8_t table_id_, uint8_t table_mask_, int timeout_);
};

class Event_monitoring: public Monitoring_epg
{
	private:
		uint16_t service_event_now;
		uint16_t service_event_next;
		bool service_event_checked_now;
		bool service_event_checked_next;
		char event_last_running_status;
		char seeking_mode;
		// 1 überprüfe, ob Event bereits gelaufen ist, 2 suche nach anderen Events mit gleicher PDC
		time_t event_now_start_time;
		time_t started_seeking;
		bool seeking_initiated;
		std::set<uint8_t> checked_sections;
		std::set<uint16_t> pdc_exclude_event_ids;
		
		
		void setNowNext(int nevent);
		bool checkPDC(bool set = false);
		void process_schedule_eit();
		bool checkFinished(uint8_t last_section_number, uint8_t segment_last_section_number);
		void changeFilter(bool enable);
	
	public:
		Event_monitoring(int argc, char *argv[]);
		~Event_monitoring();
		void virtual process();
};

class Wait_for_beginning: public Monitoring_epg
{
	public:
		Wait_for_beginning(int argc, char *argv[]);
		~Wait_for_beginning();
		void virtual process();
};

class Seek_pdc: public Monitoring_epg
{
	public:
		Seek_pdc(int argc, char *argv[]);
		~Seek_pdc();
		void virtual process();
};

class Check_pdc_existing: public Monitoring_epg
{
	public:
		Check_pdc_existing(int argc, char *argv[]);
		~Check_pdc_existing();
		void virtual process();
};



// übernommen aus Enigma2
time_t parseDVBtime(uint8_t t1, uint8_t t2, uint8_t t3, uint8_t t4, uint8_t t5);
inline int fromBCD(int bcd)
{
	if ((bcd&0xF0)>=0xA0)
		return -1;
	if ((bcd&0xF)>=0xA)
		return -1;
	return ((bcd&0xF0)>>4)*10+(bcd&0xF);
}

// aus libdvbsi++
#if __BYTE_ORDER == __BIG_ENDIAN
#define r16(p)		(*(const uint16_t * const)(p))
#else
#define r16(p)		bswap_16(*(const uint16_t * const)p)
#endif

#define GET_PDC(p) (((p[2] & 0x0f) << 16) | r16(&p[3]))

#endif
