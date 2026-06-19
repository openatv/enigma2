/* SPDX-License-Identifier: GPL-2.0-only */

#ifndef __lib_dvb_hevc_hdr_parser_h
#define __lib_dvb_hevc_hdr_parser_h

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>

/*
 * Bounded HEVC Annex-B parser for receivers whose video driver does not expose
 * VIDEO_EVENT_GAMMA_CHANGED or /proc/stb/vmpeg/<n>/gamma.
 *
 * Only the syntax required for transfer-function detection is parsed:
 *   - SPS VUI colour_description / transfer_characteristics
 *   - SEI 137 mastering_display_colour_volume
 *   - SEI 144 content_light_level_info (recorded, but not decisive alone)
 *   - SEI 147 alternative_transfer_characteristics
 *
 * Returned values match iServiceInformation::sGamma:
 *   0 = traditional gamma / SDR
 *   2 = SMPTE ST 2084 / HDR10
 *   3 = Hybrid Log-Gamma
 *
 * Gamma value 1 cannot be inferred unambiguously from these HEVC fields and is
 * intentionally left to the native driver.
 */
class eHEVCHDRParser
{
public:
	enum Gamma
	{
		GammaUnknown = -1,
		GammaSDR = 0,
		GammaHDR10 = 2,
		GammaHLG = 3
	};

	eHEVCHDRParser()
	{
		reset();
	}

	void reset()
	{
		m_nal.clear();
		m_zero_count = 0;
		m_bytes_seen = 0;
		m_scan_complete = false;
		m_header_bytes = 0;
		m_nal_type = -1;
		m_in_nal = false;
		m_capture = false;
		m_capture_overflow = false;
		m_gamma = GammaUnknown;
		m_vui_transfer = -1;
		m_alternative_transfer = -1;
		m_mastering_display = false;
		m_content_light = false;
		m_sps_count = 0;
		m_authoritative = false;
		m_pes_buffer.clear();
		m_pes_state = PESFindStart;
		m_pes_payload_remaining = 0;
	}

	/* Feed arbitrary chunks of HEVC Annex-B elementary-stream data. */
	int feed(const uint8_t *data, size_t length)
	{
		if (!data || !length || m_gamma != GammaUnknown || m_scan_complete)
			return m_gamma;

		for (size_t i = 0; i < length && m_gamma == GammaUnknown && !m_scan_complete; ++i)
		{
			const uint8_t value = data[i];
			++m_bytes_seen;

			if (value == 0)
			{
				++m_zero_count;
				if (m_bytes_seen >= MaxScanBytes)
				{
					m_zero_count = 0;
					finishNAL();
					updateResult(true);
					m_scan_complete = true;
				}
				continue;
			}

			if (value == 1 && m_zero_count >= 2)
			{
				finishNAL();
				beginNAL();
				m_zero_count = 0;
				continue;
			}

			while (m_zero_count)
			{
				processNALByte(0);
				--m_zero_count;
			}
			processNALByte(value);

			if (m_bytes_seen >= MaxScanBytes)
			{
				m_zero_count = 0;
				finishNAL();
				updateResult(true);
				m_scan_complete = true;
				break;
			}
		}
		return m_gamma;
	}

	/*
	 * Feed arbitrary chunks returned by iDVBPESReader.  Video PES packets are
	 * stripped before the Annex-B scanner sees the payload.  This matters for
	 * PES_packet_length == 0, where a NAL unit may span several PES packets.
	 */
	int feedPES(const uint8_t *data, size_t length)
	{
		if (!data || !length || m_gamma != GammaUnknown)
			return m_gamma;

		while (length && m_gamma == GammaUnknown)
		{
			const size_t chunk = length < MaxPESAppend ? length : MaxPESAppend;
			m_pes_buffer.insert(m_pes_buffer.end(), data, data + chunk);
			data += chunk;
			length -= chunk;
			processPESBuffer();
		}
		return m_gamma;
	}

