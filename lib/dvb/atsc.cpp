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

StringValue::StringValue(const uint8_t *const buffer)
{
	const uint8_t *pos = &buffer[4];
	uint8_t segments = buffer[3];
	iso639LanguageCode.assign((char*)buffer, 3);
	size = 4;
	for (uint8_t i = 0; i < segments; i++)
	{
		uint8_t compression_type = *pos++;
		uint8_t mode = *pos++;
		uint8_t number_bytes = *pos++;
		size += 3 + number_bytes;
		std::string data;
		size_t k;
		switch (compression_type)
		{
		case 0: /* no compression */
			data.assign((char*)pos, number_bytes);
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
			for (k = 0; k < data.length(); k++)
			{
				value += UTF16ToUTF8(mode << 8 | data[k]);
			}
			break;
		case 0x3e:
			/* TODO: SCSU */
			break;
		case 0x3f:
			/* UTF-16 */
			for (k = 0; k < data.length(); k += 2)
			{
				value += UTF16ToUTF8(data[k] << 8 | data[k + 1]);
			}
			break;
		}
	}
}

const std::string &StringValue::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

const std::string &StringValue::getValue(void) const
{
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

const std::string &ExtendedChannelNameDescriptor::getName(void) const
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
