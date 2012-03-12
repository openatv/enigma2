#include <lib/dvb/pvrparse.h>
#include <lib/base/eerror.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <byteswap.h>
#include <sys/mman.h>

#ifndef BYTE_ORDER
#	error no byte order defined!
#endif

#ifndef PAGESIZE
#	define PAGESIZE 4096
#endif
#define ROUND_TO_PAGESIZE(value) ((value) & 0xFFFFF000)
#define MAPSIZE (PAGESIZE*8)

eMPEGStreamInformation::eMPEGStreamInformation():
	m_structure_read_fd(-1),
	m_cache_index(-1),
	m_current_entry(-1),
	m_structure_cache_entries(0),
	m_structure_file_entries(0),
	m_structure_cache(NULL),
	m_streamtime_accesspoints(false)
{
}

eMPEGStreamInformation::~eMPEGStreamInformation()
{
	close();
}

void eMPEGStreamInformation::close()
{
	if (m_structure_read_fd >= 0)
	{
		if (m_structure_cache != NULL)
		{
			//eDebug("[eMPEGStreamInformation] {%d} close - unmap %p size %d", gettid(), m_structure_cache, m_structure_cache_entries * 16);
			::munmap(m_structure_cache, m_structure_cache_entries * 16);
			m_structure_cache = NULL;
		}
		::close(m_structure_read_fd);
		m_structure_cache_entries = 0;
		m_cache_index = -1;
		m_structure_read_fd = -1;
		m_structure_file_entries = 0;
	}
}

int eMPEGStreamInformation::load(const char *filename)
{
	//eDebug("[eMPEGStreamInformation] {%d} load(%s)", gettid(), filename);
	close();
	std::string s_filename(filename);
	m_structure_read_fd = ::open((s_filename + ".sc").c_str(), O_RDONLY);
	m_access_points.clear();
	m_pts_to_offset.clear();
	m_timestamp_deltas.clear();
	FILE *f = fopen((s_filename + ".ap").c_str(), "rb");
	if (!f)
		return -1;
	while (1)
	{
		unsigned long long d[2];
		if (fread(d, sizeof(d), 1, f) < 1)
			break;
		d[0] = be64toh(d[0]);
		d[1] = be64toh(d[1]);
		m_access_points[d[0]] = d[1];
		m_pts_to_offset.insert(std::pair<pts_t,off_t>(d[1], d[0]));
	}
	fclose(f);
	/* assume the accesspoints are in streamtime, if they start with a 0 timestamp */
	m_streamtime_accesspoints = (!m_access_points.empty() && m_access_points.begin()->second == 0);
	fixupDiscontinuties();
	return 0;
}

void eMPEGStreamInformation::fixupDiscontinuties()
{
	if (m_access_points.empty())
		return;
		/* if we have no delta at the beginning, extrapolate it */
	if ((m_access_points.find(0) == m_access_points.end()) && (m_access_points.size() > 1))
	{
		std::map<off_t,pts_t>::const_iterator second = m_access_points.begin();
		std::map<off_t,pts_t>::const_iterator first  = second++;
		if (first->first < second->first) /* i.e., not equal or broken */
		{
			off_t diff = second->first - first->first;
			pts_t tdiff = second->second - first->second;
			tdiff *= first->first;
			tdiff /= diff;
			m_timestamp_deltas[0] = first->second - tdiff;
//			eDebug("first delta is %08llx", first->second - tdiff);
		}
	}

	if (m_timestamp_deltas.empty())
		m_timestamp_deltas[m_access_points.begin()->first] = m_access_points.begin()->second;

	pts_t currentDelta = m_timestamp_deltas.begin()->second, lastpts_t = 0;
	for (std::map<off_t,pts_t>::const_iterator i(m_access_points.begin()); i != m_access_points.end(); ++i)
	{
		pts_t current = i->second - currentDelta;
		pts_t diff = current - lastpts_t;
		
		if (llabs(diff) > (90000*10)) // 10sec diff
		{
//			eDebug("%llx < %llx, have discont. new timestamp is %llx (diff is %llx)!", current, lastpts_t, i->second, diff);
			currentDelta = i->second - lastpts_t; /* FIXME: should be the extrapolated new timestamp, based on the current rate */
//			eDebug("current delta now %llx, making current to %llx", currentDelta, i->second - currentDelta);
			m_timestamp_deltas[i->first] = currentDelta;
		}
		lastpts_t = i->second - currentDelta;
	}
}

pts_t eMPEGStreamInformation::getDelta(off_t offset)
{
	if (!m_timestamp_deltas.size())
		return 0;
	std::map<off_t,pts_t>::iterator i = m_timestamp_deltas.upper_bound(offset);
	/* i can be the first when you query for something before the first PTS */
	if (i != m_timestamp_deltas.begin())
		--i;
	return i->second;
}

