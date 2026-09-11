#include <algorithm>
#include <cstdio>

#include <lib/service/dabdebug.h>
#include <lib/service/dabpacketdecoder.h>
#include <lib/service/dabpadtools.h>

namespace
{
const size_t MAX_DATA_GROUP_SIZE = 1024 * 1024;
const size_t MAX_MOT_OBJECT_SIZE = 4 * 1024 * 1024;
const size_t MAX_MOT_DIRECTORY_SIZE = 4 * 1024 * 1024;
const size_t MAX_MOT_OBJECTS = 4096;
}

eDABPacketDecoder::eDABPacketDecoder(int packetAddress, const ObjectCallback &callback)
	: m_packet_address(packetAddress), m_callback(callback)
{
}

void eDABPacketDecoder::Segments::clear()
{
	data.clear();
	last = -1;
	size = 0;
}

bool eDABPacketDecoder::Segments::add(int number, bool lastSegment,
	const uint8_t *payload, size_t length)
{
	if (number < 0 || number >= 8192 || !payload || length > MAX_MOT_OBJECT_SIZE ||
		size > MAX_MOT_OBJECT_SIZE - length)
		return false;
	if (lastSegment)
	{
		if (last >= 0 && last != number)
			clear();
		last = number;
	}
	std::map<int, std::vector<uint8_t> >::iterator existing = data.find(number);
	if (existing != data.end())
	{
		if (existing->second.size() == length &&
			std::equal(existing->second.begin(), existing->second.end(), payload))
			return true;
		size -= existing->second.size();
		existing->second.assign(payload, payload + length);
		size += length;
		return true;
	}
	data[number].assign(payload, payload + length);
	size += length;
	return true;
}

bool eDABPacketDecoder::Segments::complete() const
{
	if (last < 0)
		return false;
	for (int number = 0; number <= last; ++number)
		if (data.find(number) == data.end())
			return false;
	return true;
}

std::vector<uint8_t> eDABPacketDecoder::Segments::join(size_t limit) const
{
	std::vector<uint8_t> result;
	if (!complete() || (limit && size > limit))
		return result;
	result.reserve(size);
	for (int number = 0; number <= last; ++number)
	{
		std::map<int, std::vector<uint8_t> >::const_iterator segment = data.find(number);
		if (segment == data.end())
			return std::vector<uint8_t>();
		result.insert(result.end(), segment->second.begin(), segment->second.end());
	}
	return result;
}

uint16_t eDABPacketDecoder::read16(const uint8_t *data)
{
	return static_cast<uint16_t>((data[0] << 8) | data[1]);
}

