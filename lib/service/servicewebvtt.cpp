/*
 * WebVTT subtitle parser for Enigma2
 *
 * Copyright (c) 2025 jbleyel and others
 * Licensed under GPLv2.
 */

#include <lib/base/eerror.h>
#include <lib/service/servicewebvtt.h>

#include <cstdio>
#include <sstream>

WebVTTParser::WebVTTParser()
	: m_last_mpegts_ms(0)
	, m_has_last_mpegts(false)
{
}

void WebVTTParser::reset()
{
	m_last_mpegts_ms = 0;
	m_has_last_mpegts = false;
}

bool WebVTTParser::parseTimecode(const std::string& s, uint64_t& ms_out)
{
	unsigned h = 0, m = 0, sec = 0, ms = 0;
	if (sscanf(s.c_str(), "%u:%u:%u.%u", &h, &m, &sec, &ms) == 4) {
		ms_out = ((h * 3600 + m * 60 + sec) * 1000 + ms);
		return true;
	}
	return false;
}

bool WebVTTParser::parse(const std::string& vtt_data, std::vector<WebVTTSubtitleEntry>& subs_out)
{
	std::istringstream stream(vtt_data);
	std::string line;

	std::string current_text;
	uint64_t start_ms = 0, end_ms = 0, vtt_mpegts_base = 0, local_offset_ms = 0;
	bool expecting_text = false;

	while (std::getline(stream, line)) {
		if (!line.empty() && line.back() == '\r')
			line.pop_back();
		if (line.empty())
			continue;

		if (line.rfind("X-TIMESTAMP-MAP=", 0) == 0) {
			size_t mpegts_pos = line.find("MPEGTS:");
			size_t local_pos = line.find("LOCAL:");

			if (mpegts_pos != std::string::npos && local_pos != std::string::npos) {
				mpegts_pos += 7;
				local_pos += 6;

				size_t comma_pos = line.find(',', mpegts_pos);
				std::string mpegts_str = line.substr(mpegts_pos, comma_pos - mpegts_pos);
				std::string local_str = line.substr(local_pos);

				vtt_mpegts_base = std::stoull(mpegts_str);
				if (vtt_mpegts_base < 1000000) // Ignore less than 1000000
					vtt_mpegts_base = 0;
				parseTimecode(local_str, local_offset_ms);

				// Detect backward jumps in MPEGTS (advertisement -> content switch)
				if (vtt_mpegts_base > 0) {
					const uint64_t local_mpegts_ms = pts90kToMs(vtt_mpegts_base);
					if (m_has_last_mpegts && local_mpegts_ms < m_last_mpegts_ms) {
						// If MPEGTS jump back -> deactivate this segment.
						eDebug("[WebVTTParser] MPEGTS backward jump detected: %llu -> %llu, disabling mapping for this segment",
							   (unsigned long long)m_last_mpegts_ms,
							   (unsigned long long)local_mpegts_ms);
						vtt_mpegts_base = 0; // reset offsets
					}
					m_last_mpegts_ms = local_mpegts_ms;
					m_has_last_mpegts = true;
				}
			}
			continue;
		}

		if (line.find("-->") != std::string::npos) {
			if (!current_text.empty()) {
				WebVTTSubtitleEntry entry;
				entry.start_time_ms = start_ms;
				entry.end_time_ms = end_ms;
				entry.vtt_mpegts_base = vtt_mpegts_base;
				entry.local_offset_ms = local_offset_ms;
				entry.text = current_text;
				subs_out.push_back(entry);
				current_text.clear();
			}

			size_t arrow = line.find("-->");
			std::string start_str = line.substr(0, arrow);
			std::string end_str = line.substr(arrow + 3);
			if (!parseTimecode(start_str, start_ms))
				continue;
			if (!parseTimecode(end_str, end_ms))
				continue;

			expecting_text = true;
			continue;
		}

		if (!expecting_text || line.find_first_not_of("0123456789") == std::string::npos)
			continue;

		if (expecting_text) {
			if (!current_text.empty())
				current_text += "\n";
			current_text += line;
		}
	}

	if (!current_text.empty()) {
		WebVTTSubtitleEntry entry;
		entry.start_time_ms = start_ms;
		entry.end_time_ms = end_ms;
		entry.vtt_mpegts_base = vtt_mpegts_base;
		entry.local_offset_ms = local_offset_ms;
		entry.text = current_text;
		subs_out.push_back(entry);
	}

	return !subs_out.empty();
}