// fixupPTS is apparently called to get UI time information and such
int eMPEGStreamInformation::fixupPTS(const off_t &offset, pts_t &ts)
{
	//eDebug("eMPEGStreamInformation::fixupPTS(offset=%llu pts=%llu)", offset, ts);
	if (m_streamtime_accesspoints)
	{
		/*
		 * The access points are measured in stream time, rather than actual mpeg pts.
		 * Overrule the timestamp with the nearest access point pts. 
		 */
		off_t nearestoffset = offset;
		getPTS(nearestoffset, ts);
		return 0;
	}
	if (m_timestamp_deltas.empty())
		return -1;

	std::multimap<pts_t, off_t>::const_iterator 
		l = m_pts_to_offset.upper_bound(ts - 60 * 90000), 
		u = m_pts_to_offset.upper_bound(ts + 60 * 90000), 
		nearest = m_pts_to_offset.end();

	while (l != u)
	{
		if ((nearest == m_pts_to_offset.end()) || (llabs(l->first - ts) < llabs(nearest->first - ts)))
			nearest = l;
		++l;
	}
	if (nearest == m_pts_to_offset.end())
		return 1;

	ts -= getDelta(nearest->second);

	return 0;
}

// getPTS is typically called when you "jump" in a file.
int eMPEGStreamInformation::getPTS(off_t &offset, pts_t &pts)
{
	//eDebug("[eMPEGStreamInformation] {%d} getPTS(offset=%llu, pts=%llu)", gettid(), offset, pts);
	std::map<off_t,pts_t>::iterator before = m_access_points.lower_bound(offset);

		/* usually, we prefer the AP before the given offset. however if there is none, we take any. */
	if (before != m_access_points.begin())
		--before;
	
	if (before == m_access_points.end())
	{
		pts = 0;
		return -1;
	}
	
	offset = before->first;
	pts = before->second - getDelta(offset);
	
	return 0;
}

pts_t eMPEGStreamInformation::getInterpolated(off_t offset)
{
		/* get the PTS values before and after the offset. */
	std::map<off_t,pts_t>::iterator before, after;
	after = m_access_points.upper_bound(offset);
	before = after;

	if (before != m_access_points.begin())
		--before;
	else	/* we query before the first known timestamp ... FIXME */
		return 0;

		/* empty... */
	if (before == m_access_points.end())
		return 0;

		/* if after == end, then we need to extrapolate ... FIXME */
	if ((before->first == offset) || (after == m_access_points.end()))
		return before->second - getDelta(offset);
	
	pts_t before_ts = before->second - getDelta(before->first);
	pts_t after_ts = after->second - getDelta(after->first);
	
//	eDebug("%08llx .. ? .. %08llx", before_ts, after_ts);
//	eDebug("%08llx .. %08llx .. %08llx", before->first, offset, after->first);
	
	pts_t diff = after_ts - before_ts;
	off_t diff_off = after->first - before->first;
	
	diff = (offset - before->first) * diff / diff_off;
//	eDebug("%08llx .. %08llx .. %08llx", before_ts, before_ts + diff, after_ts);
	return before_ts + diff;
}
 
off_t eMPEGStreamInformation::getAccessPoint(pts_t ts, int marg)
{
	//eDebug("eMPEGStreamInformation::getAccessPoint(ts=%llu, marg=%d)", ts, marg);
		/* FIXME: more efficient implementation */
	off_t last = 0;
	off_t last2 = 0;
	ts += 1; // Add rounding error margin
	for (std::map<off_t, pts_t>::const_iterator i(m_access_points.begin()); i != m_access_points.end(); ++i)
	{
		pts_t delta = getDelta(i->first);
		pts_t c = i->second - delta;
		if (c > ts) {
			if (marg > 0)
				return (last + i->first)/376*188;
			else if (marg < 0)
				return (last + last2)/376*188;
			else
				return last;
		}
		last2 = last;
		last = i->first;
	}
	if (marg < 0)
		return (last + last2)/376*188;
	else
		return last;
}

