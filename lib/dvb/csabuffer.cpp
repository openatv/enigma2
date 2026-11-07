#include <lib/dvb/csabuffer.h>
#include <lib/base/eerror.h>

#include <chrono>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

/* Ring size per second of delay, and the ceiling before chunks are dropped.
 * Not bitrates - the level also carries what piles up while the decoder
 * lags, which is not predictable. grow() covers what this misses. */
static const size_t CSABUF_BYTES_PER_SEC = 1536 * 1024;
static const size_t CSABUF_BYTES_PER_SEC_MAX = 8 * 1024 * 1024;
static const size_t CSABUF_HARD_MAX = 64 * 1024 * 1024;

/* One slot being written, one waiting, one for the wrap. */
static const size_t CSABUF_MIN_SLOTS = 3;

static uint64_t monotonicUs()
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000000ULL + (uint64_t)(ts.tv_nsec / 1000);
}

eDVBCSABuffer::eDVBCSABuffer(int delay_ms, size_t max_chunk)
	: m_slot(max_chunk + sizeof(ChunkHdr))
{
	const uint64_t delay_us = (uint64_t)(delay_ms > 0 ? delay_ms : 0) * 1000;
	m_delay_us.store(delay_us, std::memory_order_relaxed); // S8417: no reader yet

	m_size = sizeFor(delay_us);
	m_max_size = capFor(delay_us);
}

size_t eDVBCSABuffer::sizeFor(uint64_t delay_us) const
{
	const size_t need = (size_t)((delay_us / 1000000.0) * CSABUF_BYTES_PER_SEC);

	/* Whole slots, and one spare for a chunk that wraps to the front. */
	size_t slots = need / m_slot + 2;
	if (slots < CSABUF_MIN_SLOTS)
		slots = CSABUF_MIN_SLOTS;
	if (slots > CSABUF_HARD_MAX / m_slot)
		slots = CSABUF_HARD_MAX / m_slot;

	return slots * m_slot;
}

size_t eDVBCSABuffer::capFor(uint64_t delay_us) const
{
	size_t cap = (size_t)((delay_us / 1000000.0) * CSABUF_BYTES_PER_SEC_MAX);
	cap = (cap / m_slot + 2) * m_slot;
	if (cap > CSABUF_HARD_MAX)
		cap = (CSABUF_HARD_MAX / m_slot) * m_slot;
	if (cap < m_size)
		cap = m_size;
	return cap;
}

eDVBCSABuffer::~eDVBCSABuffer()
{
	stop();
	free(m_buf);
	free(m_work);
}

bool eDVBCSABuffer::start()
{
	if (!m_stop)
		return true;
	if (!m_delay_us.load(std::memory_order_relaxed)) // S8417: nothing is ordered on it
		return false;

	m_buf = (unsigned char *)malloc(m_size);
	if (!m_buf)
	{
		eWarning("[eDVBCSABuffer] alloc %zu failed", m_size);
		m_size = 0;
		return false;
	}

	m_read_pos = 0;
	m_write_pos = 0;
	m_chunks = 0;
	m_dropped = 0;
	m_bytes_in = 0;
	m_start_us = monotonicUs();
	m_stop = 0;

	run();

	eDebug("[eDVBCSABuffer] started, delay=%dms, %zuKB allocated = %zu chunks of %zuKB (max %zuKB)",
		delayMs(), m_size >> 10, m_size / m_slot, m_slot >> 10, m_max_size >> 10);
	return true;
}

void eDVBCSABuffer::stop()
{
	/* If we aren't running, don't bother stopping. */
	if (m_stop == 1)
		return;

	m_stop = 1;
	m_cond.notify_all();
	kill();

	logSummary();
}

void eDVBCSABuffer::logSummary() const
{
	const uint64_t ran = monotonicUs() - m_start_us;
	eDebug("[eDVBCSABuffer] stopped after %llus: %llu chunks, %llu dropped, %zuKB peak, %lluKB/s",
		(unsigned long long)(ran / 1000000),
		(unsigned long long)m_chunks, (unsigned long long)m_dropped, m_size >> 10,
		(unsigned long long)(ran ? (m_bytes_in * 1000000ULL / ran) >> 10 : 0));
}