	/* Finalize the pending PES payload and then the current NAL unit. */
	int finishPES()
	{
		if (m_gamma == GammaUnknown)
		{
			processPESBuffer();
			if (m_pes_state == PESBoundedPayload)
			{
				const size_t payload = std::min(m_pes_buffer.size(), m_pes_payload_remaining);
				if (payload)
					feed(m_pes_buffer.data(), payload);
			}
			else if (m_pes_state == PESUnboundedPayload && !m_pes_buffer.empty())
				feed(m_pes_buffer.data(), m_pes_buffer.size());
		}
		m_pes_buffer.clear();
		m_pes_state = PESFindStart;
		m_pes_payload_remaining = 0;
		return finish();
	}

	/* Finalize a bounded elementary-stream scan. */
	int finish()
	{
		if (m_gamma == GammaUnknown && !m_scan_complete)
		{
			while (m_zero_count)
			{
				processNALByte(0);
				--m_zero_count;
			}
			finishNAL();
			updateResult(true);
		}
		return m_gamma;
	}

	bool resultIsAuthoritative() const
	{
		return m_authoritative;
	}

	bool hasSPS() const
	{
		return m_sps_count != 0;
	}

private:
	enum PESState
	{
		PESFindStart,
		PESReadHeader,
		PESBoundedPayload,
		PESUnboundedPayload
	};

	static const size_t MaxCapturedNAL = 64 * 1024;
	static const size_t MaxScanBytes = 64 * 1024 * 1024;
	static const size_t MaxPESAppend = 64 * 1024;
	static const size_t NotFound = std::numeric_limits<size_t>::max();

	static size_t findVideoPESStart(const std::vector<uint8_t> &buffer, size_t start = 0)
	{
		if (buffer.size() < 4 || start > buffer.size() - 4)
			return NotFound;
		for (size_t i = start; i + 3 < buffer.size(); ++i)
		{
			if (buffer[i] == 0 && buffer[i + 1] == 0 && buffer[i + 2] == 1 &&
				(buffer[i + 3] & 0xf0) == 0xe0)
				return i;
		}
		return NotFound;
	}

	void erasePESPrefix(size_t count)
	{
		if (count)
			m_pes_buffer.erase(m_pes_buffer.begin(), m_pes_buffer.begin() + count);
	}

	void processPESBuffer()
	{
		while (m_gamma == GammaUnknown)
		{
			if (m_pes_state == PESFindStart)
			{
				const size_t start = findVideoPESStart(m_pes_buffer);
				if (start == NotFound)
				{
					if (m_pes_buffer.size() > 3)
						erasePESPrefix(m_pes_buffer.size() - 3);
					return;
				}
				erasePESPrefix(start);
				m_pes_state = PESReadHeader;
			}

			if (m_pes_state == PESReadHeader)
			{
				if (m_pes_buffer.size() < 9)
					return;
				if (findVideoPESStart(m_pes_buffer) != 0 || (m_pes_buffer[6] & 0xc0) != 0x80)
				{
					erasePESPrefix(1);
					m_pes_state = PESFindStart;
					continue;
				}

				const size_t packet_length = (static_cast<size_t>(m_pes_buffer[4]) << 8) | m_pes_buffer[5];
				const size_t bytes_after_length_before_payload = 3 + m_pes_buffer[8];
				const size_t payload_offset = 6 + bytes_after_length_before_payload;
				if (packet_length && packet_length < bytes_after_length_before_payload)
				{
					erasePESPrefix(4);
					m_pes_state = PESFindStart;
					continue;
				}
				if (m_pes_buffer.size() < payload_offset)
					return;

				erasePESPrefix(payload_offset);
				if (packet_length)
				{
					m_pes_payload_remaining = packet_length - bytes_after_length_before_payload;
					m_pes_state = m_pes_payload_remaining ? PESBoundedPayload : PESFindStart;
				}
				else
					m_pes_state = PESUnboundedPayload;
			}

			if (m_pes_state == PESBoundedPayload)
			{
				const size_t payload = std::min(m_pes_buffer.size(), m_pes_payload_remaining);
				if (payload)
				{
					feed(m_pes_buffer.data(), payload);
					erasePESPrefix(payload);
					m_pes_payload_remaining -= payload;
				}
				if (m_gamma != GammaUnknown)
					return;
				if (m_pes_payload_remaining)
					return;
				m_pes_state = PESFindStart;
				continue;
			}

			if (m_pes_state == PESUnboundedPayload)
			{
				const size_t next = findVideoPESStart(m_pes_buffer);
				if (next != NotFound)
				{
					if (next)
						feed(m_pes_buffer.data(), next);
					erasePESPrefix(next);
					m_pes_state = PESReadHeader;
					continue;
				}
				if (m_pes_buffer.size() > 3)
				{
					const size_t payload = m_pes_buffer.size() - 3;
					feed(m_pes_buffer.data(), payload);
					erasePESPrefix(payload);
				}
				return;
			}
		}
	}