int eMPEGStreamInformation::getNextAccessPoint(pts_t &ts, const pts_t &start, int direction)
{
	if (m_access_points.empty())
	{
		eDebug("can't get next access point without streaminfo (yet)");
		return -1;
	}
	off_t offset = getAccessPoint(start);
	std::map<off_t, pts_t>::const_iterator i = m_access_points.find(offset);
	if (i == m_access_points.end())
	{
		eDebug("getNextAccessPoint: initial AP not found");
		return -1;
	}
	pts_t c1 = i->second - getDelta(i->first);
	while (direction)
	{
		while (direction > 0)
		{
			if (i == m_access_points.end())
				return -1;
			++i;
			pts_t c2 = i->second - getDelta(i->first);
			if (c1 == c2) { // Discontinuity
				++i;
				c2 = i->second - getDelta(i->first);
			}
			c1 = c2;
			direction--;
		}
		while (direction < 0)
		{
			if (i == m_access_points.begin())
			{
				eDebug("getNextAccessPoint at start");
				return -1;
			}
			--i;
			pts_t c2 = i->second - getDelta(i->first);
			if (c1 == c2) { // Discontinuity
				--i;
				c2 = i->second - getDelta(i->first);
			}
			c1 = c2;
			direction++;
		}
	}
	ts = i->second - getDelta(i->first);
	eDebug("getNextAccessPoint fine, at %lld - %lld = %lld", ts, i->second, getDelta(i->first));
	return 0;
}

#define structureCacheOffset(i) ((off_t)be64toh(m_structure_cache[(i)*2]))
#define structureCacheData(i) ((off_t)be64toh(m_structure_cache[(i)*2+1]))

static const int entry_size = 16;

int eMPEGStreamInformation::moveCache(int index)
{
	//eDebug("[eMPEGStreamInformation::moveCache] index=%d m_cache_index=%d m_structure_cache_entries=%d", index, m_cache_index, m_structure_cache_entries);
	// Check if index falls inside current range.
	if ((m_structure_cache_entries != 0) && (index >= m_cache_index) && (index < m_cache_index + m_structure_cache_entries))
	{
		// Request for the same data. If the request is at the end of the stream,
		// check if the file has become larger.
		if (index + m_structure_cache_entries >= m_structure_file_entries)
		{
			int l = ::lseek(m_structure_read_fd, 0, SEEK_END) / entry_size;
			if (l == m_structure_file_entries)
			{
				// No change to file, just return
				return m_structure_cache_entries;
			}
			m_structure_file_entries = l;
		}
		else
		{
			// Requested same position as last time, just return
			return m_structure_cache_entries;
		}
	}
	// Really have to re-read the cache now
	return loadCache(index);
}

// Page size is 4k, entry size is 16. To round it down, (((value*16)/PAGESIZE)*PAGESIZE)/16

int eMPEGStreamInformation::loadCache(int index)
{
	//eDebug("[eMPEGStreamInformation::loadCache] index=%d", index);
	if (m_structure_cache != NULL)
	{
		//eDebug("[eMPEGStreamInformation] munmap %p size %d index %d", m_structure_cache, m_structure_cache_entries * entry_size, m_cache_index);
		::munmap(m_structure_cache, m_structure_cache_entries * entry_size);
		m_structure_cache = NULL;
		m_structure_cache_entries = 0;
		m_cache_index = -1;
	}
	off_t where = ROUND_TO_PAGESIZE(index * entry_size);
	off_t until = ::lseek(m_structure_read_fd, 0, SEEK_END);
	size_t bytes;
	if (where + MAPSIZE <= until)
	{
		bytes = MAPSIZE;
	}
	else
	{
		if (index * entry_size >= until)
		{
			eDebug("[eMPEGStreamInformation] index %d is past EOF", index);
			return 0;
		}
		bytes = (size_t)(until-where);
		if (bytes == 0)
		{
			eDebug("[eMPEGStreamInformation] mmap file is empty");
			return 0;
		}
	}
	//eDebug("[eMPEGStreamInformation] mmap offset=%lld size %d", where, bytes);
	m_structure_cache = (unsigned long long*) ::mmap(NULL, bytes, PROT_READ, MAP_SHARED, m_structure_read_fd, where);
	if (m_structure_cache == NULL)
	{
		eDebug("[eMPEGStreamInformation] failed to mmap cache: %m");
		m_cache_index = -1;
		m_structure_cache_entries = 0;
		return -1;
	}
	m_cache_index = (int)(where / entry_size);
	//eDebug("[eMPEGStreamInformation] cache index %d starts at %d (%lld) bytes: %d", index, m_cache_index, where, bytes);
	int num = (int)bytes / entry_size;
	m_structure_cache_entries = num;
	return num;
}

