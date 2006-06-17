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

int eDVBTSTools::openFile(const char *filename)
{
	closeFile();
	
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
		return -1;

	int left = m_maxrange;
	
	while (left >= 188)
	{
		unsigned char block[188];
		if (m_file.read(block, 188) != 188)
		{
			eDebug("read error");
			break;
		}
		left -= 188;
		offset += 188;
		
		if (block[0] != 0x47)
		{
			int i = 0;
			while (i < 188)
			{
				if (block[i] == 0x47)
					break;
				++i;
			}
			offset = m_file.lseek(i - 188, SEEK_CUR);
			continue;
		}
		
		int pid = ((block[1] << 8) | block[2]) & 0x1FFF;
		int pusi = !!(block[1] & 0x40);
		
//		printf("PID %04x, PUSI %d\n", pid, pusi);
		
		if (m_pid >= 0)
			if (pid != m_pid)
				continue;
		if (!pusi)
			continue;
		
			/* ok, now we have a PES header */
		unsigned char *pes;
		
			/* check for adaption field */
		if (block[3] & 0x20)
			pes = block + block[4] + 4 + 1;
		else
			pes = block + 4;
		
			/* somehow not a startcode. (this is invalid, since pusi was set.) ignore it. */
		if (pes[0] || pes[1] || (pes[2] != 1))
			continue;
		
		if (pes[7] & 0x80) /* PTS */
		{
			pts  = ((unsigned long long)(pes[ 9]&0xE))  << 29;
			pts |= ((unsigned long long)(pes[10]&0xFF)) << 22;
			pts |= ((unsigned long long)(pes[11]&0xFE)) << 14;
			pts |= ((unsigned long long)(pes[12]&0xFF)) << 7;
			pts |= ((unsigned long long)(pes[13]&0xFE)) >> 1;
			offset -= 188;
			
//			eDebug("found pts %08llx at %08llx", pts, offset);
			
				/* convert to zero-based */
			if (fixed)
				fixupPTS(offset, pts);
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
//		eDebug("get offset");
		if (!m_samples_taken)
			takeSamples();
		
		if (!m_samples.empty())
		{
//		eDebug("ok, samples ok");
				/* search entry before and after */
			std::map<pts_t, off_t>::const_iterator l = m_samples.lower_bound(pts);
			std::map<pts_t, off_t>::const_iterator u = l;

			if (l != m_samples.begin())
				--l;
		
			if ((u != m_samples.end()) && (l != m_samples.end()))
			{
				pts_t pts_diff = u->first - l->first;
				off_t offset_diff = u->second - l->second;
//		eDebug("using: %llx:%llx -> %llx:%llx", l->first, u->first, l->second, u->second);
	
				if (pts_diff)
				{
					int bitrate = offset_diff * 90000 * 8 / pts_diff;
					if (bitrate > 0)
					{
						offset = l->second;
						offset += ((pts - l->first) * (pts_t)bitrate) / 8ULL / 90000ULL;
						offset -= offset % 188;
						return 0;
					}
				}
			}
		}
		
		eDebug("falling back");
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
	
	if (abs(end - m_last_filelength) > 1*1024*1024)
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
		off_t o = offset;
		pts_t p;
		if (!eDVBTSTools::getPTS(o, p, 1))
		{
//			eDebug("sample: %llx, %llx", o, p);
			m_samples[p] = o;
		}
	}
	m_samples[m_pts_begin] = m_offset_begin;
	m_samples[m_pts_end] = m_offset_end;
//	eDebug("begin, end: %llx %llx", m_offset_begin, m_offset_end); 
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
		unsigned char block[188];
		if (m_file.read(block, 188) != 188)
		{
			eDebug("read error");
			break;
		}
		left -= 188;
		
		if (block[0] != 0x47)
		{
			int i = 0;
			while (i < 188)
			{
				if (block[i] == 0x47)
					break;
				++i;
			}
			m_file.lseek(i - 188, SEEK_CUR);
			continue;
		}
		
		int pid = ((block[1] << 8) | block[2]) & 0x1FFF;
		
		int pusi = !!(block[1] & 0x40);
		
		if (!pusi)
			continue;
		
			/* ok, now we have a PES header or section header*/
		unsigned char *sec;
		
			/* check for adaption field */
		if (block[3] & 0x20)
			sec = block + block[4] + 4 + 1;
		else
			sec = block + 4;
		
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
