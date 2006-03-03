#include <unistd.h>
#include <fcntl.h>
#include <lib/base/rawfile.h>
#include <lib/base/eerror.h>

eRawFile::eRawFile()
{
	m_fd = -1;
	m_splitsize = 0;
	m_totallength = 0;
	m_current_offset = 0;
	m_base_offset = 0;
	m_last_offset = 0;
	m_nrfiles = 0;
	m_current_file = 0;
}

eRawFile::~eRawFile()
{
	close();
}

int eRawFile::open(const char *filename)
{
	close();
	m_basename = filename;
	scan();
	m_current_offset = 0;
	m_last_offset = 0;
	m_fd = ::open(filename, O_RDONLY | O_LARGEFILE);
	return m_fd;
}

void eRawFile::setfd(int fd)
{
	close();
	m_nrfiles = 1;
	m_fd = fd;
}

off_t eRawFile::lseek(off_t offset, int whence)
{
//	eDebug("lseek: %lld, %d", offset, whence);
		/* if there is only one file, use the native lseek - the file could be growing! */
	if (m_nrfiles < 2)
		return ::lseek(m_fd, offset, whence);
	switch (whence)
	{
	case SEEK_SET:
		m_current_offset = offset;
		break;
	case SEEK_CUR:
		m_current_offset += offset;
		break;
	case SEEK_END:
		m_current_offset = m_totallength + offset;
		break;
	}

	if (m_current_offset < 0)
		m_current_offset = 0;
	return m_current_offset;
}

int eRawFile::close()
{
	int ret = ::close(m_fd);
	m_fd = -1;
	return ret;
}

ssize_t eRawFile::read(void *buf, size_t count)
{
//	eDebug("read: %p, %d", buf, count);
	switchOffset(m_current_offset);
	
	if (m_nrfiles >= 2)
	{
		if (m_current_offset + count > m_totallength)
			count = m_totallength - m_current_offset;
		if (count < 0)
			return 0;
	}
	
	int ret = ::read(m_fd, buf, count);
	if (ret > 0)
		m_current_offset = m_last_offset += ret;
	return ret;
}

int eRawFile::valid()
{
	return m_fd != -1;
}

void eRawFile::scan()
{
	m_nrfiles = 0;
	m_totallength = 0;
	while (m_nrfiles < 1000) /* .999 is the last possible */
	{
		int f = openFile(m_nrfiles);
		if (f < 0)
			break;
		if (!m_nrfiles)
			m_splitsize = ::lseek(f, 0, SEEK_END);
		m_totallength += ::lseek(f, 0, SEEK_END);
		::close(f);
		
		++m_nrfiles;
	}
//	eDebug("found %d files, splitsize: %llx, totallength: %llx", m_nrfiles, m_splitsize, m_totallength);
}

int eRawFile::switchOffset(off_t off)
{
	if (m_splitsize)
	{
		int filenr = off / m_splitsize;
		if (filenr >= m_nrfiles)
			filenr = m_nrfiles - 1;
		if (filenr != m_current_file)
		{	
//			eDebug("-> %d", filenr);
			close();
			m_fd = openFile(filenr);
			m_last_offset = m_base_offset = m_splitsize * filenr;
			m_current_file = filenr;
		}
	} else
		m_base_offset = 0;
	
	if (off != m_last_offset)
	{
//		eDebug("%llx != %llx", off, m_last_offset);
		m_last_offset = ::lseek(m_fd, off - m_base_offset, SEEK_SET) + m_base_offset;
//		eDebug("offset now %llx", m_last_offset);
		return m_last_offset;
	} else
	{
//		eDebug("offset already ok");
		return m_last_offset;
	}
}

int eRawFile::openFile(int nr)
{
	std::string filename = m_basename;
	if (nr)
	{
		char suffix[5];
		snprintf(suffix, 5, ".%03d", nr);
		filename += suffix;
	}
	return ::open(filename.c_str(), O_RDONLY);
}