int eMPEGStreamInformation::getStructureEntryFirst(off_t &offset, unsigned long long &data)
{
	//eDebug("[eMPEGStreamInformation] {%d} getStructureEntryFirst(offset=%llu)", gettid(), offset);
	if (m_structure_read_fd < 0)
	{
		eDebug("getStructureEntryFirst failed because of no m_structure_read_fd");
		return -1;
	}

	if ((m_structure_cache_entries == 0) ||
	    (structureCacheOffset(0) > offset) ||
	    (structureCacheOffset(m_structure_cache_entries - 1) <= offset))
	{
		int l = ::lseek(m_structure_read_fd, 0, SEEK_END) / entry_size;
		if (l == 0)
		{
			eDebug("getStructureEntryFirst failed because file size is zero");
			return -1;
		}
		m_structure_file_entries = l;

		/* do a binary search */
		int count = l;
		int i = 0;
		const int structure_cache_size = MAPSIZE / entry_size;
		while (count > (structure_cache_size/4))
		{
			int step = count >> 1;
			::lseek(m_structure_read_fd, (i + step) * entry_size, SEEK_SET);
			unsigned long long d;
			if (::read(m_structure_read_fd, &d, sizeof(d)) < (ssize_t)sizeof(d))
			{
				eDebug("getStructureEntryFirst read error at entry %d", i+step);
				return -1;
			}
			d = be64toh(d);
			if (d < (unsigned long long)offset)
			{
				i += step + 1;
				count -= step + 1;
			} else
				count = step;
		}
		//eDebug("[eMPEGStreamInformation] getStructureEntryFirst i=%d size=%d count=%d", i, l, count);

		if (i + structure_cache_size > l)
		{
			i = l - structure_cache_size; // Near end of file, just fetch the last
		}
		if (i < 0)
			i = 0;
		int num = moveCache(i);
		if ((num < structure_cache_size) && (structureCacheOffset(num - 1) <= offset))
		{
			eDebug("[eMPEGStreamInformation] offset %lld is past EOF of structure file", offset);
			data = 0;
			return 1;
		}
	}

	// Binary search for offset
	int i = 0;
	int low = 0;
	int high = m_structure_cache_entries - 1;
	while (low <= high)
	{
		int mid = (low + high) / 2;
		off_t value = structureCacheOffset(mid);
		if (value <= offset)
			low = mid + 1;
		else
			high = mid - 1;
	}
	// Note that low > high
	if (high >= 0)
		i = high;
	else
		i = 0;
	offset = structureCacheOffset(i);
	data = structureCacheData(i);
	m_current_entry = m_cache_index + i;
	//eDebug("[eMPEGStreamInformation] first index=%d (%d); %llu: %llu", m_current_entry, i, offset, data);
	return 0;
}

int eMPEGStreamInformation::getStructureEntryNext(off_t &offset, unsigned long long &data, int delta)
{
	//eDebug("[eMPEGStreamInformation] {%d} getStructureEntryNext(offset=%llu, delta=%d)", gettid(), offset, delta);
	int next = m_current_entry + delta;
	if (next < 0)
	{
		eDebug("getStructureEntryNext before start-of-file");
		return -1;
	}
	int index = next - m_cache_index;
	if ((index < 0) || (index >= m_structure_cache_entries))
	{
		// Moved outsize cache range, fetch a new array
		int where;
		if (delta < 0)
		{
			// When moving backwards, take a bigger step back (but we will probably be moving forward later...)
			const int structure_cache_size = MAPSIZE / entry_size;
			where = next - structure_cache_size/2;
			if (where < 0)
				where = 0;
		}
		else
		{
			where = next;
		}
		int num = moveCache(where);
		if (num <= 0)
		{
			eDebug("getStructureEntryNext failed, no data");
			return -1;
		}
		index = next - m_cache_index;
		//eDebug("[getStructureEntryNext] Moved outside cache, next=%d delta=%d cache=%d index=+%d", next, delta, m_cache_index, index);
	}
	offset = structureCacheOffset(index);
	data = structureCacheData(index);
	m_current_entry = m_cache_index + index;
	//eDebug("[eMPEGStreamInformation] next index=%d (%d); %llu: %llu", m_current_entry, index, offset, data);
	return 0;
}

