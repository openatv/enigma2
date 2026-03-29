#include "eramtimeshift.h"
#include <lib/base/eerror.h>
#include <algorithm>
#include <vector>
#include <string>
#include <assert.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>

/* ------------------------------------------------------------------ */
/* eRamRingBuffer                                                      */
/* ------------------------------------------------------------------ */

int64_t eRamRingBuffer::nowMs()
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (int64_t)(ts.tv_sec * 1000) + (ts.tv_nsec / 1000000);
}

eRamRingBuffer::eRamRingBuffer(size_t capacity_bytes, size_t max_blocks)
	: m_max_blocks(max_blocks)
	, m_write_offset(0)
	, m_first_write_ms(0)
	, m_block_write_idx(0)
	, m_total_blocks(0)
{
	/* Align capacity down to 188-byte boundary so every read/write
	 * is always a whole number of TS packets. */
	m_capacity = capacity_bytes - (capacity_bytes % 188);

	m_buf = static_cast<uint8_t *>(malloc(m_capacity));
	m_blocks = m_buf ? static_cast<eRamBlock *>(calloc(m_max_blocks, sizeof(eRamBlock))) : nullptr;

	pthread_mutex_init(&m_mutex, nullptr);

	if (!m_buf || !m_blocks)
	{
		eWarning("[eRamRingBuffer] allocation failed (%zu MB) — RAM timeshift disabled",
			m_capacity >> 20);
		free(m_buf);
		free(m_blocks);
		m_buf    = nullptr;
		m_blocks = nullptr;
		return;
	}

	eDebug("[eRamRingBuffer] ready: %zu MB, %zu blocks",
		m_capacity >> 20, m_max_blocks);
}

eRamRingBuffer::~eRamRingBuffer()
{
	pthread_mutex_destroy(&m_mutex);
	free(m_blocks);
	free(m_buf);
}

int eRamRingBuffer::write(const uint8_t *data, size_t len, bool is_access_point)
{
	/* Round down to whole TS packets — partial packets are not valid. */
	len -= len % 188;
	if (!data || len == 0 || len > m_capacity)
		return 0;

	pthread_mutex_lock(&m_mutex);

	const int64_t now = nowMs();
	if (m_first_write_ms == 0)
		m_first_write_ms = now;

	size_t ring_pos = (size_t)(m_write_offset % (off_t)m_capacity);

	/* Handle wrap-around: split memcpy if data crosses ring boundary. */
	size_t part1 = m_capacity - ring_pos;
	if (part1 >= len)
	{
		memcpy(m_buf + ring_pos, data, len);
	}
	else
	{
		memcpy(m_buf + ring_pos, data, part1);
		memcpy(m_buf,            data + part1, len - part1);
	}

	/* Record block metadata for access-point lookup. */
	eRamBlock &blk      = m_blocks[m_block_write_idx];
	blk.offset          = m_write_offset;
	blk.is_access_point = is_access_point;

	m_block_write_idx = (m_block_write_idx + 1) % m_max_blocks;
	if (m_total_blocks < m_max_blocks)
		m_total_blocks++;

	m_write_offset += (off_t)len;

	pthread_mutex_unlock(&m_mutex);
	return (int)len;
}

int eRamRingBuffer::read(off_t offset, uint8_t *buf, size_t len)
{
	len -= len % 188;
	if (!buf || len == 0)
	{
		errno = EAGAIN;
		return -1;
	}

	pthread_mutex_lock(&m_mutex);

	off_t min_off = (m_write_offset > (off_t)m_capacity)
	              ? m_write_offset - (off_t)m_capacity
	              : 0;
	off_t avail   = m_write_offset - offset;

	if (offset < min_off || avail <= 0)
	{
		/* Offset has been overwritten by the ring — caller must seek
		 * forward to the current minimum. */
		pthread_mutex_unlock(&m_mutex);
		errno = EAGAIN;
		return -1;
	}

	/* Clamp read length to available data (rounded down to 188). */
	if ((off_t)len > avail)
		len = (size_t)(avail - (avail % 188));

	if (len == 0)
	{
		pthread_mutex_unlock(&m_mutex);
		errno = EAGAIN;
		return -1;
	}

	/* Map absolute offset → ring position, handle wrap-around. */
	size_t ring_pos = (size_t)(offset % (off_t)m_capacity);
	size_t part1    = m_capacity - ring_pos;

	if (part1 >= len)
	{
		memcpy(buf, m_buf + ring_pos, len);
	}
	else
	{
		memcpy(buf,         m_buf + ring_pos, part1);
		memcpy(buf + part1, m_buf,            len - part1);
	}

	pthread_mutex_unlock(&m_mutex);
	return (int)len;
}

