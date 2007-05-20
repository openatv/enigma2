#define _ISOC99_SOURCE /* for llabs */
#include <lib/dvb/tstools.h>
#include <lib/base/eerror.h>
#include <unistd.h>
#include <fcntl.h>

#include <stdio.h>

eDVBTSTools::eDVBTSTools()
{
	m_pid = -1;
	m_maxrange = 256*1024;
	
	m_begin_valid = 0;
	m_end_valid = 0;
	
	m_use_streaminfo = 0;
	m_samples_taken = 0;
	
	m_last_filelength = 0;
	
	m_futile = 0;
}

eDVBTSTools::~eDVBTSTools()
{
	closeFile();
}

int eDVBTSTools::openFile(const char *filename, int nostreaminfo)
{
	closeFile();
	
	if (!nostreaminfo)
		m_streaminfo.load((std::string(filename) + ".ap").c_str());
	
	if (!m_streaminfo.empty())
		m_use_streaminfo = 1;
	else
	{
//		eDebug("no recorded stream information available");
		m_use_streaminfo = 0;
	}
	
	m_samples_taken = 0;

	if (m_file.open(filename, 1) < 0)
		return -1;
	return 0;
}

void eDVBTSTools::closeFile()
{
	m_file.close();
}

void eDVBTSTools::setSyncPID(int pid)
{
	m_pid = pid;
}

void eDVBTSTools::setSearchRange(int maxrange)
{
	m_maxrange = maxrange;
}

	/* getPTS extracts a pts value from any PID at a given offset. */
int eDVBTSTools::getPTS(off_t &offset, pts_t &pts, int fixed)
{
	if (m_use_streaminfo)
		return m_streaminfo.getPTS(offset, pts);
	
	if (!m_file.valid())
		return -1;

	offset -= offset % 188;
	
	if (m_file.lseek(offset, SEEK_SET) < 0)
	{
		eDebug("lseek failed");
		return -1;
	}
	
	int left = m_maxrange;
	
	while (left >= 188)
	{
		unsigned char packet[188];
		if (m_file.read(packet, 188) != 188)
		{
			eDebug("read error");
			break;
		}
		left -= 188;
		offset += 188;
		
		if (packet[0] != 0x47)
		{
			eDebug("resync");
			int i = 0;
			while (i < 188)
			{
				if (packet[i] == 0x47)
					break;
				++i;
			}
			offset = m_file.lseek(i - 188, SEEK_CUR);
			continue;
		}
		
		int pid = ((packet[1] << 8) | packet[2]) & 0x1FFF;
		int pusi = !!(packet[1] & 0x40);
		
//		printf("PID %04x, PUSI %d\n", pid, pusi);

		unsigned char *payload;
		
			/* check for adaption field */
		if (packet[3] & 0x20)
		{
			if (packet[4] >= 183)
				continue;
			if (packet[4])
			{
				if (packet[5] & 0x10) /* PCR present */
				{
					pts  = ((unsigned long long)(packet[ 6]&0xFF)) << 25;
					pts |= ((unsigned long long)(packet[ 7]&0xFF)) << 17;
					pts |= ((unsigned long long)(packet[ 8]&0xFE)) << 9;
					pts |= ((unsigned long long)(packet[ 9]&0xFF)) << 1;
					pts |= ((unsigned long long)(packet[10]&0x80)) >> 7;
					offset -= 188;
					eDebug("PCR  found at %llx: %16llx", offset, pts);
					if (fixed && fixupPTS(offset, pts))
						return -1;
					return 0;
				}
			}
			payload = packet + packet[4] + 4 + 1;
		} else
			payload = packet + 4;

		
		if (m_pid >= 0)
			if (pid != m_pid)
				continue;
		if (!pusi)
			continue;
		
		
			/* somehow not a startcode. (this is invalid, since pusi was set.) ignore it. */
		if (payload[0] || payload[1] || (payload[2] != 1))
			continue;
		
			/* drop non-audio, non-video packets because other streams
			   can be non-compliant.*/
		if (((payload[3] & 0xE0) != 0xC0) &&  // audio
		    ((payload[3] & 0xF0) != 0xE0))    // video
			continue;
		
		if (payload[7] & 0x80) /* PTS */
		{
			pts  = ((unsigned long long)(payload[ 9]&0xE))  << 29;
			pts |= ((unsigned long long)(payload[10]&0xFF)) << 22;
			pts |= ((unsigned long long)(payload[11]&0xFE)) << 14;
			pts |= ((unsigned long long)(payload[12]&0xFF)) << 7;
			pts |= ((unsigned long long)(payload[13]&0xFE)) >> 1;
			offset -= 188;

//			eDebug("found pts %08llx at %08llx pid %02x stream: %02x", pts, offset, pid, payload[3]);
			
				/* convert to zero-based */
			if (fixed && fixupPTS(offset, pts))
					return -1;
			return 0;
		}
	}
	
	return -1;
}