// Get first or last PTS value and offset.
int eMPEGStreamInformation::getFirstFrame(off_t &offset, pts_t& pts)
{
	//eDebug("{%d} eMPEGStreamInformation::getFirstFrame", gettid());
	std::map<off_t,pts_t>::const_iterator entry = m_access_points.begin();
	if (entry != m_access_points.end())
	{
		offset = entry->first;
		pts = entry->second;
		return 0;
	}
	// No access points (yet?) use the .sc data instead
	if (m_structure_read_fd >= 0)
	{
		int num = moveCache(0);
		if (num <= 0)
		{
			eDebug("eMPEGStreamInformation::getFirstFrame - no data (yet?)");
			offset = 0;
			pts = 0;
			return 1;
		}
		if (num > 20) num = 20; // We don't need to look that hard, it may be an old file without PTS data
		for (int i = 0; i < num; ++i)
		{
			unsigned long long data = structureCacheData(i);
			if ((data & 0x1000000) != 0)
			{
				pts = data >> 31;
				offset = structureCacheOffset(i);
				return 0;
			}
		}
	}
	return -1;
}
int eMPEGStreamInformation::getLastFrame(off_t &offset, pts_t& pts)
{
	//eDebug("{%d} eMPEGStreamInformation::getLastFrame", gettid());
	std::map<off_t,pts_t>::const_reverse_iterator entry = m_access_points.rbegin();
	if (entry != m_access_points.rend())
	{
		offset = entry->first;
		pts = entry->second;
		return 0;
	}
	// No access points (yet?) use the .sc data instead
	if (m_structure_read_fd >= 0)
	{
		int l = ::lseek(m_structure_read_fd, 0, SEEK_END) / entry_size;
		if (l <= 0)
		{
			eDebug("eMPEGStreamInformation::getLastFrame - no data (yet?)");
			offset = 0;
			pts = 0;
			return 1;
		}
		
		int index = l - 1;
		if (index < 0)
			index = 0;
		
		int num = moveCache(index);
		if (num <= 0)
		{
			eDebug("eMPEGStreamInformation::getLastFrame - no data in sc file");
			return -1;
		}
		// binary search for "real" end
		int last = num - 1;
		int first = 0;
		while (first <= last)
		{
			int mid = (first + last) / 2;
			if (structureCacheOffset(mid) != 0x7fffFFFFffffFFFFll)
			{
				first = mid + 1;
			}
			else
			{
				last = mid - 1;
			}
		}
		// Search 10 items for a timestamp
		if (last > 10)
			first = last - 10;
		else
			first = 0;
		for (int i = last; i >= first; --i)
		{
			unsigned long long data = structureCacheData(i);
			if ((data & 0x1000000) != 0)
			{
				pts = data >> 31;
				offset = structureCacheOffset(i);
				return 0;
			}
		}
	}
	return -1;
}

eMPEGStreamInformationWriter::eMPEGStreamInformationWriter():
	m_structure_write_fd(-1),
	m_structure_pos(0),
	m_write_buffer(NULL),
	m_buffer_filled(0)
{}

eMPEGStreamInformationWriter::~eMPEGStreamInformationWriter()
{
	close();
}

int eMPEGStreamInformationWriter::startSave(const std::string& filename)
{
	m_filename = filename;
	m_structure_write_fd = ::open((m_filename + ".sc").c_str(), O_RDWR | O_CREAT | O_TRUNC, 0644);
	m_buffer_filled = 0;
	m_write_buffer = NULL;
	return 0;
}

int eMPEGStreamInformationWriter::stopSave(void)
{
	close();
	if (m_filename.empty())
		return 1;
	// No access points at all, then don't save a file. A single initial
	// streamtime accesspoint is also useless, hence the <=1 instead of empty()
	if (m_access_points.empty() && (m_streamtime_access_points.size() <= 1))
		// Nothing to save, don't create an ap file at all
		return 1;
	FILE *f = fopen((m_filename + ".ap").c_str(), "wb");
	if (!f)
		return -1;
	for (std::deque<AccessPoint>::const_iterator i(m_streamtime_access_points.begin()); i != m_streamtime_access_points.end(); ++i)
	{
		unsigned long long d[2];
		d[0] = htobe64(i->off);
		d[1] = htobe64(i->pts);
		fwrite(d, sizeof(d), 1, f);
	}
	for (std::deque<AccessPoint>::const_iterator i(m_access_points.begin()); i != m_access_points.end(); ++i)
	{
		unsigned long long d[2];
		d[0] = htobe64(i->off);
		d[1] = htobe64(i->pts);
		fwrite(d, sizeof(d), 1, f);
	}
	fclose(f);
	return 0;
}

void eMPEGStreamInformationWriter::addAccessPoint(off_t offset, pts_t pts, bool streamtime)
{
	if (streamtime)
	{
		m_streamtime_access_points.push_back(AccessPoint(offset, pts));
	}
	else
	{
		/* 
		 * We've got real pts now, drop the leading 'extrapolated' accesspoints,
		 * avoid unnecessary pts discontinuity 
		 */
		m_streamtime_access_points.clear();
		m_access_points.push_back(AccessPoint(offset, pts));
	}
}

void eMPEGStreamInformationWriter::writeStructureEntry(off_t offset, unsigned long long data)
{
	if (m_structure_write_fd >= 0)
	{
		if (m_write_buffer == NULL)
		{
			m_write_buffer = malloc(PAGESIZE);
			m_buffer_filled = 0;
			if (m_write_buffer == NULL)
			{
				eWarning("malloc fail");
				return;
			}
		}
		unsigned long long *d = (unsigned long long*)((char*)m_write_buffer + m_buffer_filled);
		d[0] = htobe64(offset);
		d[1] = htobe64(data);
		m_buffer_filled += 16;
		if (m_buffer_filled == PAGESIZE)
			commit();
	}
}