uint16_t eDABPacketDecoder::crc16(uint16_t crc, const uint8_t *data, size_t length)
{
	while (length--)
	{
		crc ^= static_cast<uint16_t>(*data++) << 8;
		for (int bit = 0; bit < 8; ++bit)
			crc = static_cast<uint16_t>((crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1);
	}
	return crc;
}

bool eDABPacketDecoder::checkCRC(const uint8_t *data, size_t length)
{
	return length >= 2 && read16(data + length - 2) ==
		static_cast<uint16_t>(crc16(0xffff, data, length - 2) ^ 0xffff);
}

uint64_t eDABPacketDecoder::objectHash(const uint8_t *data, size_t length, int type, int subtype)
{
	uint64_t hash = 1469598103934665603ULL;
	hash ^= static_cast<uint64_t>(type & 0xff);
	hash *= 1099511628211ULL;
	hash ^= static_cast<uint64_t>(subtype & 0x1ff);
	hash *= 1099511628211ULL;
	for (size_t i = 0; i < length; ++i)
	{
		hash ^= data[i];
		hash *= 1099511628211ULL;
	}
	return hash;
}

void eDABPacketDecoder::feed(const uint8_t *data, size_t length)
{
	if (!m_probe_logged && data && length)
	{
		char bytes[3 * 16 + 1] = {};
		const size_t shown = std::min<size_t>(length, 16);
		for (size_t i = 0; i < shown; ++i)
			snprintf(bytes + i * 3, sizeof(bytes) - i * 3, "%02x%s", data[i], i + 1 == shown ? "" : " ");
		eDABDebug("[eDABPacketDecoder] packet stream address=%d frame=%u first=%s",
			m_packet_address, static_cast<unsigned int>(length), bytes);
		m_probe_logged = true;
	}
	while (data && length >= 24)
	{
		const size_t packetLength = (static_cast<size_t>(data[0] >> 6) + 1) * 24;
		if (packetLength > length)
			break;
		processPacket(data, packetLength);
		data += packetLength;
		length -= packetLength;
	}
}

void eDABPacketDecoder::processPacket(const uint8_t *data, size_t length)
{
	++m_packets;
	if (length < 5 || !checkCRC(data, length))
	{
		if (++m_crc_failures <= 3)
			eDABDebug("[eDABPacketDecoder] packet CRC rejected length=%u header=%02x%02x%02x",
				static_cast<unsigned int>(length), data[0], data[1], data[2]);
		return;
	}
	const int continuity = (data[0] >> 4) & 3;
	const int firstLast = (data[0] >> 2) & 3;
	const int address = ((data[0] & 3) << 8) | data[1];
	const bool command = data[2] & 0x80;
	const size_t usefulLength = data[2] & 0x7f;
	if (!address || address != m_packet_address || command || usefulLength > length - 5)
		return;
	++m_matching_packets;
	if (m_matching_packets <= 40)
		eDABDebug("[eDABPacketDecoder] packet accepted address=%d ci=%d fl=%d useful=%u length=%u",
			address, continuity, firstLast, static_cast<unsigned int>(usefulLength),
			static_cast<unsigned int>(length));
	const uint8_t *payload = data + 3;

	if (firstLast == 3) // a complete data group in one packet
	{
		m_group_active = false;
		m_group.assign(payload, payload + usefulLength);
		processDataGroup(m_group);
		m_group.clear();
		m_expected_continuity = (continuity + 1) & 3;
		return;
	}
	if (firstLast == 2) // first packet
	{
		m_group.assign(payload, payload + usefulLength);
		m_group_active = m_group.size() <= MAX_DATA_GROUP_SIZE;
		m_expected_continuity = (continuity + 1) & 3;
		return;
	}
	if (!m_group_active || continuity != m_expected_continuity)
	{
		m_group_active = false;
		m_group.clear();
		m_expected_continuity = -1;
		return;
	}
	m_expected_continuity = (continuity + 1) & 3;
	if (m_group.size() > MAX_DATA_GROUP_SIZE - usefulLength)
	{
		m_group_active = false;
		m_group.clear();
		return;
	}
	m_group.insert(m_group.end(), payload, payload + usefulLength);
	if (firstLast == 1) // last packet
	{
		processDataGroup(m_group);
		m_group_active = false;
		m_group.clear();
	}
}

void eDABPacketDecoder::processDataGroup(const std::vector<uint8_t> &group)
{
	++m_data_groups;
	const int announcedType = group.empty() ? -1 : group[0] & 0x0f;
	if (m_data_groups <= 10 || announcedType != 4)
		eDABDebug("[eDABPacketDecoder] data group received size=%u header=%02x%02x crc=%d",
			static_cast<unsigned int>(group.size()), group.empty() ? 0 : group[0],
			group.size() < 2 ? 0 : group[1], group.size() >= 2 && checkCRC(group.data(), group.size()));
	if (group.size() < 9)
		return;
	const bool extension = group[0] & 0x80;
	const bool hasCRC = group[0] & 0x40;
	const bool segmented = group[0] & 0x20;
	const bool userAccess = group[0] & 0x10;
	const int groupType = group[0] & 0x0f;
	if (!hasCRC || !segmented || !userAccess ||
		(groupType != 3 && groupType != 4 && groupType != 6) || !checkCRC(group.data(), group.size()))
		return;
	const size_t payloadEnd = group.size() - 2;
	size_t offset = 2;
	if (extension)
		offset += 2;
	if (offset + 2 > payloadEnd)
		return;
	const bool lastSegment = group[offset] & 0x80;
	const int segmentNumber = ((group[offset] & 0x7f) << 8) | group[offset + 1];
	offset += 2;
	if (offset >= payloadEnd)
		return;
	const bool transportIdFlag = group[offset] & 0x10;
	const size_t accessLength = group[offset] & 0x0f;
	++offset;
	if (!transportIdFlag || accessLength < 2 || offset + accessLength > payloadEnd)
		return;
	const uint16_t transportId = read16(group.data() + offset);
	offset += accessLength;
	if (offset + 2 > payloadEnd)
		return;
	const size_t segmentSize = ((group[offset] & 0x1f) << 8) | group[offset + 1];
	offset += 2;
	if (segmentSize != payloadEnd - offset)
		return;
	if (groupType != 4)
		eDABDebug("[eDABPacketDecoder] MOT control group type=%d tid=%04x segment=%d last=%d size=%u",
			groupType, transportId, segmentNumber, lastSegment, static_cast<unsigned int>(segmentSize));
	if (groupType == 6)
		processDirectory(transportId, segmentNumber, lastSegment, group.data() + offset, segmentSize);
	else
		processMOTSegment(groupType, transportId, segmentNumber, lastSegment,
			group.data() + offset, segmentSize);
}

bool eDABPacketDecoder::parseObjectHeader(Object &object, const uint8_t *data,
	size_t available, size_t &consumed)
{
	consumed = 0;
	if (!data || available < 7)
		return false;
	const size_t bodySize = (static_cast<size_t>(data[0]) << 20) |
		(static_cast<size_t>(data[1]) << 12) | (static_cast<size_t>(data[2]) << 4) |
		(data[3] >> 4);
	const size_t headerSize = ((static_cast<size_t>(data[3]) & 0x0f) << 9) |
		(static_cast<size_t>(data[4]) << 1) | (data[5] >> 7);
	if (headerSize < 7 || headerSize > available || bodySize > MAX_MOT_OBJECT_SIZE)
		return false;
	std::string contentName;
	for (size_t offset = 7; offset < headerSize;)
	{
		const int pli = data[offset] >> 6;
		const int parameter = data[offset] & 0x3f;
		++offset;
		size_t parameterLength = 0;
		if (pli == 1)
			parameterLength = 1;
		else if (pli == 2)
			parameterLength = 4;
		else if (pli == 3)
		{
			if (offset >= headerSize)
				return false;
			parameterLength = data[offset] & 0x7f;
			const bool extended = data[offset++] & 0x80;
			if (extended)
			{
				if (offset >= headerSize)
					return false;
				parameterLength = (parameterLength << 8) | data[offset++];
			}
		}
		if (parameterLength > headerSize - offset)
			return false;
		if (parameter == 0x0c && parameterLength)
			contentName = DABlinPAD::CharsetTools::ConvertTextToUTF8(data + offset + 1,
				parameterLength - 1, data[offset] >> 4, true, nullptr);
		offset += parameterLength;
	}
	object.bodySize = bodySize;
	object.headerSize = headerSize;
	object.contentType = (data[5] >> 1) & 0x3f;
	object.contentSubType = ((data[5] & 1) << 8) | data[6];
	object.contentName = contentName;
	object.headerReady = true;
	consumed = headerSize;
	return true;
}

void eDABPacketDecoder::processMOTSegment(int groupType, uint16_t transportId,
	int segmentNumber, bool lastSegment, const uint8_t *data, size_t length)
{
	Object &object = m_objects[transportId];
	if (groupType == 3)
	{
		if (!object.header.add(segmentNumber, lastSegment, data, length) || !object.header.complete())
			return;
		const std::vector<uint8_t> header = object.header.join(64 * 1024);
		size_t consumed = 0;
		if (!header.empty() && parseObjectHeader(object, header.data(), header.size(), consumed) &&
			consumed == header.size())
			emitObject(transportId, object);
		return;
	}
	if (!object.body.add(segmentNumber, lastSegment, data, length))
		return;
	emitObject(transportId, object);
}

void eDABPacketDecoder::processDirectory(uint16_t transportId, int segmentNumber,
	bool lastSegment, const uint8_t *data, size_t length)
{
	if (m_directory.transportId && m_directory.transportId != transportId)
		m_directory = Directory();
	if (!m_directory.transportId)
		m_directory.transportId = transportId;
	if (!segmentNumber)
	{
		if (length < 11)
			return;
		const uint32_t directorySize = ((static_cast<uint32_t>(data[0]) & 0x3f) << 24) |
			(static_cast<uint32_t>(data[1]) << 16) | (static_cast<uint32_t>(data[2]) << 8) | data[3];
		const uint16_t objectCount = read16(data + 4);
		if (directorySize < 13 || directorySize > MAX_MOT_DIRECTORY_SIZE || objectCount > MAX_MOT_OBJECTS)
			return;
		if (m_directory.announcedSize && m_directory.announcedSize != directorySize)
		{
			m_directory = Directory();
			m_directory.transportId = transportId;
		}
		m_directory.announcedSize = directorySize;
		m_directory.objectCount = objectCount;
	}
	if (m_directory.transportId != transportId ||
		!m_directory.segments.add(segmentNumber, lastSegment, data, length))
		return;
	if (m_directory.announcedSize && m_directory.segments.complete() && !m_directory.parsed)
		parseDirectory();
}

void eDABPacketDecoder::parseDirectory()
{
	std::vector<uint8_t> directory = m_directory.segments.join(MAX_MOT_DIRECTORY_SIZE);
	if (directory.size() < 13 || directory.size() < m_directory.announcedSize)
		return;
	directory.resize(m_directory.announcedSize);
	const size_t extensionLength = read16(directory.data() + 11);
	size_t offset = 13 + extensionLength;
	if (offset > directory.size())
		return;
	size_t parsedObjects = 0;
	while (parsedObjects < m_directory.objectCount && offset + 9 <= directory.size())
	{
		const uint16_t transportId = read16(directory.data() + offset);
		offset += 2;
		if (!transportId)
			break;
		Object &object = m_objects[transportId];
		size_t consumed = 0;
		if (!parseObjectHeader(object, directory.data() + offset, directory.size() - offset, consumed))
			return;
		offset += consumed;
		++parsedObjects;
		emitObject(transportId, object);
	}
	m_directory.parsed = parsedObjects > 0;
	eDABDebug("[eDABPacketDecoder] MOT directory tid=%04x objects=%u parsed=%u size=%u",
		m_directory.transportId, m_directory.objectCount, static_cast<unsigned int>(parsedObjects),
		m_directory.announcedSize);
}

void eDABPacketDecoder::emitObject(uint16_t transportId, Object &object)
{
	if (!object.headerReady || !object.body.complete() || object.body.size != object.bodySize)
		return;
	std::vector<uint8_t> body = object.body.join(MAX_MOT_OBJECT_SIZE);
	if (body.size() != object.bodySize)
		return;
	const uint64_t hash = objectHash(body.data(), body.size(), object.contentType, object.contentSubType);
	if (hash == object.emittedHash)
		return;
	object.emittedHash = hash;
	eDABDebug("[eDABPacketDecoder] MOT object tid=%04x type=%d/%d name='%s' size=%u",
		transportId, object.contentType, object.contentSubType, object.contentName.c_str(),
		static_cast<unsigned int>(body.size()));
	if (m_callback)
		m_callback(body.data(), body.size(), object.contentType, object.contentSubType,
			object.contentName, transportId);
}