	class BitReader
	{
	public:
		BitReader(const uint8_t *data, size_t size)
			: m_bit_position(0)
		{
			m_data.reserve(size);
			unsigned int zeros = 0;
			for (size_t i = 0; i < size; ++i)
			{
				const uint8_t value = data[i];
				if (zeros >= 2 && value == 0x03 && i + 1 < size && data[i + 1] <= 0x03)
				{
					zeros = 2;
					continue;
				}
				m_data.push_back(value);
				zeros = value == 0 ? zeros + 1 : 0;
			}
		}

		bool readBit(uint32_t &value)
		{
			if (m_bit_position >= m_data.size() * 8)
				return false;
			value = (m_data[m_bit_position >> 3] >> (7 - (m_bit_position & 7))) & 1;
			++m_bit_position;
			return true;
		}

		bool readBits(unsigned int count, uint32_t &value)
		{
			if (count > 32 || m_bit_position + count > m_data.size() * 8)
				return false;
			value = 0;
			for (unsigned int i = 0; i < count; ++i)
			{
				value <<= 1;
				value |= (m_data[m_bit_position >> 3] >> (7 - (m_bit_position & 7))) & 1;
				++m_bit_position;
			}
			return true;
		}

		bool skipBits(size_t count)
		{
			if (m_bit_position + count > m_data.size() * 8)
				return false;
			m_bit_position += count;
			return true;
		}

		bool readUE(uint32_t &value, uint32_t limit = std::numeric_limits<uint32_t>::max())
		{
			unsigned int leading_zero_bits = 0;
			uint32_t bit = 0;
			while (true)
			{
				if (!readBit(bit))
					return false;
				if (bit)
					break;
				if (++leading_zero_bits > 31)
					return false;
			}

			uint32_t suffix = 0;
			if (leading_zero_bits && !readBits(leading_zero_bits, suffix))
				return false;
			const uint64_t decoded = ((uint64_t)1 << leading_zero_bits) - 1 + suffix;
			if (decoded > limit)
				return false;
			value = static_cast<uint32_t>(decoded);
			return true;
		}

		bool readSE(int32_t &value, uint32_t limit = 0x7fffffffU)
		{
			uint32_t code_num = 0;
			if (!readUE(code_num, limit * 2U))
				return false;
			value = (code_num & 1) ? static_cast<int32_t>((code_num + 1) >> 1) : -static_cast<int32_t>(code_num >> 1);
			return true;
		}

	private:
		std::vector<uint8_t> m_data;
		size_t m_bit_position;
	};

