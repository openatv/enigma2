#include <lib/dvb/idvb.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/atsc.h>

#include <iconv.h>
#include <byteswap.h>
#include <dvbsi++/byte_stream.h>
#include <dvbsi++/descriptor_tag.h>

static std::string UTF16ToUTF8(uint16_t c)
{
	if (c < 0x80)
	{
		char utf[2] = {(char)c, 0};
		return std::string((char*)utf, 1);
	}
	else if (c < 0x800)
	{
		char utf[3] = { (char)(0xc0 | (c >> 6)), (char)(0x80 | (c & 0x3f)), 0};
		return std::string((char*)utf, 2);
	}
	else
	{
		char utf[4] = { (char)(0xe0 | (c >> 12)), (char)(0x80 | ((c >> 6) & 0x3f)), (char)(0x80 | (c & 0x3f)), 0};
		return std::string((char*)utf, 3);
	}
	return "";
}

StringSegment::StringSegment(const uint8_t *const buffer)
{
	compression = buffer[0];
	mode = buffer[1];
	dataBytes.resize(buffer[2]);
	memcpy(&dataBytes[0], &buffer[3], buffer[2]);
}

StringSegment::~StringSegment()
{
}

const uint8_t StringSegment::getMode(void) const
{
	return mode;
}

const uint8_t StringSegment::getCompression(void) const
{
	return compression;
}

const std::vector<uint8_t> &StringSegment::getData(void) const
{
	return dataBytes;
}

const std::string StringSegment::getValue(void) const
{
	std::string value;
	size_t k;

	switch (compression)
	{
	case 0: /* no compression */
		break;
	case 1: /* huffman table C.4 and C.5 */
		/* TODO: Huffman decode */
		break;
	case 2: /* huffman table C.6 and C.7 */
		/* TODO: Huffman decode */
		break;
	}
	switch (mode)
	{
	case 0x00:
	case 0x01:
	case 0x02:
	case 0x03:
	case 0x04:
	case 0x05:
	case 0x06:
	case 0x09:
	case 0x0a:
	case 0x0b:
	case 0x0c:
	case 0x0d:
	case 0x0e:
	case 0x0f:
	case 0x10:
	case 0x20:
	case 0x21:
	case 0x22:
	case 0x23:
	case 0x24:
	case 0x25:
	case 0x26:
	case 0x27:
	case 0x30:
	case 0x31:
	case 0x32:
	case 0x33:
		for (k = 0; k < dataBytes.size(); k++)
		{
			value += UTF16ToUTF8(mode << 8 | dataBytes[k]);
		}
		break;
	case 0x3e:
		/* TODO: SCSU */
		break;
	case 0x3f:
		/* UTF-16 */
		for (k = 0; k < dataBytes.size(); k += 2)
		{
			value += UTF16ToUTF8(dataBytes[k] << 8 | dataBytes[k + 1]);
		}
		break;
	}
	return value;
}

StringValue::StringValue(const uint8_t *const buffer)
{
	const uint8_t *pos = &buffer[4];
	uint8_t numsegments = buffer[3];
	iso639LanguageCode.assign((char*)buffer, 3);
	size = 4;
	for (uint8_t i = 0; i < numsegments; i++)
	{
		segments.push_back(new StringSegment(pos));
		pos++;
		pos++;
		uint8_t number_bytes = *pos++;
		size += 3 + number_bytes;
	}
}

StringValue::~StringValue()
{
	for (std::vector<StringSegment *>::const_iterator i = segments.begin(); i != segments.end(); ++i)
		delete *i;
}

const std::string &StringValue::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

const std::vector<StringSegment *> &StringValue::getSegments(void) const
{
	return segments;
}

const std::string StringValue::getValue(void) const
{
	std::string value;
	for (std::vector<StringSegment *>::const_iterator i = segments.begin(); i != segments.end(); ++i)
	{
		value += (*i)->getValue();
	}
	return value;
}

const uint32_t StringValue::getSize(void) const
{
	return size;
}

MultipleStringStructure::MultipleStringStructure(const uint8_t *const buffer)
{
	uint8_t i;
	uint8_t number_strings = buffer[0];
	const uint8_t *pos = &buffer[1];
	for (i = 0; i < number_strings; i++)
	{
		StringValue *str = new StringValue(pos);
		strings.push_back(str);
		pos += str->getSize();
	}
}

MultipleStringStructure::~MultipleStringStructure()
{
	for (StringValueListIterator i = strings.begin(); i != strings.end(); ++i)
		delete *i;
}

const StringValueList *MultipleStringStructure::getStrings(void) const
{
	return &strings;
}