eMPEGStreamInformationWriter::PendingWrite::PendingWrite():
	m_buffer(NULL) // empty constructor because deque will make a COPY first.
{
}

int eMPEGStreamInformationWriter::PendingWrite::start(int fd, off_t where, void* buffer, size_t buffer_size)
{
	m_buffer = buffer; // Note: We take ownership of the buffer!
	memset(&m_aio, 0, sizeof(m_aio));
	m_aio.aio_fildes = fd;
	m_aio.aio_nbytes = buffer_size;
	m_aio.aio_offset = where;
	m_aio.aio_buf = buffer;
	int r = aio_write(&m_aio);
	if (r < 0)
	{
		eDebug("[eMPEGStreamInformationWriter] aio_write returned failure: %m");
	}
	return r;
}

eMPEGStreamInformationWriter::PendingWrite::~PendingWrite()
{
	if (m_buffer != NULL)
	{
		wait();
		free(m_buffer);
	}
}

int eMPEGStreamInformationWriter::PendingWrite::wait()
{
	//eDebug("[eMPEGStreamInformationWriter] PendingWrite waiting for IO completion");
	struct aiocb* aio = &m_aio;
	while (aio_error(aio) == EINPROGRESS)
	{
		eDebug("[eMPEGStreamInformationWriter] Waiting for I/O to complete");
		int r = aio_suspend(&aio, 1, NULL);
		if (r < 0)
		{
			eDebug("[eMPEGStreamInformationWriter] aio_suspend failed: %m");
			return -1;
		}
	}
	int r = aio_return(aio);
	if (r < 0)
	{
		eDebug("[eMPEGStreamInformationWriter] aio_return returned failure: %m");
	}
	return r;
}

bool eMPEGStreamInformationWriter::PendingWrite::poll()
{
	if (m_buffer == NULL)
		return true; // Nothing pending
	if (aio_error(&m_aio) == EINPROGRESS)
	{
		return false; // still busy
	}
	int r = aio_return(&m_aio);
	if (r < 0)
	{
		eDebug("[eDVBRecordFileThread] aio_return returned failure: %m");
	}
	free(m_buffer);
	m_buffer = NULL;
	return true;
}

void eMPEGStreamInformationWriter::commit()
{
	std::deque<PendingWrite>::iterator head = m_pending_writes.begin();
	while (head != m_pending_writes.end())
	{
		if (!head->poll())
		{
			// Not ready yet, stop polling
			break;
		}
		else
		{
			// head is done remove it from the queue
			m_pending_writes.pop_front();
			head = m_pending_writes.begin();
		}
	}
	if (m_write_buffer != NULL)
	{
		m_pending_writes.push_back(PendingWrite()); // calls copy constructor, so don't initialize it
		m_pending_writes.back().start(m_structure_write_fd, m_structure_pos, m_write_buffer, m_buffer_filled);
		m_structure_pos += m_buffer_filled;
		m_write_buffer = NULL;
		m_buffer_filled = 0;
	}
}


void eMPEGStreamInformationWriter::close()
{
	if (m_structure_write_fd != -1)
	{
		commit();
		m_pending_writes.clear(); // this waits for all IO to complete
		::close(m_structure_write_fd);
		m_structure_write_fd = -1;
		if ((m_structure_pos == 0) && !m_filename.empty())
		{
			// If the file is empty, attempt to delete it.
			::unlink((m_filename + ".sc").c_str());
		}
	}
}


eMPEGStreamParserTS::eMPEGStreamParserTS(int packetsize):
	m_pktptr(0),
	m_pid(-1),
	m_streamtype(-1),
	m_need_next_packet(0),
	m_skip(0),
	m_last_pts_valid(0),
	m_last_pts(0),
	m_packetsize(packetsize),
	m_header_offset(packetsize - 188),
	m_enable_accesspoints(true),
	m_pts_found(false),
	m_has_accesspoints(false)
{
}