off_t eRamRingBuffer::getWriteOffset() const
{
	pthread_mutex_lock(&m_mutex);
	off_t v = m_write_offset;
	pthread_mutex_unlock(&m_mutex);
	return v;
}

off_t eRamRingBuffer::getMinOffset() const
{
	pthread_mutex_lock(&m_mutex);
	off_t v = (m_write_offset > (off_t)m_capacity)
	        ? m_write_offset - (off_t)m_capacity
	        : 0;
	pthread_mutex_unlock(&m_mutex);
	return v;
}

int64_t eRamRingBuffer::bufferedMs() const
{
	pthread_mutex_lock(&m_mutex);
	int64_t v = (m_first_write_ms == 0) ? 0 : (nowMs() - m_first_write_ms);
	pthread_mutex_unlock(&m_mutex);
	return v;
}

off_t eRamRingBuffer::findNearestAccessPoint(off_t from_offset) const
{
	pthread_mutex_lock(&m_mutex);

	off_t min_off = (m_write_offset > (off_t)m_capacity)
	              ? m_write_offset - (off_t)m_capacity
	              : 0;

	/* Linear scan for the first access point >= from_offset that is
	 * still inside the valid ring window (>= min_off).
	 * TODO: consider binary search if m_max_blocks grows beyond ~8K. */
	off_t best = -1;
	for (size_t i = 0; i < m_total_blocks; i++)
	{
		const eRamBlock &b = m_blocks[i];
		if (b.offset >= from_offset && b.offset >= min_off && b.is_access_point)
		{
			if (best == -1 || b.offset < best)
				best = b.offset;
		}
	}

	pthread_mutex_unlock(&m_mutex);
	return best;
}

/* ------------------------------------------------------------------ */
/* eRamTsSource                                                        */
/* ------------------------------------------------------------------ */

DEFINE_REF(eRamTsSource);

eRamTsSource::eRamTsSource(std::shared_ptr<eRamRingBuffer> buf)
	: m_buf(buf)
	, m_lapped(false)
	, m_lapped_offset(0)
	, m_start_offset(-1)
{
	pthread_mutex_init(&m_offset_mutex, nullptr);
}

eRamTsSource::~eRamTsSource()
{
	pthread_mutex_destroy(&m_offset_mutex);
}

ssize_t eRamTsSource::read(off_t offset, void *buf, size_t count)
{
	if (!m_buf || !buf || count == 0)
		return 0;

	/* Pre-check: if offset is already below min, the ring has lapped
	 * us.  Compute the nearest safe 188-aligned offset. */
	off_t min_off = m_buf->getMinOffset();
	if (offset < min_off)
	{
		off_t aligned = min_off + (188 - min_off % 188) % 188;
		eDebug("[eRamTsSource] LAP pre-check: offset=%lld < min_off=%lld → lapped (aligned=%lld)",
		       (long long)offset, (long long)min_off, (long long)aligned);
		pthread_mutex_lock(&m_offset_mutex);
		m_lapped        = true;
		m_lapped_offset = aligned;
		pthread_mutex_unlock(&m_offset_mutex);
		errno = EAGAIN;
		return -1;
	}

	int rc = m_buf->read(offset, static_cast<uint8_t *>(buf), count);
	if (rc < 0 && errno == EAGAIN)
	{
		/* EAGAIN has two causes:
		 * 1. At write edge — push thread caught up, no new data yet (normal)
		 * 2. Data overwritten — ring buffer lapped the read position (error)
		 *
		 * Only set the lap flag for case 2, detected by offset < current
		 * min_off.  Case 1 returns 0 so eFilePushThread treats it as
		 * "no data yet" and retries, rather than -1 which signals EOF. */
		off_t cur_min = m_buf->getMinOffset();
		if (offset < cur_min)
		{
			off_t aligned = cur_min + (188 - cur_min % 188) % 188;
			eDebug("[eRamTsSource] LAP TOCTOU: offset=%lld < cur_min=%lld → lapped (aligned=%lld)",
			       (long long)offset, (long long)cur_min, (long long)aligned);
			pthread_mutex_lock(&m_offset_mutex);
			m_lapped        = true;
			m_lapped_offset = aligned;
			pthread_mutex_unlock(&m_offset_mutex);
			return -1; /* real lap — error */
		}
		/* At write edge — no new data yet.  Return 0 to let the
		 * push thread retry without treating it as an error. */
		return 0;
	}
	return (ssize_t)rc;
}