	static bool skipProfileTierLevel(BitReader &bits, uint32_t max_sub_layers_minus1)
	{
		if (max_sub_layers_minus1 > 6 || !bits.skipBits(96))
			return false;

		bool sub_layer_profile_present[7] = {};
		bool sub_layer_level_present[7] = {};
		uint32_t value = 0;
		for (uint32_t i = 0; i < max_sub_layers_minus1; ++i)
		{
			if (!bits.readBit(value))
				return false;
			sub_layer_profile_present[i] = value != 0;
			if (!bits.readBit(value))
				return false;
			sub_layer_level_present[i] = value != 0;
		}
		if (max_sub_layers_minus1 && !bits.skipBits((8 - max_sub_layers_minus1) * 2))
			return false;
		for (uint32_t i = 0; i < max_sub_layers_minus1; ++i)
		{
			if (sub_layer_profile_present[i] && !bits.skipBits(88))
				return false;
			if (sub_layer_level_present[i] && !bits.skipBits(8))
				return false;
		}
		return true;
	}

	static bool skipScalingListData(BitReader &bits)
	{
		uint32_t flag = 0;
		uint32_t value = 0;
		int32_t signed_value = 0;
		for (uint32_t size_id = 0; size_id < 4; ++size_id)
		{
			for (uint32_t matrix_id = 0; matrix_id < 6; matrix_id += size_id == 3 ? 3 : 1)
			{
				if (!bits.readBit(flag))
					return false;
				if (!flag)
				{
					if (!bits.readUE(value, matrix_id))
						return false;
				}
				else
				{
					const uint32_t coefficient_count = std::min<uint32_t>(64, 1U << (4 + (size_id << 1)));
					if (size_id > 1 && !bits.readSE(signed_value, 255))
						return false;
					for (uint32_t i = 0; i < coefficient_count; ++i)
						if (!bits.readSE(signed_value, 255))
							return false;
				}
			}
		}
		return true;
	}

	static bool skipShortTermReferencePictureSets(BitReader &bits, uint32_t count)
	{
		if (count > 64)
			return false;
		uint32_t delta_poc_count[64] = {};
		uint32_t flag = 0;
		uint32_t value = 0;
		for (uint32_t set_index = 0; set_index < count; ++set_index)
		{
			bool inter_prediction = false;
			if (set_index)
			{
				if (!bits.readBit(flag))
					return false;
				inter_prediction = flag != 0;
			}
			if (inter_prediction)
			{
				if (!bits.skipBits(1) || !bits.readUE(value, 32767))
					return false;
				const uint32_t reference_count = delta_poc_count[set_index - 1];
				uint32_t current_count = 0;
				for (uint32_t i = 0; i <= reference_count; ++i)
				{
					uint32_t used_by_current = 0;
					uint32_t use_delta = 1;
					if (!bits.readBit(used_by_current))
						return false;
					if (!used_by_current && !bits.readBit(use_delta))
						return false;
					if (used_by_current || use_delta)
						++current_count;
				}
				if (current_count > 64)
					return false;
				delta_poc_count[set_index] = current_count;
			}
			else
			{
				uint32_t negative_count = 0;
				uint32_t positive_count = 0;
				if (!bits.readUE(negative_count, 64) || !bits.readUE(positive_count, 64) || negative_count + positive_count > 64)
					return false;
				delta_poc_count[set_index] = negative_count + positive_count;
				for (uint32_t i = 0; i < negative_count + positive_count; ++i)
					if (!bits.readUE(value, 32767) || !bits.skipBits(1))
						return false;
			}
		}
		return true;
	}

	static std::vector<uint8_t> unescapeRBSP(const std::vector<uint8_t> &ebsp)
	{
		std::vector<uint8_t> rbsp;
		rbsp.reserve(ebsp.size());
		unsigned int zeros = 0;
		for (std::vector<uint8_t>::const_iterator it = ebsp.begin(); it != ebsp.end(); ++it)
		{
			const uint8_t value = *it;
			if (zeros >= 2 && value == 0x03 && it + 1 != ebsp.end() && *(it + 1) <= 0x03)
			{
				zeros = 2;
				continue;
			}
			rbsp.push_back(value);
			zeros = value == 0 ? zeros + 1 : 0;
		}
		return rbsp;
	}

