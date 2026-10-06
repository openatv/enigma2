#include <algorithm>
#include <cerrno>
#include <cstdio>
#include <limits>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <lib/base/rawfile.h>
#include <lib/base/eerror.h>

DEFINE_REF(eRawFile);

eRawFile::eRawFile(unsigned int packetsize)
	: iTsSource(packetsize)
	, m_lock()
	, m_fd(-1)
	, m_totallength(0)
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
	m_file_offsets.clear();
	m_totallength = 0;
	m_current_file = 0;
	m_last_offset = 0;
	m_fd = ::open(filename, O_RDONLY | O_LARGEFILE | O_CLOEXEC);
	if (m_fd >= 0)
	{
		posix_fadvise(m_fd, 0, 0, POSIX_FADV_SEQUENTIAL);
		m_file_offsets.push_back(0);
		if (scan() < 0)
		{
			int saved_errno = errno;
			close();
			errno = saved_errno;
		}
	}
	return m_fd;
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

	if (m_fd < 0 || offset < 0)
	{
		errno = m_fd < 0 ? EBADF : EINVAL;
		return -1;
	}

	count = std::min(count, static_cast<size_t>(std::numeric_limits<ssize_t>::max()));
	size_t done = 0;
	while (done < count)
	{
		// Only the current last part can grow. Discover successors at its end.
		if (offset >= m_totallength && scan() < 0)
			return done ? static_cast<ssize_t>(done) : -1;
		if (switchOffset(offset) < 0)
			return done ? static_cast<ssize_t>(done) : -1;
		if (offset >= m_totallength)
			break;

		off_t end = m_current_file + 1 < static_cast<int>(m_file_offsets.size()) ? m_file_offsets[m_current_file + 1] : m_totallength;
		size_t amount = std::min<off_t>(count - done, end - offset);
		ssize_t result;
		do
			result = ::read(m_fd, static_cast<char *>(buf) + done, amount);
		while (result < 0 && errno == EINTR);
		if (result < 0)
			return done ? static_cast<ssize_t>(done) : -1;
		if (!result)
			break;
		done += result;
		offset += result;
		m_last_offset = offset;
	}
	return done;
}

int eRawFile::valid()
{
	return m_fd != -1;
}

int eRawFile::scan()
{
	if (m_fd < 0 || m_file_offsets.empty())
	{
		errno = EBADF;
		return -1;
	}
	int last = m_file_offsets.size() - 1;
	struct stat current = {};
	if ((last == m_current_file ? ::fstat(m_fd, &current) : ::stat(_filename(last).c_str(), &current)) < 0)
		return -1;
	while (true)
	{
		if (current.st_size < 0 || current.st_size > std::numeric_limits<off_t>::max() - m_file_offsets[last])
		{
			errno = EOVERFLOW;
			return -1;
		}
		m_totallength = m_file_offsets[last] + current.st_size;
		if (last == 999) // Preserve the established base.ts through base.ts.999 limit.
			break;
		struct stat next = {};
		if (::stat(_filename(last + 1).c_str(), &next) < 0)
		{
			if (errno == ENOENT)
				break;
			return -1;
		}
		// A successor proves that its predecessor is complete. Recheck its final
		// size, since the writer may have filled it between the two stat calls.
		if ((last == m_current_file ? ::fstat(m_fd, &current) : ::stat(_filename(last).c_str(), &current)) < 0)
			return -1;
		if (current.st_size < 0 || current.st_size > std::numeric_limits<off_t>::max() - m_file_offsets[last])
		{
			errno = EOVERFLOW;
			return -1;
		}
		m_totallength = m_file_offsets[last] + current.st_size;
		m_file_offsets.push_back(m_totallength);
		++last;
		current = next;
	}
	return 0;
}

off_t eRawFile::switchOffset(off_t off)
{
	int filenr = std::upper_bound(m_file_offsets.begin(), m_file_offsets.end(), off) - m_file_offsets.begin() - 1;
	if (filenr != m_current_file)
	{
		int fd = openFileUncached(filenr);
		if (fd < 0)
			return -1;
		close();
		m_fd = fd;
		posix_fadvise(m_fd, 0, 0, POSIX_FADV_SEQUENTIAL);
		m_current_file = filenr;
		m_last_offset = m_file_offsets[filenr];
	}
	if (off != m_last_offset)
	{
		off_t position = ::lseek(m_fd, off - m_file_offsets[filenr], SEEK_SET);
		if (position < 0)
			return -1;
		m_last_offset = position + m_file_offsets[filenr];
	}
	return m_last_offset;
}

std::string eRawFile::_filename(int nr) const
{
	std::string filename = m_basename;
	if (nr)
	{
		char suffix[16];
		snprintf(suffix, sizeof(suffix), ".%03d", nr);
		filename += suffix;
	}
	return filename;
}

int eRawFile::openFileUncached(int nr)
{
	return ::open(_filename(nr).c_str(), O_RDONLY | O_LARGEFILE | O_CLOEXEC);
}

off_t eRawFile::length()
{
	eSingleLocker l(m_lock);
	return scan() < 0 ? -1 : m_totallength;
}

off_t eRawFile::offset()
{
	return m_last_offset;
}