bool eRamTsSource::getLappedOffset(off_t &out_offset)
{
	pthread_mutex_lock(&m_offset_mutex);
	bool lapped = m_lapped;
	if (lapped)
	{
		out_offset = m_lapped_offset;
		m_lapped   = false;
	}
	pthread_mutex_unlock(&m_offset_mutex);
	return lapped;
}

off_t eRamTsSource::length()
{
	return m_buf ? m_buf->getWriteOffset() : -1;
}

off_t eRamTsSource::offset()
{
	pthread_mutex_lock(&m_offset_mutex);
	off_t o = m_start_offset;
	if (o >= 0)
		m_start_offset = -1;
	pthread_mutex_unlock(&m_offset_mutex);

	/* First call after setStartOffset() returns the forced offset.
	 * Subsequent calls return the live write edge. */
	if (o >= 0)
		return o;
	return m_buf ? m_buf->getWriteOffset() : 0;
}

void eRamTsSource::setStartOffset(off_t o)
{
	pthread_mutex_lock(&m_offset_mutex);
	m_start_offset = o;
	pthread_mutex_unlock(&m_offset_mutex);
}

/* ------------------------------------------------------------------ */
/* eRamRecorder                                                        */
/* ------------------------------------------------------------------ */

eRamRecorder::eRamRecorder(eRamRingBuffer *buf, int packetsize)
	: eDVBRecordScrambledThread(packetsize, 188 * 256, false, false)
	, m_ring(buf)
	, m_write_offset_atomic(0)
	, m_last_pcr(0)
	, m_last_pcr_valid(false)
	, m_first_pcr(0)
	, m_first_pcr_valid(false)
	, m_pcr_hist_write(0)
	, m_pcr_hist_count(0)
{
	m_pcr_history.resize(PCR_HISTORY);
	/* PCR scan loop in writeData() assumes 188-byte TS packets.
	 * RAM timeshift always uses packetsize=188 (see startTimeshift()),
	 * but assert here to catch any future misuse early. */
	assert(packetsize == 188);
	pthread_mutex_init(&m_pcr_mutex, nullptr);
}

eRamRecorder::~eRamRecorder()
{
	pthread_mutex_destroy(&m_pcr_mutex);
}

/*
 * waitForFirstData()
 *
 * Fast non-blocking check to see if the ring buffer has data.
 * Fixes the "200ms Glitch" (black screen timeout) on unpause.
 *
 * Uses atomic load of the write offset so we avoid reading
 * eRamRingBuffer internals from the main thread while the recorder
 * thread is actively writing. */
bool eRamRecorder::waitForFirstData(int timeout_ms)
{
	int slept = 0;
	while (slept < timeout_ms)
	{
		if (m_write_offset_atomic.load(std::memory_order_acquire) > 0)
			return true;
		usleep(10000); /* Check every 10ms */
		slept += 10;
	}
	return false;
}