	bool parseSPS(const std::vector<uint8_t> &payload, int &transfer) const
	{
		transfer = -1;
		BitReader bits(payload.data(), payload.size());
		uint32_t value = 0;
		uint32_t max_sub_layers_minus1 = 0;
		if (!bits.skipBits(4) || !bits.readBits(3, max_sub_layers_minus1) || !bits.skipBits(1) ||
			!skipProfileTierLevel(bits, max_sub_layers_minus1))
			return false;

		uint32_t chroma_format_idc = 0;
		if (!bits.readUE(value, 15) || !bits.readUE(chroma_format_idc, 3))
			return false;
		if (chroma_format_idc == 3 && !bits.skipBits(1))
			return false;
		if (!bits.readUE(value, 65535) || !bits.readUE(value, 65535))
			return false;

		uint32_t flag = 0;
		if (!bits.readBit(flag))
			return false;
		if (flag)
			for (unsigned int i = 0; i < 4; ++i)
				if (!bits.readUE(value, 65535))
					return false;

		uint32_t log2_max_pic_order_cnt_lsb_minus4 = 0;
		if (!bits.readUE(value, 8) || !bits.readUE(value, 8) || !bits.readUE(log2_max_pic_order_cnt_lsb_minus4, 12))
			return false;

		if (!bits.readBit(flag))
			return false;
		const uint32_t first_layer = flag ? 0 : max_sub_layers_minus1;
		for (uint32_t i = first_layer; i <= max_sub_layers_minus1; ++i)
			for (unsigned int j = 0; j < 3; ++j)
				if (!bits.readUE(value, 65535))
					return false;

		for (unsigned int i = 0; i < 6; ++i)
			if (!bits.readUE(value, 65535))
				return false;

		if (!bits.readBit(flag))
			return false;
		if (flag)
		{
			if (!bits.readBit(flag))
				return false;
			if (flag && !skipScalingListData(bits))
				return false;
		}

		if (!bits.skipBits(2) || !bits.readBit(flag))
			return false;
		if (flag)
		{
			if (!bits.skipBits(8) || !bits.readUE(value, 31) || !bits.readUE(value, 31) || !bits.skipBits(1))
				return false;
		}

		uint32_t short_term_reference_picture_set_count = 0;
		if (!bits.readUE(short_term_reference_picture_set_count, 64) ||
			!skipShortTermReferencePictureSets(bits, short_term_reference_picture_set_count))
			return false;

		if (!bits.readBit(flag))
			return false;
		if (flag)
		{
			uint32_t long_term_reference_picture_count = 0;
			if (!bits.readUE(long_term_reference_picture_count, 32))
				return false;
			for (uint32_t i = 0; i < long_term_reference_picture_count; ++i)
				if (!bits.skipBits(log2_max_pic_order_cnt_lsb_minus4 + 5))
					return false;
		}

		if (!bits.skipBits(2) || !bits.readBit(flag))
			return false;
		if (!flag)
			return true;

		if (!bits.readBit(flag))
			return false;
		if (flag)
		{
			uint32_t aspect_ratio_idc = 0;
			if (!bits.readBits(8, aspect_ratio_idc))
				return false;
			if (aspect_ratio_idc == 255 && !bits.skipBits(32))
				return false;
		}
		if (!bits.readBit(flag))
			return false;
		if (flag && !bits.skipBits(1))
			return false;
		if (!bits.readBit(flag))
			return false;
		if (!flag)
			return true;
		if (!bits.skipBits(4) || !bits.readBit(flag))
			return false;
		if (!flag)
			return true;

		uint32_t colour_primaries = 0;
		uint32_t transfer_characteristics = 0;
		uint32_t matrix_coefficients = 0;
		if (!bits.readBits(8, colour_primaries) || !bits.readBits(8, transfer_characteristics) ||
			!bits.readBits(8, matrix_coefficients))
			return false;
		transfer = static_cast<int>(transfer_characteristics);
		return true;
	}

