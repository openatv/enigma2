#ifndef __servicewebvtt_h
#define __servicewebvtt_h

#include <cstdint>
#include <string>
#include <vector>

#include <lib/service/servicemp3.h>

/**
 * @struct WebVTTSubtitleEntry
 * @brief Represents a single WebVTT subtitle entry with timing and text information.
 *
 * This structure holds the timing information (start and end times in milliseconds),
 * a base timestamp for MPEG-TS to WebVTT conversion, and the subtitle text itself.
 */
struct WebVTTSubtitleEntry {
	uint64_t start_time_ms;
	uint64_t end_time_ms;
	uint64_t vtt_mpegts_base;
	uint64_t local_offset_ms;
	std::string text;
};

/**
 * @class WebVTTParser
 * @brief Parser for WebVTT subtitle format with HLS/MPEG-TS timestamp mapping support.
 *
 * This class handles parsing of WebVTT subtitle data, including support for
 * X-TIMESTAMP-MAP headers used in HLS streams to synchronize subtitles with
 * MPEG-TS timestamps.
 */
class WebVTTParser {
public:
	WebVTTParser();

	/**
	 * @brief Parses WebVTT subtitle data and extracts subtitle entries.
	 *
	 * @param vtt_data The input string containing the WebVTT subtitle data.
	 * @param subs_out Output vector to which parsed entries will be appended.
	 * @return true if at least one subtitle entry was successfully parsed.
	 */
	bool parse(const std::string& vtt_data, std::vector<WebVTTSubtitleEntry>& subs_out);

	/**
	 * @brief Resets the parser state for MPEGTS jump detection.
	 *
	 * Call this when starting a new stream to clear the persistent state
	 * used for detecting backward jumps in MPEGTS timestamps.
	 */
	void reset();

private:
	/**
	 * @brief Parses a timecode string in the format "HH:MM:SS.mmm" into milliseconds.
	 */
	static bool parseTimecode(const std::string& s, uint64_t& ms_out);

	// Persistent state for detecting MPEGTS jumps between segments
	uint64_t m_last_mpegts_ms;
	bool m_has_last_mpegts;
};

/**
 * @struct WebVTTState
 * @brief Holds the runtime state for WebVTT subtitle synchronization.
 *
 * This structure encapsulates the state variables needed to synchronize
 * WebVTT subtitles with the video decoder, particularly for live streams.
 */
struct WebVTTState {
	int64_t initial_mpegts = 0;
	int64_t live_base_time = -1;
	bool is_live = false;
	int64_t base_mpegts = -1;

	/**
	 * @brief Resets all state variables to their initial values.
	 */
	void reset() {
		initial_mpegts = 0;
		live_base_time = -1;
		is_live = false;
		base_mpegts = -1;
	}
};

#endif /* __servicewebvtt_h */