void eRamRecorder::updatePCR(pts_t pcr)
{
	pthread_mutex_lock(&m_pcr_mutex);
	m_last_pcr       = pcr;
	m_last_pcr_valid = true;
	if (!m_first_pcr_valid)
	{
		m_first_pcr       = pcr;
		m_first_pcr_valid = true;
	}

	/* Store sample for sliding window (getPTSWindow).
	 * m_current_offset is the parent's write position — safe to read
	 * here because we are on the recorder thread (same thread that
	 * writes m_current_offset in writeData). */
	m_pcr_history[m_pcr_hist_write].offset = m_current_offset;
	m_pcr_history[m_pcr_hist_write].pcr    = pcr;
	m_pcr_hist_write = (m_pcr_hist_write + 1) % PCR_HISTORY;
	if (m_pcr_hist_count < PCR_HISTORY)
		m_pcr_hist_count++;

	pthread_mutex_unlock(&m_pcr_mutex);
}

/*
 * extractPCR()
 *
 * Parse the 33-bit PCR base from the TS adaptation field.
 * The adaptation field is always unencrypted per DVB spec,
 * so this works on scrambled streams without decryption.
 */
bool eRamRecorder::extractPCR(const uint8_t *pkt, pts_t &pcr)
{
	if (pkt[0] != 0x47)
		return false;
	/* adaptation_field_control bits [5:4] must be 0b10 or 0b11 */
	if (!(pkt[3] & 0x20))
		return false;
	/* adaptation_field_length >= 7 for PCR to fit */
	if (pkt[4] < 7)
		return false;
	/* PCR_flag (bit 4 of adaptation field flags byte) */
	if (!(pkt[5] & 0x10))
		return false;
	/* PCR base (33 bits): bytes 6..10 */
	pcr = ((pts_t)pkt[6] << 25)
	    | ((pts_t)pkt[7] << 17)
	    | ((pts_t)pkt[8] <<  9)
	    | ((pts_t)pkt[9] <<  1)
	    | ((pts_t)(pkt[10] >> 7) & 1);
	return true;
}

int eRamRecorder::writeData(int len)
{
	if (len <= 0 || !m_ring)
		return 0;

	/* Descramble in place (same as disk recorder path). */
	if (m_serviceDescrambler)
		m_serviceDescrambler->descramble(m_buffer, len);

	/* Check corruption status FIRST before updating PCR.
	 * PCR lives in the adaptation field which is never encrypted, so
	 * extractPCR() succeeds even on scrambled/corrupt payloads.  If we
	 * updated PCR unconditionally, getCurrentPCR() would keep returning
	 * increasing values while the stream is corrupt → PRS current_delay
	 * grows → premature unpause → black screen loop.
	 *
	 * servicedvb.cpp already handles event flooding via:
	 *   if (m_stream_corruption_detected) return;
	 *   if (m_is_paused) return;
	 * so no rate-limiting is needed here. */
	size_t ap_before = m_ts_parser.getAccessPointCount();
	bool is_corrupt = false;

	if (!getProtocol())
	{
		int parse_result = m_ts_parser.parseData(m_current_offset, m_buffer, len);
		if (parse_result == -2)
		{
			is_corrupt = true;
			m_event(eFilePushThreadRecorder::evtStreamCorrupt);
		}
	}

	/* Mirror disk behavior — discard corrupt buffers entirely.
	 * On disk, asyncWrite() returns early without aio_write() when
	 * parseData() returns -2.  We do the same here so the ring buffer
	 * never contains corrupt data and getCurrentPCR() freezes naturally. */
	if (is_corrupt)
		return len;

	bool is_ap = (m_ts_parser.getAccessPointCount() > ap_before);

	int written = m_ring->write(m_buffer, (size_t)len, is_ap);
	if (written > 0)
	{
		/* Advance parent offset (recorder thread — same thread). */
		m_current_offset += written;

		/* Publish the new offset atomically so the main thread can
		 * read it in waitForFirstData() without a data race.
		 * release pairs with the acquire in waitForFirstData(). */
		m_write_offset_atomic.store(m_current_offset, std::memory_order_release);

		/* Only update PCR after a successful write — guarantees that
		 * getCurrentPCR() never advances past data not yet in the ring. */
		const uint8_t *data = reinterpret_cast<const uint8_t *>(m_buffer);
		for (int i = 0; i + 188 <= written; i += 188)
		{
			pts_t pcr;
			if (extractPCR(data + i, pcr))
				updatePCR(pcr);
		}
	}
	return written;
}

void eRamRecorder::flush()
{
	/* Nothing to flush — ring buffer is purely in-memory. */
}