int eDVBTSTools::fixupPTS(const off_t &offset, pts_t &now)
{
	if (m_use_streaminfo)
	{
		return m_streaminfo.fixupPTS(offset, now);
	} else
	{
			/* for the simple case, we assume one epoch, with up to one wrap around in the middle. */
		calcBegin();
		if (!m_begin_valid)
		{	
			eDebug("begin not valid, can't fixup");
			return -1;
		}
		
		pts_t pos = m_pts_begin;
		if ((now < pos) && ((pos - now) < 90000 * 10))
		{	
			pos = 0;
			return 0;
		}
		
		if (now < pos) /* wrap around */
			now = now + 0x200000000LL - pos;
		else
			now -= pos;
		return 0;
	}
}

int eDVBTSTools::getOffset(off_t &offset, pts_t &pts)
{
	if (m_use_streaminfo)
	{
		offset = m_streaminfo.getAccessPoint(pts);
		return 0;
	} else
	{
		calcBegin(); calcEnd();
		
		if (!m_begin_valid)
			return -1;
		if (!m_end_valid)
			return -1;

		if (!m_samples_taken)
			takeSamples();
		
		if (!m_samples.empty())
		{
			int maxtries = 5;
			pts_t p = -1;
			
			while (maxtries--)
			{
					/* search entry before and after */
				std::map<pts_t, off_t>::const_iterator l = m_samples.lower_bound(pts);
				std::map<pts_t, off_t>::const_iterator u = l;

				if (l != m_samples.begin())
					--l;
				
					/* we could have seeked beyond the end */
				if (u == m_samples.end())
				{
						/* use last segment for interpolation. */
					if (l != m_samples.begin())
					{
						--u;
						--l;
					}
				}
					
					/* if we don't have enough points */
				if (u == m_samples.end())
					break;
				
				pts_t pts_diff = u->first - l->first;
				off_t offset_diff = u->second - l->second;

				eDebug("using: %llx:%llx -> %llx:%llx", l->first, u->first, l->second, u->second);

				int bitrate;
				
				if (pts_diff)
					bitrate = offset_diff * 90000 * 8 / pts_diff;
				else
					bitrate = 0;

				offset = l->second;
				offset += ((pts - l->first) * (pts_t)bitrate) / 8ULL / 90000ULL;
				offset -= offset % 188;
				
				p = pts;
				
				if (!takeSample(offset, p))
				{
					int diff = (p - pts) / 90;
			
					eDebug("calculated diff %d ms", diff);
					if (abs(diff) > 300)
					{
						eDebug("diff to big, refining");
						continue;
					}
				} else
					eDebug("no sample taken, refinement not possible.");

				break;
			}
			
				/* if even the first sample couldn't be taken, fall back. */
				/* otherwise, return most refined result. */
			if (p != -1)
			{
				pts = p;
				return 0;
			}
		}
		
		int bitrate = calcBitrate();
		offset = pts * (pts_t)bitrate / 8ULL / 90000ULL;
		offset -= offset % 188;
		
		return 0;
	}
}

int eDVBTSTools::getNextAccessPoint(pts_t &ts, const pts_t &start, int direction)
{
	if (m_use_streaminfo)
		return m_streaminfo.getNextAccessPoint(ts, start, direction);
	else
	{
		eDebug("can't get next access point without streaminfo");
		return -1;
	}
}

void eDVBTSTools::calcBegin()
{
	if (!m_file.valid())
		return;

	if (!(m_begin_valid || m_futile))
	{
		m_offset_begin = 0;
		if (!getPTS(m_offset_begin, m_pts_begin))
			m_begin_valid = 1;
		else
			m_futile = 1;
	}
}