	void parseSEI(const std::vector<uint8_t> &payload)
	{
		const std::vector<uint8_t> rbsp = unescapeRBSP(payload);
		size_t position = 0;
		while (position + 1 < rbsp.size())
		{
			if (rbsp[position] == 0x80)
				break;

			uint32_t payload_type = 0;
			while (position < rbsp.size() && rbsp[position] == 0xff)
			{
				if (payload_type > 0xffff - 255)
					return;
				payload_type += 255;
				++position;
			}
			if (position >= rbsp.size())
				return;
			payload_type += rbsp[position++];

			uint32_t payload_size = 0;
			while (position < rbsp.size() && rbsp[position] == 0xff)
			{
				if (payload_size > 0xffff - 255)
					return;
				payload_size += 255;
				++position;
			}
			if (position >= rbsp.size())
				return;
			payload_size += rbsp[position++];
			if (payload_size > rbsp.size() - position)
				return;

			if (payload_type == 137 && payload_size >= 24)
				m_mastering_display = true;
			else if (payload_type == 144 && payload_size >= 4)
				m_content_light = true;
			else if (payload_type == 147 && payload_size >= 1)
				m_alternative_transfer = rbsp[position];
			position += payload_size;
		}
	}

	void beginNAL()
	{
		m_in_nal = true;
		m_header_bytes = 0;
		m_nal_type = -1;
		m_capture = false;
		m_capture_overflow = false;
		m_nal.clear();
	}

	void processNALByte(uint8_t value)
	{
		if (!m_in_nal)
			return;
		if (m_header_bytes < 2)
		{
			if (m_header_bytes++ == 0)
			{
				m_nal_type = (value >> 1) & 0x3f;
				m_capture = m_nal_type == 33 || m_nal_type == 39 || m_nal_type == 40;
			}
			return;
		}
		if (!m_capture || m_capture_overflow)
			return;
		if (m_nal.size() >= MaxCapturedNAL)
		{
			m_nal.clear();
			m_capture_overflow = true;
			return;
		}
		m_nal.push_back(value);
	}

	void finishNAL()
	{
		if (!m_in_nal || m_header_bytes < 2 || !m_capture || m_capture_overflow)
		{
			m_in_nal = false;
			return;
		}

		if (m_nal_type == 33)
		{
			int transfer = -1;
			if (parseSPS(m_nal, transfer))
			{
				++m_sps_count;
				if (transfer >= 0)
					m_vui_transfer = transfer;
			}
		}
		else if (m_nal_type == 39 || m_nal_type == 40)
			parseSEI(m_nal);
		m_in_nal = false;
		updateResult(false);
	}

	void updateResult(bool final)
	{
		if (m_gamma != GammaUnknown)
			return;
		if (m_alternative_transfer == 18 || m_vui_transfer == 18)
		{
			m_gamma = GammaHLG;
			m_authoritative = true;
		}
		else if (m_alternative_transfer == 16 || m_vui_transfer == 16 || m_mastering_display)
		{
			m_gamma = GammaHDR10;
			m_authoritative = true;
		}
		else if (final && m_sps_count)
		{
			m_gamma = GammaSDR;
			m_authoritative = false;
		}
	}

	std::vector<uint8_t> m_nal;
	size_t m_zero_count;
	size_t m_bytes_seen;
	unsigned int m_header_bytes;
	int m_nal_type;
	bool m_in_nal;
	bool m_capture;
	bool m_capture_overflow;
	bool m_scan_complete;
	int m_gamma;
	int m_vui_transfer;
	int m_alternative_transfer;
	bool m_mastering_display;
	bool m_content_light;
	unsigned int m_sps_count;
	bool m_authoritative;

	std::vector<uint8_t> m_pes_buffer;
	PESState m_pes_state;
	size_t m_pes_payload_remaining;
};

#endif