/*
 * getFirstPCR()
 *
 * Returns the very first PCR seen since recording started.
 * Stable across ring wraps — used as fixed reference by getPlayPosition()
 * to match the disk timeshift pts_begin semantics.
 */
int eRamRecorder::getFirstPCR(pts_t &pcr) const
{
	pthread_mutex_lock(&m_pcr_mutex);
	bool valid = m_first_pcr_valid;
	pts_t val  = m_first_pcr;
	pthread_mutex_unlock(&m_pcr_mutex);
	if (!valid) return -1;
	pcr = val;
	return 0;
}

/*
 * getPTSWindow()
 *
 * Returns the oldest and newest PCR values still inside the valid
 * ring buffer window.  Used by the seek bar to show the available
 * timeshift range.
 *
 * Thread safety: called from main thread, protected by m_pcr_mutex.
 * Samples below min_off are skipped (they've been overwritten).
 */
int eRamRecorder::getPTSWindow(pts_t &first, pts_t &last) const
{
	if (!m_ring)
		return -1;

	const off_t min_off = m_ring->getMinOffset();

	pthread_mutex_lock(&m_pcr_mutex);

	if (!m_last_pcr_valid || m_pcr_hist_count == 0)
	{
		pthread_mutex_unlock(&m_pcr_mutex);
		return -1;
	}

	last = m_last_pcr;

	/* Scan the entire history for the oldest valid sample.
	 * The history is circular, so we can't just take index 0. */
	pts_t  oldest_pcr    = 0;
	off_t  oldest_offset = -1;
	bool   found         = false;

	for (size_t i = 0; i < m_pcr_hist_count; i++)
	{
		const PcrSample &s = m_pcr_history[i];
		if (s.offset >= min_off)
		{
			if (!found || s.offset < oldest_offset)
			{
				oldest_pcr    = s.pcr;
				oldest_offset = s.offset;
				found         = true;
			}
		}
	}

	pthread_mutex_unlock(&m_pcr_mutex);

	if (!found)
		return -1;

	first = oldest_pcr;
	return 0;
}

/*
 * findOffsetForPTS()
 *
 * Locates the byte offset in the ring buffer closest to the given
 * absolute PCR value.  Uses the circular PCR history for lookup.
 *
 * 1. Linear scan through all valid (non-overwritten) samples.
 * 2. Find the sample with smallest PCR distance (handles 33-bit wrap).
 * 3. Snap down to 188-byte packet boundary.
 * 4. Snap to nearest I-frame (access point) for clean decode start.
 *
 * Thread safety: called from main thread, protected by m_pcr_mutex.
 */
off_t eRamRecorder::findOffsetForPTS(pts_t target) const
{
	if (!m_ring)
		return -1;

	const off_t min_off = m_ring->getMinOffset();

	pthread_mutex_lock(&m_pcr_mutex);

	off_t  best_offset = -1;
	pts_t  best_delta  = INT64_MAX;
	bool   best_found  = false;

	for (size_t i = 0; i < m_pcr_hist_count; i++)
	{
		const PcrSample &s = m_pcr_history[i];

		/* Skip overwritten samples. */
		if (s.offset < min_off)
			continue;

		/* PCR wrap-aware distance: take the shorter path around
		 * the 33-bit counter. */
		pts_t mask = (1LL << 33) - 1;
		pts_t fwd  = (s.pcr  - target) & mask;
		pts_t bwd  = (target - s.pcr)  & mask;
		pts_t diff = (fwd < bwd) ? fwd : bwd;

		if (!best_found || diff < best_delta)
		{
			best_delta  = diff;
			best_offset = s.offset;
			best_found  = true;
			if (diff == 0)
				break; /* exact match — no need to keep scanning */
		}
	}

	pthread_mutex_unlock(&m_pcr_mutex);

	/* Snap down to 188-byte packet boundary. */
	if (best_offset > 0)
		best_offset -= best_offset % 188;

	/* Snap to nearest I-frame for clean decode start. */
	if (best_offset >= 0)
	{
		off_t ap = m_ring->findNearestAccessPoint(best_offset);
		if (ap >= 0)
			best_offset = ap;
	}

	return best_offset;
}
