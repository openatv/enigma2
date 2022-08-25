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
 * 
 * mode
 * 0 Event überwachen
 * 1 in "other transport stream, present/following" nach Event suchen
 *   und bei running_status 2 <= x <= 4 beenden
 * 2 nach PDC-Zeit suchen und Event-ID zurückgeben
 * 3 in "other transport stream, present/following" nach PDC suchen und Event-ID zurückgeben
 * 10 prüfen, ob überhaupt PDC vorhanden
 * 
 **/

#include "vps.h"
#include <sys/ioctl.h>
#include <fcntl.h>
#include <signal.h>
#include <string.h>
#include <errno.h>
#include <iostream>
#include <cstdlib>
#include <unistd.h>

using std::cout;
using std::endl;
using std::atoi;
using std::flush;


const time_t max_wait_time = 20 * 60;
bool isAbort = false;
uint8_t mode;



int main(int argc, char *argv[])
{
	signal(SIGINT, abort_program);
	signal(SIGTERM, abort_program);
	
	if (argc < 7)
	{
		cout << "too few arguments" << endl;
		return 0;
	}
	
	mode = atoi(argv[2]);
	int n = 0;
	
	
	// 0x12 EIT-PID
	// 0x4e EIT - actual transport stream, present/following
	// 0x4f EIT - other_transport_stream, present/following
	// 0x50 EIT - actual_transport_stream, schedule (first four days)
	if (mode == 0)
	{
		Event_monitoring monitor(argc, argv);
		n = monitor.start(0x12, 0x4e, 0xff, 8000);
	}
	else if (mode == 1)
	{
		Wait_for_beginning wait(argc, argv);
		n = wait.start(0x12, 0x4f, 0xff, 30000);
		if (n == -2)
			n = wait.start(3218, 0x4f, 0xff, 30000); // Kabel Deutschland Barker PID
	}
	else if (mode == 2)
	{
		Seek_pdc seek(argc, argv);
		n = seek.start(0x12, 0x4e, 0xff, 8000);
	}
	else if (mode == 3)
	{	
		Seek_pdc seek(argc, argv);
		n = seek.start(0x12, 0x4f, 0xff, 30000);
	}
	else if (mode == 10)
	{	
		Check_pdc_existing check(argc, argv);
		n = check.start(0x12, 0x4e, 0xff, 8000);
	}
	
	
	if (n == -2)
		cout << "DMX_ERROR_TIMEOUT\n" << flush;
	
	return 0;
}


Monitoring_epg::Monitoring_epg(int argc, char *argv[])
{
	f_demux = argv[1];
	onid = atoi(argv[3]);
	tsid = atoi(argv[4]);
	sid = atoi(argv[5]);
	event_id = atoi(argv[6]);
}

Monitoring_epg::~Monitoring_epg() { }

int Monitoring_epg::start(uint16_t pid_, uint8_t table_id_, uint8_t table_mask_, int timeout_)
{
	pid = pid_;
	table_id = table_id_;
	table_mask = table_mask_;
	timeout = timeout_;
	
	if (!openDemux())
		return -1;
	
	// Startzeit
	time(&received_event_last_time);
		
	// Daten vom Demux lesen und auswerten
	bool timeout_error = false;
	while (!isAbort)
	{
		int n;
		b = &buf[0];
		n = read(fd_demux, b, sizeof(buf));
		
		if (n == 0) continue;
		else if (n < 0)
		{
			if (errno == ETIMEDOUT)
			{
				timeout_error = true;
				break;
			}
			else if (errno == EOVERFLOW)
				cout << "DMX_OVERFLOW\n";
			
			continue;
		}
		
		checkTable();
		cout << flush; // Die Ausgabe muss zeitnah ankommen
	}
	
	// Demux schließen
	ioctl(fd_demux, DMX_STOP, 0);
	close(fd_demux);
	
	if (timeout_error)
 		return -2;
	
	return 0;
}

void Monitoring_epg::checkTable()
{
	// überprüfe Table-ID
	//if ((b[0] & table_mask) != (table_id & table_mask))
	//	return;
	
	// überprüfe SID, TSID, ONID
	if (r16(&b[3]) != sid)
		return;
	if (r16(&b[10]) != onid)
		return;
	if (r16(&b[8]) != tsid)
		return;
	
	// current_next_indicator muss 1 sein
	if ((b[5] & 0x1) == 0)
		return;
		
	section_length = ((b[1] & 0x0f) << 8) + b[2];
	section_number = b[6];
	
	// header data after length value
	only_header = ((section_length - 11) <= 16); // 12 Bytes Event-Header + 4 Bytes CRC
	
	process();
}

