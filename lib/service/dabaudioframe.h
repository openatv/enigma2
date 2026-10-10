#ifndef __lib_service_dabaudioframe_h
#define __lib_service_dabaudioframe_h

#include <cstddef>
#include <cstdint>

/* Framing of the compressed byte stream supplied by the RTL-SDR backend.
 * Pipe reads need not coincide with AAC/MP2 frames or even complete headers. */
struct eDABAudioFrame
{
	enum Result { Invalid, Incomplete, Complete };
	size_t length = 0;
	uint64_t durationNs = 0;
	bool dabplus = true;

	Result parse(const uint8_t *data, size_t size)
	{
		length = 0;
		durationNs = 0;
		dabplus = true;
		if (!size)
			return Incomplete;
		if (data[0] == 0x56)
		{
			if (size < 2)
				return Incomplete;
			if ((data[1] & 0xe0) != 0xe0)
				return Invalid;
			if (size < 3)
				return Incomplete;
			length = 3 + ((static_cast<size_t>(data[1] & 0x1f) << 8) | data[2]);
			if (length == 3)
				return Invalid;
		}
		else if (data[0] == 0xff)
		{
			if (size < 2)
				return Incomplete;
			const unsigned version = (data[1] >> 3) & 3;
			if ((data[1] & 0xe0) != 0xe0 || ((data[1] >> 1) & 3) != 2 || version < 2)
				return Invalid;
			if (size < 4)
				return Incomplete;
			const unsigned bitrateIndex = data[2] >> 4;
			const unsigned rateIndex = (data[2] >> 2) & 3;
			if (!bitrateIndex || bitrateIndex == 15 || rateIndex == 3)
				return Invalid;
			static const unsigned bitrates[2][15] = {
				{0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160},
				{0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384}
			};
			static const unsigned rates[3] = {44100, 48000, 32000};
			const unsigned rate = rates[rateIndex] / (version == 3 ? 1 : 2);
			length = 144000 * bitrates[version == 3 ? 1 : 0][bitrateIndex] / rate + ((data[2] >> 1) & 1);
			durationNs = 1152000000000ULL / rate;
			dabplus = false;
		}
		else
			return Invalid;
		return size < length ? Incomplete : Complete;
	}
};

#endif