int eMPEGStreamParserTS::processPacket(const unsigned char *pkt, off_t offset)
{
	if (!m_has_accesspoints && m_enable_accesspoints)
	{
		/* initial stream time access point: 0,0 */
		addAccessPoint(offset, m_last_pts, !m_pts_found);
	}
	if (!wantPacket(pkt))
		eWarning("something's wrong.");

	pkt += m_header_offset;

	if (!(pkt[3] & 0x10)) return 0; /* do not process packets without payload */

	bool pusi = (pkt[1] & 0x40) != 0;

	if (pkt[3] & 0xc0) 
	{
		/* scrambled stream, we cannot parse pts, extrapolate with measured stream time instead */
		if (pusi && m_enable_accesspoints)
		{
			timespec now, diff;
			clock_gettime(CLOCK_MONOTONIC, &now);
			diff = now - m_last_access_point;
			/* limit the number of extrapolated access points to one per second */
			if (diff.tv_sec)
			{
				m_last_pts += diff.tv_sec * 90000L;
				m_last_pts += diff.tv_nsec / 11111L;
				m_last_pts_valid = 1;
				addAccessPoint(offset, m_last_pts, now, !m_pts_found);
			}
		}
		return 0;
	}

	const unsigned char *end = pkt + 188;
	const unsigned char *begin = pkt;

	if (pkt[3] & 0x20) // adaptation field present?
		pkt += pkt[4] + 4 + 1;  /* skip adaptation field and header */
	else
		pkt += 4; /* skip header */

	if (pkt > end)
	{
		eWarning("[TSPARSE] dropping huge adaption field");
		return 0;
	}

	pts_t pts = 0;
	int ptsvalid = 0;
	
	if (pusi)
	{
			// ok, we now have the start of the payload, aligned with the PES packet start.
		if (pkt[0] || pkt[1] || (pkt[2] != 1))
		{
			eWarning("broken startcode");
			return 0;
		}

		if (pkt[7] & 0x80) // PTS present?
		{
			pts  = ((unsigned long long)(pkt[ 9]&0xE))  << 29;
			pts |= ((unsigned long long)(pkt[10]&0xFF)) << 22;
			pts |= ((unsigned long long)(pkt[11]&0xFE)) << 14;
			pts |= ((unsigned long long)(pkt[12]&0xFF)) << 7;
			pts |= ((unsigned long long)(pkt[13]&0xFE)) >> 1;
			ptsvalid = 1;
			
			m_last_pts = pts;
			m_last_pts_valid = 1;
			m_pts_found = true;
		}
		
			/* advance to payload */
		pkt += pkt[8] + 9;
	}

	while (pkt < (end-4))
	{
		int pkt_offset = pkt - begin;
		if (!(pkt[0] || pkt[1] || (pkt[2] != 1)))
		{
//			 ("SC %02x %02x %02x %02x, %02x", pkt[0], pkt[1], pkt[2], pkt[3], pkt[4]);
			unsigned int sc = pkt[3];
			
			if (m_streamtype == 0) /* mpeg2 */
			{
				if ((sc == 0x00) || (sc == 0xb3) || (sc == 0xb8)) /* picture, sequence, group start code */
				{
					if ((sc == 0xb3) && m_enable_accesspoints) /* sequence header */
					{
						if (ptsvalid)
						{
							addAccessPoint(offset, pts);
							//eDebug("Sequence header at %llx, pts %llx", offset, pts);
						}
					}
					if (pkt <= (end - 6))
					{
						unsigned long long data = sc | ((unsigned)pkt[4] << 8) | ((unsigned)pkt[5] << 16);
						if (ptsvalid) // If available, add timestamp data as well. PTS = 33 bits
							data |= (pts << 31) | 0x1000000;
						writeStructureEntry(offset + pkt_offset, data);
					}
					else
					{
						// Returning non-zero suggests we need more data. This does not
						// work, and never has, so we should make this a void function
						// or fix that...
						return 1;
					}
				}
			}
			else if (m_streamtype == 1) /* H.264 */
			{
				if (sc == 0x09)
				{
					/* store image type */
					unsigned long long data = sc | (pkt[4] << 8);
					if (ptsvalid) // If available, add timestamp data as well. PTS = 33 bits
						data |= (pts << 31) | 0x1000000;
					writeStructureEntry(offset + pkt_offset, data);
					if ( //pkt[3] == 0x09 &&   /* MPEG4 AVC NAL unit access delimiter */
						 (pkt[4] >> 5) == 0) /* and I-frame */
					{
						if (ptsvalid && m_enable_accesspoints)
						{
							addAccessPoint(offset, pts);
							// eDebug("MPEG4 AVC UAD at %llx, pts %llx", offset, pts);
						}
					}
				}
			}
		}
		++pkt;
	}
	return 0;
}

inline int eMPEGStreamParserTS::wantPacket(const unsigned char *pkt) const
{
	const unsigned char *hdr = pkt + m_header_offset;
	if (hdr[0] != 0x47)
	{
		eDebug("missing sync!");
		return 0;
	}
	int ppid = ((hdr[1]&0x1F) << 8) | hdr[2];

	if (ppid != m_pid)
		return 0;
		
	if (m_need_next_packet)  /* next packet (on this pid) was required? */
		return 1;
	
	if (hdr[1] & 0x40)	 /* pusi set: yes. */
		return 1;

	return m_streamtype == 0; /* we need all packets for MPEG2, but only PUSI packets for H.264 */
}

