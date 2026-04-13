#ifndef __lib_dvb_eramtimeshift_h
#define __lib_dvb_eramtimeshift_h

#include <lib/base/itssource.h>
#include <lib/dvb/demux.h>
#include <memory>
#include <pthread.h>
#include <stdint.h>

struct eRamBlock {
	off_t offset; // absolute write offset at this block
	bool is_access_point;
};

// eRamRingBuffer
//
// Seekable circular RAM buffer for DVB TS data.
// Addressed by absolute byte offset (like a file), so the standard
// e2 timeshift machinery (eFilePushThread, cuesheet, seek) works
// without modification.
//
// read(offset, ...) maps the absolute offset to the physical ring
// position via offset % capacity. Reads from overwritten regions
// return EAGAIN.
//
// Thread safety: all public methods lock m_mutex internally.
// The caller does NOT need external synchronization.
class eRamRingBuffer {
public:
	eRamRingBuffer(size_t capacity_bytes, size_t max_blocks);
	~eRamRingBuffer();

	bool isValid() const { return m_buf && m_blocks; }

	// Write TS data into the ring. Returns bytes written (aligned
	// down to 188). is_access_point marks the block for fast seek.
	int write(const uint8_t* data, size_t len, bool is_access_point = false);

	// Read TS data from the ring at the given absolute offset.
	// Returns bytes read, or -1 with errno=EAGAIN if the region
	// has been overwritten or no data is available yet.
	int read(off_t offset, uint8_t* buf, size_t len);

	off_t getWriteOffset() const;
	off_t getMinOffset() const;
	int64_t bufferedMs() const;

	// Linear scan: finds the first access point at or after
	// from_offset that is still inside the valid ring window.
	off_t findNearestAccessPoint(off_t from_offset) const;

	static int64_t nowMs();

private:
	uint8_t* m_buf;
	size_t m_capacity;

	size_t m_max_blocks;
	off_t m_write_offset;
	int64_t m_first_write_ms;

	eRamBlock* m_blocks;
	size_t m_block_write_idx;
	size_t m_total_blocks;

	mutable pthread_mutex_t m_mutex;
};

// eRamTsSource
//
// iTsSource backed by eRamRingBuffer.
// Implements read(offset, ...) so eFilePushThread can seek within
// the recorded RAM data. length() returns the current write offset
// so the push thread knows how far it can read.
//
// Lap detection: when the ring buffer overwrites data that the decoder
// is still trying to read, read() sets m_lapped = true and stores the
// new safe aligned offset. The watchdog in eRamServicePlay picks this
// up via getLappedOffset() and triggers a source position jump.
class eRamTsSource : public iTsSource {
	DECLARE_REF(eRamTsSource);

public:
	explicit eRamTsSource(std::shared_ptr<eRamRingBuffer> buf);
	~eRamTsSource() override;

	ssize_t read(off_t offset, void* buf, size_t count) override;
	off_t length() override;
	int valid() override { return m_buf ? 1 : 0; }
	off_t offset() override;

	// Set the position the push thread will start reading from.
	// Called before the thread starts so offset() returns this value
	// instead of the live write position. -1 means "start from live".
	void setStartOffset(off_t o);

	// Returns true (once) when the ring has lapped the read position.
	// out_offset is set to the nearest safe aligned byte to resume from.
	// Thread-safe: uses m_offset_mutex internally.
	bool getLappedOffset(off_t& out_offset);

private:
	std::shared_ptr<eRamRingBuffer> m_buf;

	mutable pthread_mutex_t m_offset_mutex;
	bool m_lapped;
	off_t m_lapped_offset;
	off_t m_start_offset; // -1 = live edge
};

// eRamRecorder
//
// Subclass of eDVBRecordScrambledThread that writes into eRamRingBuffer
// instead of a disk file. Descrambling (CI, SoftCAM, StreamRelay) and
// I-frame detection work identically to the disk path.
//
// relies entirely on the base class eDVBRecordFileThread for PTS
// extraction (via eMPEGStreamParserTS) to drive the seek bar and
// the Precise Recovery System, matching the standard master branch behavior.
class eRamRecorder : public eDVBRecordScrambledThread {
public:
	explicit eRamRecorder(eRamRingBuffer* buf, int packetsize = 188);
	~eRamRecorder() override;

	eRamRingBuffer* getRingBuffer() { return m_ring; }

protected:
	int writeData(int len) override;
	void flush() override;

private:
	eRamRingBuffer* m_ring;
};

#endif // __lib_dvb_eramtimeshift_h