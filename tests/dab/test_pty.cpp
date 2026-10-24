#include <cassert>
#include <fstream>
#include <iostream>
#include <iterator>
#include <lib/service/dabpaddecoder.h>
#include <memory>
#include <functional>

// Exercise production FIG parsing without adding a testing API to the decoder.
#define private public
#include <lib/service/dabdecoder.h>
#undef private

static void fig(eDABDecoder &decoder, std::initializer_list<uint8_t> bytes)
{
	const std::vector<uint8_t> data(bytes);
	decoder.parseFIG0(data.data(), data.size());
}

int main(int argc, char **argv)
{
	eDABDecoder decoder(0x1201, 0, {}, {}, {});
	assert(decoder.programmeType() == -1);
	assert(decoder.programmeTypeTable() == -1);
	fig(decoder, {17, 0x12, 0x01, 0, 1}); // Static PTY before FIG 0/2.
	assert(decoder.programmeType() == 1);
	fig(decoder, {9, 0, 0xe1, 1});
	assert(decoder.programmeTypeTable() == 1);
	fig(decoder, {17, 0x12, 0x01, 0x80, 24}); // Late dynamic change.
	assert(decoder.programmeType() == 24);
	fig(decoder, {17, 0x12, 0x01, 0x30, 112, 14, 0x1f}); // Legacy L + CC.
	assert(decoder.programmeType() == 14);
	assert(decoder.language() == 112);
	fig(decoder, {17, 0x12, 0x01, 0x30, 112, 4}); // Truncated CC: no change.
	assert(decoder.programmeType() == 14);
	fig(decoder, {17, 0x12, 0x02, 0, 11}); // A different service.
	assert(decoder.programmeType() == 14);
	fig(decoder, {0x51, 0x12, 0x01, 0, 11}); // Other ensemble.
	fig(decoder, {0x91, 0x12, 0x01, 0, 11}); // Next configuration.
	assert(decoder.programmeType() == 14);
	fig(decoder, {17, 0x12, 0x01, 0, 0}); // Transmitted "no programme type".
	assert(decoder.programmeType() == 0);
	fig(decoder, {9, 0, 0xe1, 2});
	assert(decoder.programmeTypeTable() == 2);
	eDABDecoder fresh(0x1201, 0, {}, {}, {});
	assert(fresh.programmeType() == -1 && fresh.programmeTypeTable() == -1);
	std::cout << "FIG PTY cases passed\n";
	if (argc == 2)
	{
		std::ifstream input(argv[1], std::ios::binary);
		assert(input);
		const std::vector<uint8_t> capture((std::istreambuf_iterator<char>(input)), {});
		assert(capture.size() % 6144 == 0);
		const std::vector<std::pair<uint16_t, int> > expected = {
			{0x1201,1}, {0x1202,15}, {0x1203,14}, {0x1204,4}, {0x1205,15},
			{0x1206,9}, {0x1207,11}, {0x1208,24}, {0x1209,28}, {0x120a,13},
			{0x120b,28}, {0x120c,12}, {0x120d,27}, {0x1332,9}
		};
		for (const auto &entry : expected)
		{
			eDABDecoder replay(entry.first, 0xe000,
				[](const uint8_t *, size_t, const uint8_t *, size_t, uint64_t, uint8_t, bool) {}, {}, {});
			for (size_t offset = 0; offset < capture.size(); offset += 6144)
				replay.feedETI(capture.data() + offset, 6144);
			assert(replay.programmeType() == entry.second);
			assert(replay.programmeTypeTable() == 1);
			assert(replay.language() == 112);
			assert(replay.protection() == ((entry.first == 0x1206 || entry.first == 0x1332) ? "EEP 3-A" : "EEP 2-A"));
			assert(replay.crcErrors() == 0);
			std::cout << std::hex << entry.first << std::dec << " PTY=" << replay.programmeType()
				<< " table=" << replay.programmeTypeTable() << " frames=" << replay.etiFrames() << '\n';
		}
	}
}