void eDVBCSABuffer::addDelayMs(int add_ms, int max_ms)
{
	if (add_ms <= 0)
		return;

	const uint64_t cur = m_delay_us.load(std::memory_order_relaxed); // S8417: only this thread writes it
	uint64_t want = cur + (uint64_t)add_ms * 1000;
	if (want > (uint64_t)max_ms * 1000)
		want = (uint64_t)max_ms * 1000;
	if (want <= cur)
		return;

	m_delay_us.store(want, std::memory_order_relaxed); // S8417: a stale read costs one more round

	/* Size for the longer wait now: one allocation instead of several once
	 * pushes start missing. */
	size_t before, after;
	{
		std::lock_guard<std::mutex> lock(m_lock);

		if (const size_t cap = capFor(want); cap > m_max_size)
			m_max_size = cap;

		before = m_size;
		if (m_buf)
			reserve(sizeFor(want));
		after = m_size;
	}

	eDebug("[eDVBCSABuffer] delay %llums -> %llums, ring %zuKB -> %zuKB (max %zuKB)",
		(unsigned long long)(cur / 1000), (unsigned long long)(want / 1000),
		before >> 10, after >> 10, m_max_size >> 10);
}

size_t eDVBCSABuffer::used() const
{
	std::lock_guard<std::mutex> lock(m_lock);
	if (m_write_pos >= m_read_pos)
		return m_write_pos - m_read_pos;
	return m_size - m_read_pos + m_write_pos;
}

size_t eDVBCSABuffer::size() const
{
	std::lock_guard<std::mutex> lock(m_lock);
	return m_size;
}

bool eDVBCSABuffer::fits(size_t need, bool &wrap) const
{
	if (m_write_pos >= m_read_pos)
	{
		/* Free: [write, size) and [0, read), minus room for a wrap marker. */
		if (m_size - m_write_pos >= need + sizeof(ChunkHdr))
		{
			wrap = false;
			return true;
		}
		if (m_size - m_write_pos >= sizeof(ChunkHdr) && m_read_pos > need)
		{
			wrap = true;
			return true;
		}
		return false;
	}

	/* Free: [write, read) */
	if (m_read_pos - m_write_pos > need)
	{
		wrap = false;
		return true;
	}
	return false;
}

size_t eDVBCSABuffer::nextChunkPos(size_t pos, uint32_t &len, uint64_t &stamp) const
{
	ChunkHdr hdr;
	memcpy(&hdr, m_buf + pos, sizeof(hdr));

	if (hdr.len == 0)
	{
		/* Wrap marker - the chunk sits at the start of the buffer. */
		pos = 0;
		memcpy(&hdr, m_buf + pos, sizeof(hdr));
	}

	len = hdr.len;
	stamp = hdr.stamp_us;
	return pos + sizeof(ChunkHdr);
}

bool eDVBCSABuffer::grow(size_t inuse, size_t need)
{
	/* The larger of what the delay needs and what this push needs, plus a
	 * slot of headroom. */
	size_t want = sizeFor(m_delay_us.load(std::memory_order_relaxed)); // S8417: nothing is ordered on it
	if (const size_t least = ((inuse + need) / m_slot + 2) * m_slot; want < least)
		want = least;
	else
		want += m_slot;

	/* Repacking alone helps a fragmented ring that has the room. Without the
	 * room it would be an allocation per chunk, so let the caller drop. */
	if (want <= m_size && m_size - inuse <= need + sizeof(ChunkHdr))
		return false;

	return reserve(want);
}

bool eDVBCSABuffer::reserve(size_t want)
{
	if (want > m_max_size)
		want = m_max_size;

	/* The same size still pays: the copy below relinearises the ring. */
	const bool grown = want > m_size;
	const size_t target = grown ? want : m_size;

	unsigned char *nb = (unsigned char *)malloc(target);
	if (!nb)
	{
		eWarning("[eDVBCSABuffer] alloc %zu failed, staying at %zu", target, m_size);
		return false;
	}

	/* Copy pending chunks over linearly. */
	size_t np = 0;
	size_t p = m_read_pos;
	size_t guard = m_size / sizeof(ChunkHdr) + 1;

	while (p != m_write_pos && guard > 0)
	{
		--guard;
		uint32_t len;
		uint64_t stamp;
		size_t dpos = nextChunkPos(p, len, stamp);
		if (!len || np + sizeof(ChunkHdr) + len > target)
			break;

		ChunkHdr hdr = { stamp, len };
		memcpy(nb + np, &hdr, sizeof(hdr));
		np += sizeof(hdr);
		memcpy(nb + np, m_buf + dpos, len);
		np += len;
		p = dpos + len;
	}

	if (grown)
		eDebug("[eDVBCSABuffer] %zuKB -> %zuKB = %zu chunks (%zuKB in use)",
			m_size >> 10, target >> 10, target / m_slot, np >> 10);
	else
		eDebug("[eDVBCSABuffer] repacked %zuKB (%zuKB in use)",
			target >> 10, np >> 10);

	free(m_buf);
	m_buf = nb;
	m_size = target;
	m_read_pos = 0;
	m_write_pos = np;
	return true;
}