VirtualChannel::VirtualChannel(const uint8_t * const buffer, bool terrestrial)
{
	int i;
	for (i = 0; i < 7; i++)
	{
		name += UTF16ToUTF8(buffer[2 * i] << 8 | buffer[2 * i + 1]);
	}
	transportStreamId = UINT16(&buffer[22]);
	serviceId = UINT16(&buffer[24]);
	accessControlled = (buffer[26] >> 5) & 0x1;
	serviceType = buffer[27] & 0x3f;
	sourceId = UINT16(&buffer[28]);
	descriptorsLoopLength = DVB_LENGTH(&buffer[30]) & 0x3ff;

	for (i = 32; i < descriptorsLoopLength + 32; i += buffer[i + 1] + 2)
	{
		switch (buffer[i])
		{
		case 0xa0:
			descriptorList.push_back(new ExtendedChannelNameDescriptor(&buffer[i]));
			break;
		default:
			descriptor(&buffer[i], SCOPE_SI);
			break;
		}
	}
}

VirtualChannel::~VirtualChannel(void)
{
}

const std::string &VirtualChannel::getName(void) const
{
	return name;
}

uint16_t VirtualChannel::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t VirtualChannel::getServiceId(void) const
{
	return serviceId;
}

uint16_t VirtualChannel::getSourceId(void) const
{
	return sourceId;
}

uint8_t VirtualChannel::getServiceType(void) const
{
	return serviceType;
}

uint16_t VirtualChannel::getDescriptorsLoopLength(void) const
{
	return descriptorsLoopLength;
}

bool VirtualChannel::isAccessControlled(void) const
{
	return accessControlled;
}

VirtualChannelTableSection::VirtualChannelTableSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	uint16_t pos = 10;
	uint8_t i;
	uint8_t numchannels = buffer[9];
	uint8_t tableid = buffer[0];

	transportStreamId = UINT16(&buffer[3]);
	versionNumber = (buffer[5] >> 1) & 0x1f;

	for (i = 0; i < numchannels; i++)
	{
		VirtualChannel *channel = new VirtualChannel(&buffer[pos], (tableid == 0xc8));
		channels.push_back(channel);
		pos += 32 + channel->getDescriptorsLoopLength();
	}
}

VirtualChannelTableSection::~VirtualChannelTableSection(void)
{
	for (VirtualChannelListIterator i = channels.begin(); i != channels.end(); ++i)
		delete *i;
}

uint8_t VirtualChannelTableSection::getVersion(void) const
{
	return versionNumber;
}

uint16_t VirtualChannelTableSection::getTransportStreamId(void) const
{
	return transportStreamId;
}

const VirtualChannelList *VirtualChannelTableSection::getChannels(void) const
{
	return &channels;
}

ExtendedChannelNameDescriptor::ExtendedChannelNameDescriptor(const uint8_t * const buffer)
 : Descriptor(buffer)
{
	value = new MultipleStringStructure(buffer + 2);
}

ExtendedChannelNameDescriptor::~ExtendedChannelNameDescriptor()
{
	delete value;
}

const std::string ExtendedChannelNameDescriptor::getName(void) const
{
	if (value)
	{
		const StringValueList *valuelist = value->getStrings();
		if (valuelist && valuelist->begin() != valuelist->end()) return (*valuelist->begin())->getValue();
	}
	return "";
}

SystemTimeTableSection::SystemTimeTableSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	versionNumber = (buffer[5] >> 1) & 0x1f;
	systemTime = UINT32(&buffer[9]);
	gpsOffset = buffer[13];
}

SystemTimeTableSection::~SystemTimeTableSection(void)
{
}

uint8_t SystemTimeTableSection::getVersion(void) const
{
	return versionNumber;
}

uint32_t SystemTimeTableSection::getSystemTime(void) const
{
	return systemTime;
}

uint8_t SystemTimeTableSection::getGPSOffset(void) const
{
	return gpsOffset;
}

MasterGuideTable::MasterGuideTable(const uint8_t * const buffer)
{
	tableType = UINT16(&buffer[0]);
	PID = UINT16(&buffer[2]) & 0x1fff;
	numberBytes = UINT32(&buffer[5]);
	descriptorsLoopLength = UINT16(&buffer[9]) & 0xfff;

	for (uint16_t i = 11; i < descriptorsLoopLength + 11; i += buffer[i + 1] + 2)
	{
		descriptor(&buffer[i], SCOPE_SI);
	}
}

MasterGuideTable::~MasterGuideTable(void)
{
}

uint16_t MasterGuideTable::getPID(void) const
{
	return PID;
}

uint16_t MasterGuideTable::getTableType(void) const
{
	return tableType;
}

uint32_t MasterGuideTable::getNumberBytes(void) const
{
	return numberBytes;
}

uint16_t MasterGuideTable::getDescriptorsLoopLength(void) const
{
	return descriptorsLoopLength;
}

