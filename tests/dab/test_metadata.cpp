#include <lib/service/dabdecoder.h>
#include <algorithm>
#include <array>
#include <initializer_list>
#include <cassert>
#include <fstream>
#include <iostream>

static uint16_t crc(const uint8_t *data, size_t length)
{
	uint16_t value = 0xffff;
	for (size_t i = 0; i < length; ++i)
	{
		value ^= static_cast<uint16_t>(data[i]) << 8;
		for (int j = 0; j < 8; ++j)
			value = (value << 1) ^ ((value & 0x8000) ? 0x1021 : 0);
	}
	return value ^ 0xffff;
}

static void appendCRC(uint8_t *data, size_t length)
{
	const uint16_t value = crc(data, length);
	data[length] = value >> 8;
	data[length + 1] = value & 0xff;
}

/* Send a FIG through the public ETI path, including valid header, FIB and MST CRCs. */
static void fig(eDABDecoder &decoder, std::initializer_list<uint8_t> payload)
{
	assert(payload.size() <= 29);
	std::array<uint8_t, 110> frame{};
	frame[0] = 0xff; frame[1] = 0x07; frame[2] = 0x3a; frame[3] = 0xb6;
	frame[5] = 0x80; frame[6] = 0x08; frame[7] = 27;
	appendCRC(frame.data() + 4, 6);
	for (int offset = 12; offset < 108; offset += 32)
	{
		std::fill(frame.begin() + offset, frame.begin() + offset + 30, 0xff);
		if (offset == 12)
		{
			frame[offset] = payload.size();
			std::copy(payload.begin(), payload.end(), frame.begin() + offset + 1);
		}
		appendCRC(frame.data() + offset, 30);
	}
	appendCRC(frame.data() + 12, 96);
	decoder.feedETI(frame.data(), frame.size());
	assert(decoder.crcErrors() == 0);
}

static void regression()
{
	eDABDecoder decoder(0x1201, 0, {}, {}, {});
	assert(decoder.language() == -1 && decoder.protection().empty());
	// FIG 0/5 arrives before service/subchannel organization; packet SCId 0 is English.
	fig(decoder, {5, 1, 0x70, 0x80, 0, 9});
	fig(decoder, {2, 0x12, 1, 1, 0x3f, 6});
	fig(decoder, {1, 4, 0, 0x84, 72});
	assert(decoder.language() == 112);
	assert(decoder.protection() == "EEP 2-A" && decoder.bitrate() == 72);
	// FIG 0/1 repeats must not erase the previously received language.
	fig(decoder, {1, 4, 0, 0x84, 72});
	assert(decoder.language() == 112);
	// Later FIC data must replace the stored protection and bitrate.
	fig(decoder, {1, 4, 0, 0x88, 42});
	assert(decoder.protection() == "EEP 3-A" && decoder.bitrate() == 56);
	fig(decoder, {1, 4, 0, 0x94, 42});
	assert(decoder.protection() == "EEP 2-B" && decoder.bitrate() == 64);
	fig(decoder, {1, 4, 0, 59});
	assert(decoder.protection() == "UEP 4" && decoder.bitrate() == 320);
	// Packet/FIDC metadata must not overwrite the audio language.
	fig(decoder, {5, 0x41, 9, 0x80, 0, 9});
	assert(decoder.language() == 112);
	// Future/other-ensemble configurations are not current-service metadata.
	fig(decoder, {0x85, 1, 9});
	fig(decoder, {0x45, 1, 9});
	assert(decoder.language() == 112);
	// Truncated FIG 0/5 records have no effect.
	fig(decoder, {5, 1});
	fig(decoder, {5, 0x80, 0});
	assert(decoder.language() == 112);
	// Optional FIG 0/17 language is a fallback, not a replacement for FIG 0/5.
	fig(decoder, {17, 0x12, 1, 0x20, 9, 1});
	assert(decoder.language() == 112);
	eDABDecoder fallback(0x1201, 0, {}, {}, {});
	fig(fallback, {17, 0x12, 1, 0x20, 9, 1});
	assert(fallback.language() == 9);
	fig(fallback, {17, 0x12, 1, 0x30, 0x70, 1}); // missing CC byte
	assert(fallback.language() == 9);
	fig(fallback, {17, 0x12, 1, 0x30, 0x70, 1, 0});
	assert(fallback.language() == 112);
	fig(fallback, {2, 0x12, 1, 1, 0x3f, 6});
	fig(fallback, {5, 1, 0}); // unspecified subchannel language uses the service fallback
	assert(fallback.language() == 112);
	fig(fallback, {5, 1, 9}); // later FIG 0/5 update takes precedence
	assert(fallback.language() == 9);
	std::cout << "Metadata regression tests passed\n";
}

static void capture(const char *path)
{
	const unsigned ids[] = {0x1201,0x1202,0x1203,0x1204,0x1205,0x1206,0x1207,
		0x1208,0x1209,0x120a,0x120b,0x120c,0x120d,0x1332};
	std::vector<std::unique_ptr<eDABDecoder>> decoders;
	for (unsigned id : ids)
		decoders.emplace_back(new eDABDecoder(id, 0xe000, {}, {}, {}));
	std::ifstream input(path, std::ios::binary);
	assert(input.good());
	std::array<uint8_t, 6144> frame;
	while (input.read(reinterpret_cast<char *>(frame.data()), frame.size()))
		for (auto &decoder : decoders)
			decoder->feedETI(frame.data(), frame.size());
	for (size_t i = 0; i < decoders.size(); ++i)
	{
		const auto &decoder = decoders[i];
		assert(decoder->serviceFound());
		assert(decoder->language() == 112);
		assert(decoder->protection() == ((ids[i] == 0x1206 || ids[i] == 0x1332) ? "EEP 3-A" : "EEP 2-A"));
		std::cout << std::hex << ids[i] << std::dec << " " << decoder->language()
			<< " " << decoder->protection() << " " << decoder->bitrate() << " kbit/s"
			<< " ETI=" << decoder->etiFrames() << " CRC-errors=" << decoder->crcErrors() << "\n";
	}
}

int main(int argc, char **argv)
{
	regression();
	if (argc > 1)
		capture(argv[1]);
}
