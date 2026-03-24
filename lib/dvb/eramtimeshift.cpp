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
	len -= len % 188;
	if (!data || len == 0 || len > m_capacity)
		return 0;

	pthread_mutex_lock(&m_mutex);

	const int64_t now = nowMs();
	if (m_first_write_ms == 0)
		m_first_write_ms = now;

	size_t ring_pos = (size_t)(m_write_offset % (off_t)m_capacity);

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
		pthread_mutex_unlock(&m_mutex);
		errno = EAGAIN;
		return -1;
	}

	if ((off_t)len > avail)
		len = (size_t)(avail - (avail % 188));

	if (len == 0)
	{
		pthread_mutex_unlock(&m_mutex);
		errno = EAGAIN;
		return -1;
	}

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
		return 0; /* at write edge — no new data yet, retry */
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

	/* Store sample for sliding window (getPTSWindow). */
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
 * Reads PCR from the adaptation field of a single 188-byte TS packet.
 * The adaptation field is ALWAYS unencrypted per the DVB standard,
 * even for scrambled channels.
 * Returns the 33-bit PCR base in 90 kHz units (same unit as PTS).
 */
bool eRamRecorder::extractPCR(const uint8_t *pkt, pts_t &pcr)
{
	if (pkt[0] != 0x47)
		return false;
	/* adaptation_field_control bits [5:4] must have 0x20 set */
	if (!(pkt[3] & 0x20))
		return false;
	/* adaptation_field_length >= 7 for PCR */
	if (pkt[4] < 7)
		return false;
	/* PCR_flag bit */
	if (!(pkt[5] & 0x10))
		return false;
	/* PCR base (33 bits): (b6<<25)|(b7<<17)|(b8<<9)|(b9<<1)|(b10>>7) */
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
		m_current_offset += written;

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
}

/*
 * getFirstPTS()
 *
 * Override of virtual eDVBRecordFileThread::getFirstPTS().
 * Returns the first PCR seen, used for seek bar / getLength().
 */
int eRamRecorder::getFirstPTS(pts_t &pts)
{
	pthread_mutex_lock(&m_pcr_mutex);
	bool valid = m_first_pcr_valid;
	pts_t val  = m_first_pcr;
	pthread_mutex_unlock(&m_pcr_mutex);
	if (!valid)
		return -1;
	pts = val;
	return 0;
}

/*
 * getPTSWindow()
 *
 * Returns the oldest and newest PCR currently inside the ring buffer window.
 * Unlike getFirstPTS() which is frozen at recording start, this slides forward
 * as the ring buffer wraps. Used by eRamServicePlay for seek bar and getLength
 * so the bar always reflects the live buffer window, not the full recording.
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

	/* Scan history for the oldest sample whose offset is still
	 * inside the ring buffer (offset >= min_off). */
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
 * Scans PCR history for the sample whose PCR is closest to `target`
 * and whose byte offset is still inside the live ring buffer window.
 * Returns the byte offset, or -1 if not found.
 *
 * Used by eRamServicePlay::seekTo() to bypass the .ap file mechanism.
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
		if (s.offset < min_off)
			continue;

		/* Wrap-safe circular distance between sample PCR and target.
		 * Use the shorter arc of the 33-bit circle to handle PCR wrap. */
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
				break; /* exact match */
		}
	}

	pthread_mutex_unlock(&m_pcr_mutex);

	/* Align down to 188-byte TS packet boundary */
	if (best_offset > 0)
		best_offset -= best_offset % 188;

	/* Snap forward to the nearest I-frame so the decoder gets a clean
	 * picture immediately — identical behaviour to .ap file seeks. */
	if (best_offset >= 0)
	{
		off_t ap = m_ring->findNearestAccessPoint(best_offset);
		if (ap >= 0)
			best_offset = ap;
	}

	return best_offset;
}
