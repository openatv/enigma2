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
	descriptorsLoopLength = DVB_LENGTH(&buffer[30]) & 0x3f;

	for (i = 32; i < descriptorsLoopLength + 32; i += buffer[i + 1] + 2)
		descriptor(&buffer[i], SCOPE_SI);
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
{
	/* TODO: parse multiple string object */
}

const std::string &ExtendedChannelNameDescriptor::getName(void) const
{
	return name;
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
