#include <config.h>
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
}

eDVBTSTools::~eDVBTSTools()
{
	closeFile();
}

int eDVBTSTools::openFile(const char *filename)
{
	closeFile();
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

int eDVBTSTools::getPTS(off_t &offset, pts_t &pts)
{
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
			break;
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
			return 0;
		}
	}
	
	return -1;
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
	
	m_offset_end = lseek(m_fd, 0, SEEK_END);
	
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
	return 0;
}

int eDVBTSTools::calcBitrate()
{
	calcBegin(); calcEnd();
	if (!(m_begin_valid && m_end_valid))
		return -1;

	pts_t len_in_pts = m_pts_end - m_pts_begin;
	off_t len_in_bytes = m_offset_end - m_offset_begin;
	
	if (!len_in_pts)
		return -1;
	
	unsigned long long bitrate = len_in_bytes * 90000 * 8 / len_in_pts;
	if ((bitrate < 10000) || (bitrate > 100000000))
		return -1;
	
	return bitrate;
}