bool Monitoring_epg::openDemux()
{
	if ((fd_demux = open(f_demux, O_RDWR)) < 0)
	{
		cout << "CANNOT_OPEN_DEMUX" << endl;
		return false;
	}
	  
	memset(&demux_filter, 0, sizeof (struct dmx_sct_filter_params));

	demux_filter.pid = pid;
	
	demux_filter.filter.filter[0] = table_id;
	demux_filter.filter.mask[0] = table_mask;

	// Service-ID als Filter setzen
	demux_filter.filter.filter[1] = sid >> 8;
	demux_filter.filter.mask[1] = 0xff;
	demux_filter.filter.filter[2] = sid & 0xff;
	demux_filter.filter.mask[2] = 0xff;
	
	demux_filter.flags = DMX_IMMEDIATE_START | DMX_CHECK_CRC;
	demux_filter.timeout = timeout;
	
	if (ioctl(fd_demux, DMX_SET_FILTER, &demux_filter) < 0)
	{
		cout << "DMX_SET_FILTER_ERROR" << endl;
		close(fd_demux);
		return false;
	}
	
	return true;
}



//
// mode 0: Running-Status eines Events überwachen
//   im Hintergrund nach zusammengehörigen Events suchen (gleiche PDC-Zeit)
//

Event_monitoring::Event_monitoring(int argc, char *argv[]) : Monitoring_epg(argc, argv)
{
	service_event_now = 0;
	service_event_next = 0;
	service_event_checked_now = false;
	service_event_checked_next = false;
	event_last_running_status = -1;
	pdc_time = 0;
	event_now_start_time = 0;
	seeking_mode = 0;
	started_seeking = 0;
}
Event_monitoring::~Event_monitoring() { }

void Event_monitoring::setNowNext(int nevent)
{
	if (section_number == 0 && service_event_now != nevent)
		service_event_now = nevent;
	else if (section_number == 1 && service_event_next != nevent)
		service_event_next = nevent;
	
	if (service_event_now != event_id && service_event_next != event_id && event_last_running_status >= 0)
	{
		if (section_number == 0)
			service_event_checked_now = true;
		else if (section_number == 1)
			service_event_checked_next = true;
		
		if (service_event_checked_now && service_event_checked_next)
		{
			cout << "EVENT_ENDED\n" << flush;
			abort_program(1);
		}
	}
	else if ((service_event_checked_now || service_event_checked_next)
		&& (service_event_now == event_id || service_event_next == event_id))
	{
		service_event_checked_now = false;
		service_event_checked_next = false;
	}
	else if (event_last_running_status == -1 && service_event_now != event_id
		&& service_event_next != event_id && service_event_now != 0 && service_event_next != 0)
	{
		seeking_mode = 1;
		event_last_running_status = -2;
		seeking_initiated = false;
		changeFilter(false);
		time(&started_seeking);
	}
}

