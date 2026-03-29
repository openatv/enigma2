#ifndef __lib_dvb_eramtimeshift_h
#define __lib_dvb_eramtimeshift_h

#include <lib/dvb/demux.h>
#include <lib/base/itssource.h>
#include <memory>
#include <vector>
#include <pthread.h>
#include <atomic>
#include <stdint.h>

struct eRamBlock
{
	off_t	offset;		/* absolute write offset at this block */
	bool	is_access_point;
};

/*
 * eRamRingBuffer
 *
 * Seekable circular RAM buffer for DVB TS data.
 * Addressed by absolute byte offset (like a file), so the standard
 * e2 timeshift machinery (eFilePushThread, cuesheet, seek) works
 * without modification.
 *
 * read(offset, ...) maps the absolute offset to the physical ring
 * position via offset % capacity.  Reads from overwritten regions
 * return EAGAIN.
 *
 * Thread safety: all public methods lock m_mutex internally.
 * The caller does NOT need external synchronization.
 */
class eRamRingBuffer
{
public:
	eRamRingBuffer(size_t capacity_bytes, size_t max_blocks);
	~eRamRingBuffer();

	bool	isValid() const { return m_buf && m_blocks; }

	/* Write TS data into the ring.  Returns bytes written (aligned
	 * down to 188).  is_access_point marks the block for fast seek. */
	int	write(const uint8_t *data, size_t len, bool is_access_point = false);

	/* Read TS data from the ring at the given absolute offset.
	 * Returns bytes read, or -1 with errno=EAGAIN if the region
	 * has been overwritten or no data is available yet. */
	int	read(off_t offset, uint8_t *buf, size_t len);

	off_t	getWriteOffset() const;
	off_t	getMinOffset() const;
	int64_t	bufferedMs() const;

	/* Linear scan: finds the first access point at or after
	 * from_offset that is still inside the valid ring window. */
	off_t	findNearestAccessPoint(off_t from_offset) const;

	static int64_t nowMs();

private:
	uint8_t		*m_buf;
	size_t		 m_capacity;

	size_t		 m_max_blocks;
	off_t		 m_write_offset;
	int64_t		 m_first_write_ms;

	eRamBlock	*m_blocks;
	size_t		 m_block_write_idx;
	size_t		 m_total_blocks;

	mutable pthread_mutex_t	m_mutex;
};

/*
 * eRamTsSource
 *
 * iTsSource backed by eRamRingBuffer.
 * Implements read(offset, ...) so eFilePushThread can seek within
 * the recorded RAM data.  length() returns the current write offset
 * so the push thread knows how far it can read.
 *
 * Lap detection: when the ring buffer overwrites data that the decoder
 * is still trying to read, read() sets m_lapped = true and stores the
 * new safe aligned offset.  The watchdog in eRamServicePlay picks this
 * up via getLappedOffset() and triggers a source position jump.
 */
class eRamTsSource : public iTsSource
{
	DECLARE_REF(eRamTsSource);
public:
	explicit eRamTsSource(std::shared_ptr<eRamRingBuffer> buf);
	~eRamTsSource() override;

	ssize_t	read(off_t offset, void *buf, size_t count) override;
	off_t	length() override;
	int	valid()  override { return m_buf ? 1 : 0; }
	off_t	offset() override;

	/* Set the position the push thread will start reading from.
	 * Called before the thread starts so offset() returns this value
	 * instead of the live write position.  -1 means "start from live". */
	void	setStartOffset(off_t o);

	/* Returns true (once) when the ring has lapped the read position.
	 * out_offset is set to the nearest safe aligned byte to resume from.
	 * Thread-safe: uses m_offset_mutex internally. */
	bool getLappedOffset(off_t &out_offset);

private:
	std::shared_ptr<eRamRingBuffer>	m_buf;

