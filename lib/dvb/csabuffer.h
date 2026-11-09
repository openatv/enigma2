#ifndef __dvbcsabuffer_h
#define __dvbcsabuffer_h

#include <lib/base/thread.h>

#include <stdint.h>
#include <stddef.h>
#include <atomic>
#include <condition_variable>
#include <functional>
#include <mutex>

/**
 * eDVBCSABuffer - Playback delay for SoftCSA
 *
 * push() queues timestamped chunks and returns at once. This thread releases
 * a chunk once it is older than the delay and descrambles it then, by which
 * time even a late CW has arrived.
 */
class eDVBCSABuffer: public eThread
{
public:
	/* max_chunk is the largest chunk push() will be given. */
	eDVBCSABuffer(int delay_ms, size_t max_chunk);
	~eDVBCSABuffer();

	/* Hand a released chunk on. Set before start(). */
	void setConsumer(std::function<void(unsigned char*, int)> fn) { m_consume = std::move(fn); }

	bool start();
	void stop();

	/* Filepush thread. Copies and returns; false if the chunk was dropped. */
	bool push(const unsigned char *data, int len);

	int    delayMs() const
	{
		return (int)(m_delay_us.load() / 1000);
	}

	/* The ceiling the delay may grow to while the stream is held. */
	/* Headroom over what a hold measured, against the jitter of the next. */
	static const uint64_t HOLD_MARGIN_US = 200000;

	void setMaxDelayMs(int max_ms) { m_max_delay_us = (uint64_t)max_ms * 1000; }

	/* Nothing comes out while this is set, and the chunks stay put, so this
	 * is what grows the delay. Bounded by the ceiling. Consumer thread only. */
	void setHold(bool hold) { m_hold = hold; }
	bool holding() const { return m_holding; }

	/* Asked while held, since setHold() would not hear a word arrive.
	 * Set before start(). */
	void setHoldQuery(std::function<bool()> fn) { m_hold_query = std::move(fn); }

	/* True once, for the first chunk released after the stream was held. */
	bool takeDelayGrown() { const bool b = m_grown_now; m_grown_now = false; return b; }

	/* How long that hold lasted, in ms. */
	int heldMs() const { return m_held_ms; }
	int    offsetMs() const
	{
		return m_offset_ms.load();
	}
	size_t used() const;
	size_t size() const;

private:
	/* len == 0 marks the wrap: reading continues at offset 0. */
	struct ChunkHdr
	{
		uint64_t stamp_us;
		uint32_t len;
	};

	void thread() override;

	/* All of these expect m_lock to be held. */
	size_t sizeFor(uint64_t delay_us) const;
	size_t capFor(uint64_t delay_us) const;
	bool reserve(size_t want);
	bool grow(size_t inuse, size_t need);
	bool fits(size_t need, bool &wrap) const;
	size_t nextChunkPos(size_t pos, uint32_t &len, uint64_t &stamp) const;

	void logSummary() const;

	unsigned char *m_buf{nullptr};

	// One chunk plus its header. A chunk is never split, so a short tail is dead.
	const size_t m_slot;

	size_t m_size{0};
	size_t m_max_size{0};
	size_t m_read_pos{0};  /* oldest chunk not yet released */
	size_t m_write_pos{0};

	/* The consumer copies out, so the ring may be reallocated any time. */
	unsigned char *m_work{nullptr};
	size_t m_work_size{0};

	std::function<void(unsigned char*, int)> m_consume;

	std::atomic<uint64_t> m_delay_us{0};
	int m_stop{1};
	std::atomic<int> m_offset_ms{0};
	std::atomic<bool> m_hold{false};
	std::function<bool()> m_hold_query;
	uint64_t m_max_delay_us{5000000};
	bool m_holding{false};     // this thread only
	bool m_grown_now{false};   // this thread only
	bool m_gave_up{false};     // this thread only
	int m_held_ms{0};          // this thread only
	uint64_t m_hold_start_us{0};  // this thread only

	/* Statistics, reported once on stop(). */
	uint64_t m_start_us{0};
	uint64_t m_bytes_in{0};  // whole run, for the summary line
	uint64_t m_chunks{0};
	uint64_t m_dropped{0};
	uint64_t m_last_out_us{0};  // last delivery, for spotting gaps we cause
	unsigned int m_gaps{0};  // log rate limit only

	mutable std::mutex m_lock;
	std::condition_variable m_cond;
};

#endif // __dvbcsabuffer_h