void Event_monitoring::process()
{
	if (b[0] != 0x4e)
	{
		process_schedule_eit();
		return;
	}
	
	if (only_header)
	{
		setNowNext(0);
		return;
	}
	
	b += 14;
	uint16_t n_event_id = r16(&b[0]);
	setNowNext(n_event_id);
	
	if (n_event_id != event_id)
	{	
		time_t newtime;
		time(&newtime);
		if ((newtime - received_event_last_time) > max_wait_time)
		{
			cout << "EVENT_ENDED TIMEOUT " << (newtime - received_event_last_time) << "\n" << flush;
			abort_program(1);
		}
		
		if (event_now_start_time == 0 && section_number == 0)
		{
			event_now_start_time = parseDVBtime(b[2], b[3], b[4], b[5], b[6]);
			time_t duration = (fromBCD(b[7]) * 3600) + (fromBCD(b[8]) * 60) + fromBCD(b[9]);

			// rudimentäre Erkennung, ob der EPG des Senders gerade fehlerhaft ist (hängt)
			if ((newtime - event_now_start_time - duration) > 2*3600)
				cout << "EIT_APPARENTLY_UNRELIABLE " << (newtime - event_now_start_time - duration) << "\n" << flush;
		}
		
		return;
	}
	
	// aktualisiere Zeit
	time(&received_event_last_time);
	
	char running_status = b[10] >> 5;
	
	if (running_status != event_last_running_status)
	{
 		cout << "RUNNING_STATUS " << int(running_status) << " " 
			<< ((section_number) ? "FOLLOWING" : "PRESENT")<< "\n" << flush;
		event_last_running_status = running_status;
	}
	
	
	if (started_seeking == 0 && pdc_time > 0 && running_status == 4 && seeking_mode == 0)
	{
		seeking_mode = 2;
		seeking_initiated = false;
		changeFilter(false);
		time(&started_seeking);
		pdc_exclude_event_ids.insert(event_id);
	}
	if (pdc_time == 0)
	{
		pdc_time = -1;
		checkPDC(true);
	}
	if (seeking_mode == 1)
	{
		seeking_mode = 0;
		changeFilter(true);
		checked_sections.clear();
	}
}

bool Event_monitoring::checkPDC(bool set)
{
	int descriptors_loop_length = ((b[10] & 0x0f) << 8) + b[11];
	b += 12;
	bool matches = false;
	
	while (descriptors_loop_length > 0)
	{
		if (b[0] == 105) // PDC-Descriptor
		{
			if (set)
			{
				pdc_time = GET_PDC(b);
			}
			else if (GET_PDC(b) == pdc_time)
			{
				matches = true;
			}
		}
		
		int desc_length = b[1] + 2;
		b += desc_length;
		descriptors_loop_length -= desc_length;
	}
	
	return matches;
}

void Event_monitoring::process_schedule_eit()
{
	uint8_t table = b[0];
	uint8_t last_section_number = b[7];
	uint8_t segment_last_section_number = b[12];
	
	b += 14;
	int len1 = section_length - 11;
	while (len1 > 4)
	{
		int n_event_id = r16(&b[0]);
		int descriptors_loop_length = ((b[10] & 0x0f) << 8) + b[11];
		
		len1 -= 12 + descriptors_loop_length;
		
		if (seeking_mode == 1)
		{
			if (n_event_id == event_id)
			{
				time_t event_time = parseDVBtime(b[2], b[3], b[4], b[5], b[6]);
				time_t duration = (fromBCD(b[7]) * 3600) + (fromBCD(b[8]) * 60) + fromBCD(b[9]);
				if (event_time >= event_now_start_time)
					cout << "FOUND_EVENT_ON_SCHEDULE " << event_time << " " << duration << "\n" << flush;
				else
					cout << "EVENT_OVER\n" << flush;
				
				changeFilter(true);
				checked_sections.clear();
				seeking_initiated = false;
				seeking_mode = 0;
				started_seeking = 0;
				return;
			}
			b += 12 + descriptors_loop_length;
		}
		else if (seeking_mode == 2 && checkPDC() && pdc_exclude_event_ids.count(n_event_id) == 0)
		{
			pdc_exclude_event_ids.insert(n_event_id);
			cout << "PDC_MULTIPLE_FOUND_EVENT " << n_event_id << "\n" << flush;
		}
		
	}
	
	time_t newtime;
	time(&newtime);
	if ((table == 0x50 && checkFinished(last_section_number, segment_last_section_number))
		|| (newtime - started_seeking) > 120)
	{
		changeFilter(true);
		if (seeking_mode == 1)
		{
			cout << "CANNOT_FIND_EVENT\n" << flush;
			started_seeking = 0;
		}
		
		checked_sections.clear();
		seeking_initiated = false;
		seeking_mode = 0;
	}
}

bool Event_monitoring::checkFinished(uint8_t last_section_number, uint8_t segment_last_section_number)
{
	if (!seeking_initiated)
	{
		for (int i = last_section_number + 1; i <= 255; i++)
			checked_sections.insert(i);
		seeking_initiated = true;
	}
	
	checked_sections.insert(section_number);
	
	for (int i = segment_last_section_number + 1; i <= ((int(segment_last_section_number / 8) * 8) + 7); i++)
		checked_sections.insert(i);

	return (checked_sections.size() == 256);
}

