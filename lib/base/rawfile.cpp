#include <cstdio>
#include <unistd.h>
#include <fcntl.h>
#include <lib/base/rawfile.h>
#include <lib/base/eerror.h>

DEFINE_REF(eRawFile);

eRawFile::eRawFile(unsigned int packetsize)
	: iTsSource(packetsize)
	, m_lock()
	, m_fd(-1)
	, m_nrfiles(0)
	, m_splitsize(0)
	, m_totallength(0)
	, m_current_offset(0)
	, m_base_offset(0)
	, m_last_offset(0)
	, m_current_file(0)
{
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
	m_fd = ::open(filename, O_RDONLY | O_LARGEFILE | O_CLOEXEC);
	posix_fadvise(m_fd, 0, 0, POSIX_FADV_SEQUENTIAL);
	return m_fd;
}

off_t eRawFile::lseek_internal(off_t offset)
{
//	eDebug("[eRawFile] lseek: %lld, %d", offset, whence);
		/* if there is only one file, use the native lseek - the file could be growing! */
	if (m_nrfiles < 2)
	{
		return ::lseek(m_fd, offset, SEEK_SET);
	}
	m_current_offset = offset;
	return m_current_offset;
}

int eRawFile::close()
{
	int ret = 0;
	if (m_fd >= 0)
	{
		posix_fadvise(m_fd, 0, 0, POSIX_FADV_DONTNEED);
		ret = ::close(m_fd);
		m_fd = -1;
	}
	return ret;
}

ssize_t eRawFile::read(off_t offset, void *buf, size_t count)
{
	eSingleLocker l(m_lock);

	if (offset != m_current_offset)
	{
		m_current_offset = lseek_internal(offset);
		if (m_current_offset < 0)
			return m_current_offset;
	}

	switchOffset(m_current_offset);

	if (m_nrfiles >= 2)
	{
		if (m_current_offset + count > m_totallength)
			count = m_totallength - m_current_offset;
		if (count < 0)
			return 0;
	}

	int ret;

	ret = ::read(m_fd, buf, count);

	if (ret > 0)
	{
		m_current_offset = m_last_offset += ret;
	}
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
		int f = openFileUncached(m_nrfiles);
		if (f < 0)
			break;
		if (!m_nrfiles)
			m_splitsize = ::lseek(f, 0, SEEK_END);
		m_totallength += ::lseek(f, 0, SEEK_END);
		::close(f);
		++m_nrfiles;
	}
//	eDebug("[eRawFile] found %d files, splitsize: %llx, totallength: %llx", m_nrfiles, m_splitsize, m_totallength);
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
//			eDebug("[eRawFile] -> %d", filenr);
			close();
			m_fd = openFileUncached(filenr);
			m_last_offset = m_base_offset = m_splitsize * filenr;
			m_current_file = filenr;
		}
	} else
		m_base_offset = 0;

	if (off != m_last_offset)
	{
		m_last_offset = ::lseek(m_fd, off - m_base_offset, SEEK_SET) + m_base_offset;
		return m_last_offset;
	} else
	{
		return m_last_offset;
	}
}

int eRawFile::openFileUncached(int nr)
{
	std::string filename = m_basename;
	if (nr)
	{
		char suffix[5];
		snprintf(suffix, 5, ".%03d", nr);
		filename += suffix;
	}
	return ::open(filename.c_str(), O_RDONLY | O_LARGEFILE | O_CLOEXEC);
}

off_t eRawFile::length()
{
	if (m_nrfiles >= 2)
	{
		return m_totallength;
	}
	else
	{
		struct stat st;
		if (::fstat(m_fd, &st) < 0)
			return -1;
		return st.st_size;
	}
}

off_t eRawFile::offset()
{
	return m_last_offset;
}
