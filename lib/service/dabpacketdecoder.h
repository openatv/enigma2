#ifndef __lib_service_dabpacketdecoder_h
#define __lib_service_dabpacketdecoder_h

#include <cstddef>
#include <cstdint>
#include <functional>
#include <map>
#include <string>
#include <vector>

/* Reassembles EN 300 401 packet-mode MSC data groups and the MOT carousel
 * used by DAB SPI (TS 102 371).  Instances live entirely in eDABWorker's
 * thread; only completed, size-limited objects are forwarded. */
class eDABPacketDecoder
{
public:
	typedef std::function<void(const uint8_t *, size_t, int, int,
		const std::string &, uint16_t)> ObjectCallback;

	eDABPacketDecoder(int packetAddress, const ObjectCallback &callback);
	void feed(const uint8_t *data, size_t length);

private:
	struct Segments
	{
		std::map<int, std::vector<uint8_t> > data;
		int last = -1;
		size_t size = 0;

		void clear();
		bool add(int number, bool lastSegment, const uint8_t *payload, size_t length);
		bool complete() const;
		std::vector<uint8_t> join(size_t limit = 0) const;
	};

	struct Object
	{
		Segments header;
		Segments body;
		size_t bodySize = 0;
		size_t headerSize = 0;
		int contentType = -1;
		int contentSubType = -1;
		std::string contentName;
		uint64_t emittedHash = 0;
		bool headerReady = false;
	};

	struct Directory
	{
		uint16_t transportId = 0;
		uint32_t announcedSize = 0;
		uint16_t objectCount = 0;
		Segments segments;
		bool parsed = false;
	};

	void processPacket(const uint8_t *data, size_t length);
	void processDataGroup(const std::vector<uint8_t> &group);
	void processMOTSegment(int groupType, uint16_t transportId, int segmentNumber,
		bool lastSegment, const uint8_t *data, size_t length);
	void processDirectory(uint16_t transportId, int segmentNumber, bool lastSegment,
		const uint8_t *data, size_t length);
	void parseDirectory();
	bool parseObjectHeader(Object &object, const uint8_t *data, size_t available,
		size_t &consumed);
	void emitObject(uint16_t transportId, Object &object);

	static uint16_t read16(const uint8_t *data);
	static uint16_t crc16(uint16_t crc, const uint8_t *data, size_t length);
	static bool checkCRC(const uint8_t *data, size_t length);
	static uint64_t objectHash(const uint8_t *data, size_t length, int type, int subtype);

	int m_packet_address;
	ObjectCallback m_callback;
	std::vector<uint8_t> m_group;
	bool m_group_active = false;
	int m_expected_continuity = -1;
	std::map<uint16_t, Object> m_objects;
	Directory m_directory;
	uint64_t m_packets = 0;
	uint64_t m_crc_failures = 0;
	uint64_t m_matching_packets = 0;
	uint64_t m_data_groups = 0;
	bool m_probe_logged = false;
};

#endif