void Event_monitoring::changeFilter(bool enable)
{
	demux_filter.filter.mask[0] = table_mask = (enable) ? 0xff : 0;

	if (ioctl(fd_demux, DMX_SET_FILTER, &demux_filter) < 0)
	{
		cout << "DMX_SET_FILTER_ERROR" << endl;
	}
}



//
// mode 1: in "other transport stream, present/following" nach Event suchen
//    und bei running_status 2 <= x <= 4 beenden
//
Wait_for_beginning::Wait_for_beginning(int argc, char *argv[]) : Monitoring_epg(argc, argv)
{ }
Wait_for_beginning::~Wait_for_beginning() { }
void Wait_for_beginning::process()
{
	if (only_header)
		return;
	
	b += 14;
	uint16_t n_event_id = r16(&b[0]);
	
	if (n_event_id != event_id)
	{	
		time_t newtime;
		time(&newtime);
		if ((newtime - received_event_last_time) > max_wait_time)
		{
			cout << "TIMEOUT\n" << flush;
			abort_program(1);
		}
		return;
	}
		
	// aktualisiere Zeit
	time(&received_event_last_time);
	
	char running_status = b[10] >> 5;
	
	if (running_status >= 2 && running_status <= 4)
	{
		cout << "OTHER_TS_RUNNING_STATUS " << int(running_status) << "\n" << flush;
		abort_program(1);
	}
}


//
// mode 2/3: nach PDC-Zeit suchen und Event-ID zurückgeben
//

Seek_pdc::Seek_pdc(int argc, char *argv[]) : Monitoring_epg(argc, argv)
{
	pdc_time = 0;
	if (argc >= 11)
	{
		pdc_time = atoi(argv[7]) << 15; // day
		pdc_time += (atoi(argv[8]) << 11); // month
		pdc_time += (atoi(argv[9]) << 6); // hour
		pdc_time += atoi(argv[10]); // minute
	}
}
Seek_pdc::~Seek_pdc() { }

void Seek_pdc::process()
{
	time_t newtime;
	time(&newtime);
	if ((newtime - received_event_last_time) > max_wait_time)
	{
		cout << "TIMEOUT\n" << flush;
		abort_program(1);
	}
	
	if (only_header)
		return;
	
	b += 14;
	uint16_t n_event_id = r16(&b[0]);
	
	int descriptors_loop_length = ((b[10] & 0x0f) << 8) + b[11];
	b += 12;
	while (descriptors_loop_length > 0)
	{
		if (b[0] == 105) // PDC-Descriptor
		{
			if (GET_PDC(b) == pdc_time)
			{
				cout << "PDC_FOUND_EVENT_ID " << n_event_id << "\n" << flush;
				abort_program(1);
				return;
			}
		}
		
		int desc_length = b[1] + 2;
		b += desc_length;
		descriptors_loop_length -= desc_length;
	}
}




//
// mode 10: prüfen, ob der Sender den PDC-Descriptor überträgt
//

Check_pdc_existing::Check_pdc_existing(int argc, char *argv[]) : Monitoring_epg(argc, argv)
{ }
Check_pdc_existing::~Check_pdc_existing() { }

void Check_pdc_existing::process()
{
	time_t newtime;
	time(&newtime);
	if ((newtime - received_event_last_time) > 6)
	{
		cout << "NO_PDC_AVAILABLE\n" << flush;
		abort_program(1);
		return;
	}
	
	if (only_header)
		return;
	
	bool found_pdc = false;
	
	b += 14;
	int descriptors_loop_length = ((b[10] & 0x0f) << 8) + b[11];
	b += 12;
	while (descriptors_loop_length > 0)
	{
		if (b[0] == 105) // PDC-Descriptor
		{
			found_pdc = true;
		}
		
		int desc_length = b[1] + 2;
		b += desc_length;
		descriptors_loop_length -= desc_length;
	}
	
	if (found_pdc)
		cout << "PDC_AVAILABLE\n" << flush;
	else
		cout << "NO_PDC_AVAILABLE\n" << flush;
	
	abort_program(1);

}




// übernommen aus Enigma2
time_t parseDVBtime(uint8_t t1, uint8_t t2, uint8_t t3, uint8_t t4, uint8_t t5)
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

void abort_program(int signal)
{
	isAbort = true;
}