void eMPEGStreamParserTS::parseData(off_t offset, const void *data, unsigned int len)
{
	const unsigned char *packet = (const unsigned char*)data;
	const unsigned char *packet_start = packet;
	
			/* sorry for the redundant code here, but there are too many special cases... */
	while (len)
	{
			/* emergency resync. usually, this should not happen, because the data should 
			   be sync-aligned.
			   
			   to make this code work for non-strictly-sync-aligned data, (for example, bad 
			   files) we fix a possible resync here by skipping data until the next 0x47.
			   
			   if this is a false 0x47, the packet will be dropped by wantPacket, and the
			   next time, sync will be re-established. */
		int skipped = 0;
		while (!m_pktptr && len)
		{
			if (packet[m_header_offset] == 0x47)
				break;
			len--;
			packet++;
			skipped++;
		}
		
		if (skipped)
			eDebug("SYNC LOST: skipped %d bytes.", skipped);
		
		if (!len)
			break;
		
		if (m_pktptr)
		{
				/* skip last packet */
			if (m_pktptr < 0)
			{
				unsigned int skiplen = -m_pktptr;
				if (skiplen > len)
					skiplen = len;
				packet += skiplen;
				len -= skiplen;
				m_pktptr += skiplen;
				continue;
			} else if (m_pktptr < m_header_offset + 4) /* header not complete, thus we don't know if we want this packet */
			{
				unsigned int storelen = m_header_offset + 4 - m_pktptr;
				if (storelen > len)
					storelen = len;
				memcpy(m_pkt + m_pktptr, packet,  storelen);
				
				m_pktptr += storelen;
				len -= storelen;
				packet += storelen;
				
				if (m_pktptr == m_header_offset + 4)
					if (!wantPacket(m_pkt))
					{
							/* skip packet */
						packet += 184 + m_header_offset;
						len -= 184 + m_header_offset;
						m_pktptr = 0;
						continue;
					}
			}
				/* otherwise we complete up to the full packet */
			unsigned int storelen = m_packetsize - m_pktptr;
			if (storelen > len)
				storelen = len;
			memcpy(m_pkt + m_pktptr, packet,  storelen);
			m_pktptr += storelen;
			len -= storelen;
			packet += storelen;
			
			if (m_pktptr == m_packetsize)
			{
				m_need_next_packet = processPacket(m_pkt, offset + (packet - packet_start));
				m_pktptr = 0;
			}
		} else if (len >= (unsigned int)m_header_offset + 4)  /* if we have a full header... */
		{
			if (wantPacket(packet))  /* decide wheter we need it ... */
			{
				if (len >= (unsigned int)m_packetsize)          /* packet complete? */
				{
					m_need_next_packet = processPacket(packet, offset + (packet - packet_start)); /* process it now. */
				} else
				{
					memcpy(m_pkt, packet, len);  /* otherwise queue it up */
					m_pktptr = len;
				}
			}

				/* skip packet */
			int sk = len;
			if (sk >= m_packetsize)
				sk = m_packetsize;
			else if (!m_pktptr) /* we dont want this packet, otherwise m_pktptr = sk (=len) > 4 */
				m_pktptr = sk - m_packetsize;

			len -= sk;
			packet += sk;
		} else             /* if we don't have a complete header */
		{
			memcpy(m_pkt, packet, len);   /* complete header next time */
			m_pktptr = len;
			packet += len;
			len = 0;
		}
	}
	commit();
}

void eMPEGStreamParserTS::addAccessPoint(off_t offset, pts_t pts, bool streamtime)
{
	timespec now;
	clock_gettime(CLOCK_MONOTONIC, &now);
	addAccessPoint(offset, pts, now, streamtime);
	m_has_accesspoints = true;
}

void eMPEGStreamParserTS::addAccessPoint(off_t offset, pts_t pts, timespec &now, bool streamtime)
{
	eMPEGStreamInformationWriter::addAccessPoint(offset, pts, streamtime);
	m_last_access_point = now;
}

void eMPEGStreamParserTS::setPid(int _pid, int type)
{
	m_pktptr = 0;
	m_pid = _pid;
	m_streamtype = type;
}

int eMPEGStreamParserTS::getLastPTS(pts_t &last_pts)
{
	if (!m_last_pts_valid)
	{
		last_pts = 0;
		return -1;
	}
	last_pts = m_last_pts;
	return 0;
}

