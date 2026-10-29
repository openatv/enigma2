#ifndef __lib_service_dabaudioframe_h
#define __lib_service_dabaudioframe_h

#include <cstddef>
#include <cstdint>
#include <string>

/* Source format, independent of the decoder's PCM output or sink caps. */
struct eDABAudioFormat
{
	enum Codec { Unknown, AACLC, HEAAC, HEAACv2, MP2 };
	enum Mode { UnknownMode = -1, Stereo, JointStereo, DualChannel, Mono, Surround51, Surround71, Surround };
	Codec codec = Unknown;
	Mode mode = UnknownMode;
	unsigned sampleRate = 0;

	void setAAC(uint8_t config)
	{
		const bool sbr = config & 0x20;
		const bool ps = sbr && (config & 0x08);
		codec = sbr ? (ps ? HEAACv2 : HEAAC) : AACLC;
		sampleRate = config & 0x40 ? 48000 : 32000;
		const unsigned surround = config & 7;
		mode = surround ? (surround == 1 ? Surround51 : surround == 2 ? Surround71 : Surround) :
			((config & 0x10) || ps ? Stereo : Mono);
	}

	/* Welle reports these values only when its source format changes. */
	void setMetadata(const std::string &name, unsigned rate, const std::string &channelMode)
	{
		*this = eDABAudioFormat();
		if (name == "AAC-LC") codec = AACLC;
		else if (name == "HE-AAC") codec = HEAAC;
		else if (name == "HE-AAC v2") codec = HEAACv2;
		else if (name == "MPEG 1.0 Layer II" || name == "MPEG 2.0 Layer II") codec = MP2;
		if (codec == Unknown || (rate != 16000 && rate != 22050 && rate != 24000 &&
			rate != 32000 && rate != 44100 && rate != 48000) ||
			(codec != MP2 && rate != 32000 && rate != 48000))
		{
			*this = eDABAudioFormat();
			return;
		}
		sampleRate = rate;
		if (channelMode == "Stereo") mode = Stereo;
		else if (channelMode == "Joint Stereo") mode = JointStereo;
		else if (channelMode == "Dual Channel") mode = DualChannel;
		else if (channelMode == "Mono") mode = Mono;
		else if (channelMode.find("Surround 5.1 (") == 0) mode = Surround51;
		else if (channelMode.find("Surround 7.1 (") == 0) mode = Surround71;
		else if (channelMode.compare(0, 9, "Surround ") == 0) mode = Surround;
	}

	const char *codecName() const
	{
		switch (codec)
		{
		case AACLC: return "DAB+ AAC-LC";
		case HEAAC: return "DAB+ HE-AAC";
		case HEAACv2: return "DAB+ HE-AAC v2";
		case MP2: return "DAB MPEG Audio Layer II";
		default: return "";
		}
	}

	const char *modeName() const
	{
		switch (mode)
		{
		case Stereo: return "stereo";
		case JointStereo: return "joint-stereo";
		case DualChannel: return "dual-channel";
		case Mono: return "mono";
		case Surround51: return "surround-5.1";
		case Surround71: return "surround-7.1";
		case Surround: return "surround";
		default: return "";
		}
	}

	bool operator!=(const eDABAudioFormat &other) const
	{
		return codec != other.codec || mode != other.mode || sampleRate != other.sampleRate;
	}
};

/* Shared AAC/MP2 framing for RTL-SDR byte streams and native DAB MSC blocks.
 * Pipe reads need not coincide with AAC/MP2 frames or even complete headers. */
struct eDABAudioFrame
{
	enum Result { Invalid, Incomplete, Complete };
	size_t length = 0;
	uint64_t durationNs = 0;
	bool dabplus = true;
	eDABAudioFormat format;

	Result parse(const uint8_t *data, size_t size)
	{
		length = 0;
		durationNs = 0;
		dabplus = true;
		format = eDABAudioFormat();
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
			format.codec = eDABAudioFormat::MP2;
			format.sampleRate = rate;
			format.mode = static_cast<eDABAudioFormat::Mode>((data[3] >> 6) & 3);
		}
		else
			return Invalid;
		return size < length ? Incomplete : Complete;
	}
};

#endif
