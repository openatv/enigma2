#include <lib/dvb/servicetsfilter.h>
#include <lib/dvb/crc32.h>
#include <algorithm>
#include <cstring>

void eDVBServiceTSFilter::configure(int serviceId, int pmtPid)
{
	if (serviceId <= 0 || serviceId > 0xffff || pmtPid <= 0 || pmtPid >= 0x1fff)
		return;
	if (serviceId != m_serviceId)
	{
		m_pat = Table();
		m_pmt = Table();
	}
	else if (pmtPid != m_pmtPid)
		m_pmt = Table();
	m_serviceId = serviceId;
	m_pmtPid = pmtPid;
}

void eDVBServiceTSFilter::process(unsigned char *data, size_t length, int packetSize)
{
	if (!active() || (packetSize != 188 && packetSize != 192))
		return;
	for (size_t pos = 0; pos + packetSize <= length; pos += packetSize)
	{
		unsigned char *ts = data + pos + packetSize - 188;
		if (ts[0] != 0x47)
			continue;
		int pid = ((ts[1] & 0x1f) << 8) | ts[2];
		if (!pid)
			packet(ts, m_pat, true);
		else if (pid == m_pmtPid)
			packet(ts, m_pmt, false);
	}
}

void eDVBServiceTSFilter::append(const unsigned char *data, size_t length, bool starts, Table &table, bool pat)
{
	while (length)
	{
		if (table.section.empty() && (!starts || *data == 0xff))
			return;
		size_t needed = 3;
		if (table.section.size() >= 3)
		{
			needed += ((table.section[1] & 0x0f) << 8) | table.section[2];
			if (needed < (pat ? 12U : 16U) || needed > 1024 ||
				table.section[0] != (pat ? 0 : 2) || !(table.section[1] & 0x80))
			{
				table.section.clear();
				return;
			}
		}
		size_t count = std::min(length, needed - table.section.size());
		table.section.insert(table.section.end(), data, data + count);
		data += count;
		length -= count;
		if (needed > 3 && table.section.size() == needed)
		{
			sectionReady(table, pat);
			table.section.clear();
		}
	}
}

void eDVBServiceTSFilter::sectionReady(Table &table, bool pat)
{
	const auto &s = table.section;
	if (!(s[5] & 1) || s[6] > s[7] || crc32(0xffffffff, s.data(), s.size()))
		return;
	std::vector<unsigned char> output;
	if (pat)
	{
		if ((s.size() - 12) % 4)
			return;
		for (size_t pos = 8; pos + 4 <= s.size() - 4; pos += 4)
		{
			if (((s[pos] << 8) | s[pos + 1]) != m_serviceId)
				continue;
			int pid = ((s[pos + 2] & 0x1f) << 8) | s[pos + 3];
			if (!pid || pid == 0x1fff)
				return;
			// Follow PAT changes, even before the main loop updates the PID set.
			if (pid != m_pmtPid)
			{
				m_pmtPid = pid;
				m_pmt = Table();
			}
			output.assign(s.begin(), s.begin() + 8);
			output[1] = 0xb0;
			output[2] = 13;
			output[6] = output[7] = 0;
			output.insert(output.end(), s.begin() + pos, s.begin() + pos + 4);
			uint32_t crc = crc32(0xffffffff, output.data(), output.size());
			for (int shift = 24; shift >= 0; shift -= 8)
				output.push_back(crc >> shift);
			break;
		}
	}
	else if (((s[3] << 8) | s[4]) == m_serviceId)
		output = s; // Keep all elementary streams and CA/other descriptors intact.
	// Bound memory even for corrupt/adversarial input. Never emit a partial table.
	if (!output.empty() && table.output.size() < 16)
		table.output.push_back(std::move(output));
}

void eDVBServiceTSFilter::packet(unsigned char *ts, Table &table, bool pat)
{
	int pid = ((ts[1] & 0x1f) << 8) | ts[2];
	int afc = (ts[3] >> 4) & 3;
	size_t payload = 4;
	bool valid = !(ts[1] & 0x80) && !(ts[3] & 0xc0) && afc;
	if (afc & 2)
	{
		payload += 1 + ts[4];
		valid = valid && payload <= 188 && (afc != 3 || payload < 188);
		if (valid && ts[4] && (ts[5] & 0x80))
		{
			table.section.clear();
			table.inputCC = -1;
		}
	}
	if (!valid)
	{
		table.section.clear();
		table.inputCC = -1;
		payload = 4; // Discard malformed adaptation fields too.
	}
	else if (afc & 1)
	{
		int cc = ts[3] & 15;
		bool duplicate = cc == table.inputCC && !memcmp(ts, table.previous.data(), 188);
		if (!duplicate)
		{
			if (table.inputCC >= 0 && cc != ((table.inputCC + 1) & 15))
				table.section.clear();
			table.inputCC = cc;
			memcpy(table.previous.data(), ts, 188);
			if (ts[1] & 0x40)
			{
				size_t pointer = ts[payload++];
				if (pointer <= 188 - payload)
				{
					append(ts + payload, pointer, false, table, pat);
					table.section.clear();
					append(ts + payload + pointer, 188 - payload - pointer, true, table, pat);
				}
				else
					table.section.clear();
			}
			else
				append(ts + payload, 188 - payload, false, table, pat);
		}
		// Output owns its pointer field; only preserve the input adaptation field.
		payload = (afc & 2) ? 5 + ts[4] : 4;
	}
	emit(ts, table, pid, payload);
}

void eDVBServiceTSFilter::emit(unsigned char *ts, Table &table, int pid, size_t payload)
{
	if (table.output.empty() || payload >= 187)
	{
		if (payload > 5) // Preserve adaptation data, including any PCR, without payload.
		{
			ts[1] = pid >> 8;
			ts[2] = pid;
			ts[3] = 0x20 | ((table.outputCC + 15) & 15);
			ts[4] = 183;
			memset(ts + payload, 0xff, 188 - payload);
		}
		else
		{
			ts[1] = 0x1f;
			ts[2] = 0xff;
			ts[3] = 0x10;
			memset(ts + 4, 0xff, 184);
		}
		return;
	}
	size_t remaining = table.output.front().size() - table.offset;
	bool starts = !table.offset || (table.output.size() > 1 && remaining < 187 - payload);
	ts[1] = (pid >> 8) | (starts ? 0x40 : 0);
	ts[2] = pid;
	ts[3] = (payload > 4 ? 0x30 : 0x10) | table.outputCC;
	table.outputCC = (table.outputCC + 1) & 15;
	if (starts)
		ts[payload++] = table.offset ? remaining : 0;
	while (payload < 188 && !table.output.empty())
	{
		const auto &s = table.output.front();
		size_t count = std::min(188 - payload, s.size() - table.offset);
		memcpy(ts + payload, s.data() + table.offset, count);
		table.offset += count;
		payload += count;
		if (table.offset == s.size())
		{
			table.output.pop_front();
			table.offset = 0;
			if (!starts)
				break;
		}
	}
	memset(ts + payload, 0xff, 188 - payload);
}
