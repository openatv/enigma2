#ifndef __lib_service_cea608_h
#define __lib_service_cea608_h

#include <stdint.h>
#include <stddef.h>
#include <string>
#include <vector>
#include <map>

/*
 * Minimal CEA-608 closed caption decoder (data channel 1 / CC1).
 * Input are the byte pairs carried in CEA-708 cc_data / A53 user data /
 * SMPTE S334-1A payloads (parity bits still set); output is the current
 * caption display as UTF-8 text lines.
 * CEA-708 DTVCC service data is not decoded. Only streams carrying a
 * CEA-608 compatibility feed are supported here.
 */
class eCea608Decoder
{
public:
	enum
	{
		PAYLOAD_CEA608_RAW = 0,     /* plain byte pairs */
		PAYLOAD_CEA608_S334_1A = 1, /* SMPTE S334-1A triplets */
		PAYLOAD_CEA708_RAW = 2,     /* CEA-708 cc_data triplets */
		PAYLOAD_CEA708_CDP = 3,     /* SMPTE 334-2 CDP packets */
	};

	/* extract the CEA-608 field 1 byte pairs out of a caption payload */
	static void extractField1Pairs(int payload_type, const uint8_t *data, size_t size, std::vector<uint16_t> &pairs);

	eCea608Decoder();
	void reset();
	/* feed one CEA-608 byte pair (as broadcast, parity bits included) */
	void processPair(uint8_t b1, uint8_t b2);
	/* returns true when the visible caption changed since the last call;
	 * text is the whole display, rows joined with newlines, empty = hide */
	bool takeDisplayIfChanged(std::string &text);
	/** Forget the output comparison after expiry, preserving both caption memories. */
	static bool hasCaptionData(const std::vector<uint16_t> &pairs)
	{
		for (uint16_t pair : pairs)
			if (pair & 0x7f7f)
				return true;
		return false;
	}
	/** Allow a fresh caption with the previous wording after display expiry. */
	void forgetDisplay() { m_last_emitted.clear(); }

private:
	enum { ROWS = 15, COLS = 32 };
	enum Mode { MODE_POP_ON, MODE_ROLL_UP, MODE_PAINT_ON };

	std::string m_disp[ROWS][COLS]; /* displayed memory */
	std::string m_back[ROWS][COLS]; /* non-displayed (pop-on) memory */
	Mode m_mode;
	int m_rollup_rows;
	int m_row;
	int m_col;
	int m_channel;
	bool m_text_mode;
	bool m_changed;
	bool m_force_emit;
	uint16_t m_last_control;
	std::string m_last_emitted;

	void clearBuf(std::string (*buf)[COLS]);
	std::string (*captionBuf())[COLS];
	void putChar(const char *utf8);
	void backspace();
	void carriageReturn();
	void control(uint8_t b2);
	void pac(uint8_t b1, uint8_t b2);
	std::string buildText() const;
};

/* A parser can put the PTS only on the first NAL of an access unit, while
 * caption SEI NALs retain the same DTS but have no PTS. Never substitute DTS
 * for PTS (B frames differ), or carry a timestamp across an access unit/flush.
 * Values use GstClockTime's uint64 representation; UINT64_MAX means unknown.
 */
class eCea608Timestamp
{
public:
	/** Convert the sink's offset-adjusted decoder clock back to buffer PTS. */
	static uint64_t rawTime(uint64_t clock, uint64_t start, uint64_t position)
	{
		if (clock == UINT64_MAX || start == UINT64_MAX || position == UINT64_MAX || clock < position)
			return UINT64_MAX;
		uint64_t delta = clock - position;
		return start > UINT64_MAX - delta ? UINT64_MAX : start + delta;
	}
	eCea608Timestamp() { reset(); }
	void reset() { m_pts = m_dts = UINT64_MAX; }
	uint64_t resolve(uint64_t pts, uint64_t dts, bool discontinuity = false)
	{
		if (discontinuity)
			reset();
		if (pts != UINT64_MAX)
		{
			m_pts = pts;
			m_dts = dts;
			return pts;
		}
		if (dts != UINT64_MAX && dts == m_dts)
			return m_pts;
		reset();
		return UINT64_MAX;
	}
private:
	uint64_t m_pts, m_dts;
};

/* Video sinks may read far ahead before the user selects CC. Keep collection
 * and clocked decoding independent from visibility. Caller provides locking.
 * Never consume using demux/query position: it can be far ahead of the video.
 */
class eCea608Playback
{
public:
	eCea608Playback() { reset(); }
	void reset()
	{
		m_queue.clear();
		m_decoder.reset();
		m_text.clear();
		m_visible = false;
		m_changed_at = -1;
	}
	bool enqueue(int64_t ms, uint16_t pair)
	{
		/* The decoder treats parity-only pairs as a strict no-op (including
		 * duplicate-control state). Do not let video-rate padding occupy the
		 * bounded queue and displace real captions during sink read-ahead. */
		if ((pair & 0x7f7f) == 0)
			return true;
		/* Retain imminent captions if read-ahead exceeds the fixed bound.
		 * Dropping the oldest would discard what is about to be displayed. */
		if (m_queue.size() >= 8192)
			return false;
		m_queue.emplace(ms, pair);
		return true;
	}
	size_t pending() const { return m_queue.size(); }
	bool advance(int64_t ms, bool visible, std::string &text, bool paused = false)
	{
		if (paused)
		{
			m_visible = false;
			return false;
		}
		while (!m_queue.empty() && m_queue.begin()->first <= ms + 20)
		{
			auto it = m_queue.begin();
			m_decoder.processPair(it->second >> 8, it->second & 255);
			m_queue.erase(it);
		}
		std::string updated;
		bool changed = m_decoder.takeDisplayIfChanged(updated);
		if (changed)
		{
			m_text = updated;
			m_changed_at = ms;
		}
		if (m_changed_at >= 0 && ms - m_changed_at >= 10000 && !m_text.empty())
		{
			m_text.clear();
			m_decoder.forgetDisplay();
			changed = true;
		}
		const bool render = visible && (changed || !m_visible);
		m_visible = visible;
		if (render)
			text = m_text;
		return render;
	}
	void hide() { m_visible = false; }
private:
	std::multimap<int64_t, uint16_t> m_queue;
	eCea608Decoder m_decoder;
	std::string m_text;
	bool m_visible;
	int64_t m_changed_at;
};

#endif