bool eDVBCSABuffer::push(const unsigned char *data, int len)
{
	if (!data || len <= 0)
		return true;

	std::lock_guard<std::mutex> lock(m_lock);

	if (!m_buf)
		return false;

	const size_t need = sizeof(ChunkHdr) + (size_t)len;
	bool wrap = false;

	if (!fits(need, wrap))
	{
		size_t inuse = (m_write_pos >= m_read_pos)
			? m_write_pos - m_read_pos
			: m_size - m_read_pos + m_write_pos;

		if (!grow(inuse, need) || !fits(need, wrap))
		{
			/* Past the ceiling. Dropping here is a real gap. */
			m_dropped++;
			if ((m_dropped % 128) == 1)
				eWarning("[eDVBCSABuffer] full at %zuKB, dropped %llu chunks",
					m_size >> 10, (unsigned long long)m_dropped);
			return false;
		}
	}

	if (wrap)
	{
		ChunkHdr marker = { 0, 0 };
		memcpy(m_buf + m_write_pos, &marker, sizeof(marker));
		m_write_pos = 0;
	}

	ChunkHdr hdr = { monotonicUs(), (uint32_t)len };
	memcpy(m_buf + m_write_pos, &hdr, sizeof(hdr));
	memcpy(m_buf + m_write_pos + sizeof(hdr), data, len);
	m_write_pos += need;
	m_bytes_in += (uint64_t)len;

	m_cond.notify_one();
	return true;
}

void eDVBCSABuffer::thread()
{
	hasStarted(); /* "start()" blocks until we get here */

	while (!m_stop)
	{
		uint32_t len = 0;
		uint64_t stamp = 0;

		{
			std::unique_lock<std::mutex> lock(m_lock);

			while (!m_stop && m_read_pos == m_write_pos)
				m_cond.wait_for(lock, std::chrono::milliseconds(100));

			if (m_stop)
				break;

			/* Peek at the oldest chunk; it may not be due yet. */
			ChunkHdr hdr;
			size_t peek = m_read_pos;
			memcpy(&hdr, m_buf + peek, sizeof(hdr));
			if (hdr.len == 0)
			{
				peek = 0;
				memcpy(&hdr, m_buf + peek, sizeof(hdr));
			}

			if (!hdr.len)
			{
				eWarning("[eDVBCSABuffer] zero-length chunk, resetting");
				m_read_pos = 0;
				m_write_pos = 0;
				continue;
			}

			const uint64_t now = monotonicUs();
			const uint64_t age = now - hdr.stamp_us;

			// S8417: a stale read holds the chunk one more round
			if (const uint64_t delay_us = m_delay_us.load(std::memory_order_relaxed); age < delay_us)
			{
				/* Sleep the remainder, but wake often enough to see a stop. */
				uint64_t left_ms = (delay_us - age) / 1000 + 1;
				if (left_ms > 100)
					left_ms = 100;
				m_cond.wait_for(lock, std::chrono::milliseconds(left_ms));
				continue;
			}

			size_t dpos = nextChunkPos(m_read_pos, len, stamp);

			if (len > m_work_size)
			{
				unsigned char *nw = (unsigned char *)realloc(m_work, len);
				if (!nw)
				{
					eWarning("[eDVBCSABuffer] work alloc %u failed, dropping", len);
					m_read_pos = dpos + len;
					m_dropped++;
					continue;
				}
				m_work = nw;
				m_work_size = len;
			}

			memcpy(m_work, m_buf + dpos, len);
			m_read_pos = dpos + len;
		}

		const uint64_t out_us = monotonicUs();
		m_offset_ms.store((int)((out_us - stamp) / 1000), std::memory_order_relaxed); // S8417: diagnostics only
		m_chunks++;

		/* A pause is only ours if the released chunk was overdue; on time
		 * means the stream fed us thinly. */
		// S8417: diagnostics only
		if (const int offset_ms = m_offset_ms.load(std::memory_order_relaxed);
			m_last_out_us && out_us - m_last_out_us > 300000 &&
			offset_ms > delayMs() + 200)
		{
			++m_gaps;
			if (m_gaps <= 20 || !(m_gaps % 500))
				eWarning("[eDVBCSABuffer] gap #%u: %llums without output, chunk is %dms old for a %dms delay",
					m_gaps, (unsigned long long)((out_us - m_last_out_us) / 1000),
					offset_ms, delayMs());
		}
		m_last_out_us = out_us;

		if (m_consume)
			m_consume(m_work, (int)len);
	}
}