MasterGuideTableSection::MasterGuideTableSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	uint16_t pos = 11;
	uint16_t i;
	uint16_t numtables = UINT16(&buffer[9]);

	versionNumber = (buffer[5] >> 1) & 0x1f;

	for (i = 0; i < numtables; i++)
	{
		MasterGuideTable *table = new MasterGuideTable(&buffer[pos]);
		tables.push_back(table);
		pos += 11 + table->getDescriptorsLoopLength();
	}
}

MasterGuideTableSection::~MasterGuideTableSection(void)
{
	for (MasterGuideTableListIterator i = tables.begin(); i != tables.end(); ++i)
		delete *i;
}

uint8_t MasterGuideTableSection::getVersion(void) const
{
	return versionNumber;
}

const MasterGuideTableList *MasterGuideTableSection::getTables(void) const
{
	return &tables;
}

ATSCEvent::ATSCEvent(const uint8_t * const buffer)
{
	uint16_t i;
	eventId = UINT16(&buffer[0]) & 0x3fff;
	startTime = UINT32(&buffer[2]);
	ETMLocation = (buffer[6] >> 4) & 0x3;
	lengthInSeconds = UINT32(&buffer[5]) & 0xfffff;

	titleLength = buffer[9];
	title = new MultipleStringStructure(&buffer[10]);

	descriptorsLoopLength = DVB_LENGTH(&buffer[10 + titleLength]) & 0xfff;

	for (i = 12 + titleLength; i < 12 + titleLength + descriptorsLoopLength; i += buffer[i + 1] + 2)
		descriptor(&buffer[i], SCOPE_SI);
}

ATSCEvent::~ATSCEvent(void)
{
	delete title;
}

const std::string ATSCEvent::getTitle(const std::string &language) const
{
	if (title)
	{
		const StringValueList *valuelist = title->getStrings();
		if (valuelist)
		{
			if (language.empty() || language == "---")
			{
				if (valuelist->begin() != valuelist->end()) return (*valuelist->begin())->getValue();
			}
			else
			{
				for (StringValueListConstIterator i = valuelist->begin(); i != valuelist->end(); i++)
				{
					if ((*i)->getIso639LanguageCode() == language)
					{
						return (*i)->getValue();
					}
				}
			}
		}
	}
	return "";
}

uint16_t ATSCEvent::getEventId(void) const
{
	return eventId;
}

uint8_t ATSCEvent::getETMLocation(void) const
{
	return ETMLocation;
}

uint32_t ATSCEvent::getStartTime(void) const
{
	return startTime;
}

uint32_t ATSCEvent::getLengthInSeconds(void) const
{
	return lengthInSeconds;
}

uint16_t ATSCEvent::getTitleLength(void) const
{
	return titleLength;
}

uint16_t ATSCEvent::getDescriptorsLoopLength(void) const
{
	return descriptorsLoopLength;
}

ATSCEventInformationSection::ATSCEventInformationSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	uint16_t pos = 10;
	uint8_t i;
	uint8_t numevents = buffer[9];

	versionNumber = (buffer[5] >> 1) & 0x1f;

	for (i = 0; i < numevents; i++)
	{
		ATSCEvent *event = new ATSCEvent(&buffer[pos]);
		events.push_back(event);
		pos += 12 + event->getTitleLength() + event->getDescriptorsLoopLength();
	}
}

ATSCEventInformationSection::~ATSCEventInformationSection(void)
{
	for (ATSCEventListIterator i = events.begin(); i != events.end(); ++i)
		delete *i;
}

uint8_t ATSCEventInformationSection::getVersion(void) const
{
	return versionNumber;
}

const ATSCEventList *ATSCEventInformationSection::getEvents(void) const
{
	return &events;
}

ExtendedTextTableSection::ExtendedTextTableSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	versionNumber = (buffer[5] >> 1) & 0x1f;
	ETMId = UINT32(&buffer[9]);

	message = new MultipleStringStructure(&buffer[13]);
}

ExtendedTextTableSection::~ExtendedTextTableSection()
{
	delete message;
}

uint8_t ExtendedTextTableSection::getVersion(void) const
{
	return versionNumber;
}

uint32_t ExtendedTextTableSection::getETMId(void) const
{
	return ETMId;
}

const std::string ExtendedTextTableSection::getMessage(const std::string &language) const
{
	if (message)
	{
		const StringValueList *valuelist = message->getStrings();
		if (valuelist)
		{
			if (language.empty() || language == "---")
			{
				if (valuelist->begin() != valuelist->end()) return (*valuelist->begin())->getValue();
			}
			else
			{
				for (StringValueListConstIterator i = valuelist->begin(); i != valuelist->end(); i++)
				{
					if ((*i)->getIso639LanguageCode() == language) return (*i)->getValue();
				}
			}
		}
	}
	return "";
}
