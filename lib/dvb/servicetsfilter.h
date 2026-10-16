#ifndef __lib_dvb_servicetsfilter_h
#define __lib_dvb_servicetsfilter_h

#include <array>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <vector>

/* Only enabled for a service whose PMT PID is shared. Replace PSI in its
 * existing packet slots; never move media/PCR packets or change file offsets.
 * Owned and used exclusively by the recorder thread. */
class eDVBServiceTSFilter
{
public:
	void configure(int serviceId, int pmtPid);
	bool active() const { return m_serviceId > 0; }
	void process(unsigned char *data, size_t length, int packetSize);

private:
	struct Table
	{
		std::vector<unsigned char> section;
		std::deque<std::vector<unsigned char>> output;
		size_t offset = 0;
		int inputCC = -1;
		unsigned char outputCC = 0;
		std::array<unsigned char, 188> previous{};
	};
	int m_serviceId = -1;
	int m_pmtPid = -1;
	Table m_pat, m_pmt;
	void packet(unsigned char *data, Table &table, bool pat);
	void append(const unsigned char *data, size_t length, bool starts, Table &table, bool pat);
	void sectionReady(Table &table, bool pat);
	void emit(unsigned char *data, Table &table, int pid, size_t payload);
};

#endif
