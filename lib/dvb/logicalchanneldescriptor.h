#ifndef _logicalchanneldescriptor_h
#define _logicalchanneldescriptor_h

#include <dvbsi++/descriptor.h>

class LogicalChannel
{
protected:
	unsigned serviceId : 16;
	unsigned logicalChannelNumber : 14;

public:
	LogicalChannel(const uint8_t *const buffer);
	~LogicalChannel(void);

	uint16_t getServiceId(void) const;
	uint16_t getLogicalChannelNumber(void) const;
};

typedef std::list<LogicalChannel *> LogicalChannelList;
typedef LogicalChannelList::iterator LogicalChannelListIterator;
typedef LogicalChannelList::const_iterator LogicalChannelListConstIterator;

class LogicalChannelDescriptor : public Descriptor
{
protected:
	LogicalChannelList channelList;

public:
	LogicalChannelDescriptor(const uint8_t *const buffer);
	~LogicalChannelDescriptor(void);

	const LogicalChannelList *getChannelList(void) const;
};

#endif
