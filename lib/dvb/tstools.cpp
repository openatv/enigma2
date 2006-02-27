#include <lib/dvb/tstools.h>
#include <lib/base/eerror.h>
#include <unistd.h>
#include <fcntl.h>

#include <stdio.h>

eDVBTSTools::eDVBTSTools()
{
	m_fd = -1;
	m_pid = -1;
	m_maxrange = 256*1024;
	
	m_begin_valid = 0;
	m_end_valid = 0;
	
	m_use_streaminfo = 0;
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
		eDebug("no recorded stream information available");
		m_use_streaminfo = 0;
	}

	m_fd = ::open(filename, O_RDONLY);
	if (m_fd < 0)
		return -1;
	return 0;
}

void eDVBTSTools::closeFile()
{
	if (m_fd >= 0)
		::close(m_fd);
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
	
	if (m_fd < 0)
		return -1;

	offset -= offset % 188;
	
		// TODO: multiple files!	
	if (lseek(m_fd, offset, SEEK_SET) < 0)
		return -1;

	int left = m_maxrange;
	
	while (left >= 188)
	{
		unsigned char block[188];
		if (read(m_fd, block, 188) != 188)
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
			offset = lseek(m_fd, i - 188, SEEK_CUR);
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
		int bitrate = calcBitrate(); /* in bits/s */
		if (bitrate <= 0)
			return -1;
		
		offset = (pts * (pts_t)bitrate) / 8ULL / 90000ULL;
		offset -= offset % 188;

		return 0;
	}
}

void eDVBTSTools::calcBegin()
{
	if (m_fd < 0)	
		return;

	if (!m_begin_valid)
	{
		m_offset_begin = 0;
		if (!getPTS(m_offset_begin, m_pts_begin))
			m_begin_valid = 1;
	}
}

void eDVBTSTools::calcEnd()
{
	if (m_fd < 0)	
		return;
	
	off_t end = lseek(m_fd, 0, SEEK_END);
	
	if (abs(end - m_offset_end) > 1*1024*1024)
	{
		m_offset_end = end;
		m_end_valid = 0;
		eDebug("file size changed, recalc length");
	}
	
	int maxiter = 10;
	
	while (!m_end_valid)
	{
		if (!--maxiter)
			return;
		
		m_offset_end -= m_maxrange;
		if (m_offset_end < 0)
			m_offset_end = 0;
		if (!getPTS(m_offset_end, m_pts_end))
			m_end_valid = 1;
		if (!m_offset_end)
			return;
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