	mutable pthread_mutex_t	m_offset_mutex;
	bool			m_lapped;
	off_t			m_lapped_offset;
	off_t			m_start_offset;   /* -1 = live edge */
};

/*
 * eRamRecorder
 *
 * Subclass of eDVBRecordScrambledThread that writes into eRamRingBuffer
 * instead of a disk file.  Descrambling (CI, SoftCAM, StreamRelay) and
 * I-frame detection work identically to the disk path.
 *
 * PCR is extracted directly from the adaptation field of each TS packet
 * (always unencrypted per DVB spec) and cached for getCurrentPCR() /
 * getFirstPTS(), which drive the seek bar and the Precise Recovery System.
 *
 * Thread safety note:
 *   - writeData() / updatePCR() run on the recorder thread.
 *   - findOffsetForPTS() / getPTSWindow() run on the main thread.
 *   - m_pcr_mutex protects the PCR history vector.
 *   - m_write_offset_atomic tracks the recorder's write position
 *     atomically so the main thread can read it without a data race.
 */
class eRamRecorder : public eDVBRecordScrambledThread
{
public:
	explicit eRamRecorder(eRamRingBuffer *buf, int packetsize = 188);
	~eRamRecorder() override;

	eRamRingBuffer *getRingBuffer() { return m_ring; }

	/* Fast non-blocking check to see if the ring buffer has data.
	 * Fixes the "200ms Glitch" (black screen timeout) on unpause.
	 * Uses atomic load for thread-safe access from main thread. */
	bool waitForFirstData(int timeout_ms) override;

	/* Returns the oldest and newest PCR still inside the ring buffer
	 * window.  Unlike getFirstPTS() which is fixed at recording start,
	 * this tracks the sliding window correctly after ring wrap-around.
	 * Returns 0 on success, -1 if not enough data yet. */
	int getPTSWindow(pts_t &first, pts_t &last) const;

	/* Returns the very first PCR seen since recording started.
	 * Stable across ring wraps — used as fixed reference by
	 * getPlayPosition() and getLength(). */
	int getFirstPCR(pts_t &pcr) const;

	/* Find the byte offset inside the ring buffer that is closest to
	 * the given absolute PCR value.  Returns -1 if not found.
	 * Used by eRamServicePlay::seekTo() to bypass .ap file logic. */
	off_t findOffsetForPTS(pts_t target) const;

protected:
	int  writeData(int len) override;
	void flush() override;

private:
	static bool extractPCR(const uint8_t *pkt, pts_t &pcr);
	void        updatePCR(pts_t pcr);

	eRamRingBuffer *m_ring;

	/* Atomic copy of the parent's m_current_offset.
	 * The parent field is written by the recorder thread (writeData)
	 * and read by the main thread (waitForFirstData) without any
	 * synchronization primitive.  This atomic provides a data-race-free
	 * way to observe the current write position. */
	std::atomic<off_t>	m_write_offset_atomic;

	pts_t	m_last_pcr;
	bool	m_last_pcr_valid;
	pts_t	m_first_pcr;
	bool	m_first_pcr_valid;

	/* Circular history of (offset, pcr) samples for sliding window.
	 * PCR arrives ~25 times/sec (every ~40ms on PCR PID).
	 * 8192 entries ≈ 328s ≈ ~5.5 min — covers a typical 128MB ring
	 * buffer at 6Mbit/s without losing seek resolution after wrap.
	 *
	 * Protected by m_pcr_mutex because updatePCR() writes from the
	 * recorder thread while findOffsetForPTS()/getPTSWindow() read
	 * from the main thread. */
	static const size_t PCR_HISTORY = 8192;
	struct PcrSample { off_t offset; pts_t pcr; };
	std::vector<PcrSample>	m_pcr_history;
	size_t		m_pcr_hist_write;
	size_t		m_pcr_hist_count;

	mutable pthread_mutex_t	m_pcr_mutex;
};

#endif /* __lib_dvb_eramtimeshift_h */
