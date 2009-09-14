#include <byteswap.h>
#include <dvbsi++/byte_stream.h>

#include <lib/dvb/logicalchanneldescriptor.h>

LogicalChannel::LogicalChannel(const uint8_t *const buffer)
{
	serviceId = UINT16(&buffer[0]);
	logicalChannelNumber = UINT16(&buffer[2]) & 0x3fff;
}

LogicalChannel::~LogicalChannel(void)
{
}

uint16_t LogicalChannel::getServiceId(void) const
{
	return serviceId;
}

uint16_t LogicalChannel::getLogicalChannelNumber(void) const
{
	return logicalChannelNumber;
}

LogicalChannelDescriptor::LogicalChannelDescriptor(const uint8_t *const buffer)
: Descriptor(buffer)
{
	uint16_t pos = 2;
	uint16_t bytesLeft = descriptorLength;
	uint16_t loopLength = 4;

	while (bytesLeft >= loopLength)
	{
		channelList.push_back(new LogicalChannel(&buffer[pos]));
		bytesLeft -= loopLength;
		pos += loopLength;
	}
}

LogicalChannelDescriptor::~LogicalChannelDescriptor(void)
{
	for (LogicalChannelListIterator i = channelList.begin(); i != channelList.end(); ++i)
		delete *i;
}

const LogicalChannelList *LogicalChannelDescriptor::getChannelList(void) const
{
	return &channelList;
}