void eDVBTSTools::calcEnd()
{
	if (!m_file.valid())
		return;
	
	off_t end = m_file.lseek(0, SEEK_END);
	
	if (llabs(end - m_last_filelength) > 1*1024*1024)
	{
		m_last_filelength = end;
		m_end_valid = 0;
		
		m_futile = 0;
//		eDebug("file size changed, recalc length");
	}
	
	int maxiter = 10;
	
	m_offset_end = m_last_filelength;
	
	while (!(m_end_valid || m_futile))
	{
		if (!--maxiter)
		{
			m_futile = 1;
			return;
		}

		m_offset_end -= m_maxrange;
		if (m_offset_end < 0)
			m_offset_end = 0;

			/* restore offset if getpts fails */
		off_t off = m_offset_end;

		if (!getPTS(m_offset_end, m_pts_end))
			m_end_valid = 1;
		else
			m_offset_end = off;

		if (!m_offset_end)
		{
			m_futile = 1;
			break;
		}
	}
}

int eDVBTSTools::calcLen(pts_t &len)
{
	calcBegin(); calcEnd();
	if (!(m_begin_valid && m_end_valid))
		return -1;
	len = m_pts_end - m_pts_begin;
		/* wrap around? */
	if (len < 0)
		len += 0x200000000LL;
	return 0;
}

int eDVBTSTools::calcBitrate()
{
	calcBegin(); calcEnd();
	if (!(m_begin_valid && m_end_valid))
		return -1;

	pts_t len_in_pts = m_pts_end - m_pts_begin;

		/* wrap around? */
	if (len_in_pts < 0)
		len_in_pts += 0x200000000LL;
	off_t len_in_bytes = m_offset_end - m_offset_begin;
	
	if (!len_in_pts)
		return -1;
	
	unsigned long long bitrate = len_in_bytes * 90000 * 8 / len_in_pts;
	if ((bitrate < 10000) || (bitrate > 100000000))
		return -1;
	
	return bitrate;
}

	/* pts, off */
void eDVBTSTools::takeSamples()
{
	m_samples_taken = 1;
	m_samples.clear();
	pts_t dummy;
	if (calcLen(dummy) == -1)
		return;
	
	int nr_samples = 30;
	off_t bytes_per_sample = (m_offset_end - m_offset_begin) / (long long)nr_samples;
	if (bytes_per_sample < 40*1024*1024)
		bytes_per_sample = 40*1024*1024;

	bytes_per_sample -= bytes_per_sample % 188;
	
	for (off_t offset = m_offset_begin; offset < m_offset_end; offset += bytes_per_sample)
	{
		pts_t p;
		takeSample(offset, p);
	}
	m_samples[0] = m_offset_begin;
	m_samples[m_pts_end - m_pts_begin] = m_offset_end;
	
//	eDebug("begin, end: %llx %llx", m_offset_begin, m_offset_end); 
}

	/* returns 0 when a sample was taken. */
int eDVBTSTools::takeSample(off_t off, pts_t &p)
{
	if (!eDVBTSTools::getPTS(off, p, 1))
	{
		m_samples[p] = off;
		return 0;
	}
	return 1;
}

int eDVBTSTools::findPMT(int &pmt_pid, int &service_id)
{
		/* FIXME: this will be factored out soon! */
	if (!m_file.valid())
	{
		eDebug(" file not valid");
		return -1;
	}

	if (m_file.lseek(0, SEEK_SET) < 0)
	{
		eDebug("seek failed");
		return -1;
	}

	int left = 5*1024*1024;
	
	while (left >= 188)
	{
		unsigned char packet[188];
		if (m_file.read(packet, 188) != 188)
		{
			eDebug("read error");
			break;
		}
		left -= 188;
		
		if (packet[0] != 0x47)
		{
			int i = 0;
			while (i < 188)
			{
				if (packet[i] == 0x47)
					break;
				++i;
			}
			m_file.lseek(i - 188, SEEK_CUR);
			continue;
		}
		
		int pid = ((packet[1] << 8) | packet[2]) & 0x1FFF;
		
		int pusi = !!(packet[1] & 0x40);
		
		if (!pusi)
			continue;
		
			/* ok, now we have a PES header or section header*/
		unsigned char *sec;
		
			/* check for adaption field */
		if (packet[3] & 0x20)
		{
			if (packet[4] >= 183)
				continue;
			sec = packet + packet[4] + 4 + 1;
		} else
			sec = packet + 4;
		
		if (sec[0])	/* table pointer, assumed to be 0 */
			continue;

		if (sec[1] == 0x02) /* program map section */
		{
			pmt_pid = pid;
			service_id = (sec[4] << 8) | sec[5];
			return 0;
		}
	}
	
	return -1;
}
