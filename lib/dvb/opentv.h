#ifndef __OPENTV_H__
#define __OPENTV_H__

#include <dvbsi++/long_crc_section.h>
#include <dvbsi++/descriptor_container.h>

#define OPENTV_DESCRIPTOR_LOOP			0xb0
#define OPENTV_LOGICAL_CHANNEL_DESCRIPTOR	0xb1
#define OPENTV_EVENT_TITLE_DESCRIPTOR		0xb5
#define OPENTV_EVENT_SUMMARY_DESCRIPTOR		0xb9
#define OPENTV_EVENT_DESCRIPTION_DESCRIPTOR	0xbb
#define OPENTV_EVENT_SERIES_LINK_DESCRIPTOR	0xc1
#define OPENTV_EVENT_TITLE_LENGTH		0xff
#define OPENTV_EVENT_SUMMARY_LENGTH		0x3ff

class OpenTvChannel
{
protected:
	unsigned transportStreamId	: 16;
	unsigned originalNetworkId	: 16;
	unsigned serviceId		: 16;
	unsigned channelId		: 16;
	unsigned serviceType		: 6;

public:
	OpenTvChannel(const uint8_t *const buffer);
	~OpenTvChannel(void);

	uint16_t getTransportStreamId(void) const;
	uint16_t getOriginalNetworkId(void) const;
	uint16_t getServiceId(void) const;
	uint16_t getChannelId(void) const;
	uint8_t getServiceType(void) const;

	void setTransportStreamId(uint16_t transportstreamid);
	void setOriginalNetworkId(uint16_t originalnetworkid);
};

typedef std::list<OpenTvChannel *> OpenTvChannelList;
typedef OpenTvChannelList::iterator OpenTvChannelListIterator;
typedef OpenTvChannelList::const_iterator OpenTvChannelListConstIterator;

class OpenTvChannelSection : public LongCrcSection , public DescriptorContainer
{
protected:
	unsigned descriptorsLength		: 12;
	unsigned descriptorLength		: 8;
	unsigned transportDescriptorsLength	: 12;
	unsigned transportStreamId		: 16;
	unsigned originalNetworkId		: 16;
	OpenTvChannelList channels;

public:
	OpenTvChannelSection(const uint8_t * const buffer);
	~OpenTvChannelSection(void);

	const OpenTvChannelList *getChannels(void) const;
	uint16_t getChannelsListSize(void) const;
};

class OpenTvTitle : public DescriptorContainer
{
protected:
	unsigned channelId	: 16;
	unsigned eventId	: 16;
	unsigned startTimeBcd	: 32;
	unsigned duration	: 24;
	unsigned crc32		: 32;
	std::string title;

public:
	OpenTvTitle(const uint8_t *const buffer, uint16_t mjdtime);
	~OpenTvTitle(void);

	std::string getTitle(void) const;
	uint32_t getCRC32(void) const;
	uint16_t getChannelId(void) const;
	uint32_t getStartTime(void) const;
	uint16_t getEventId(void) const;
	uint16_t getDuration(void) const;
	void setChannelId(uint16_t channelid);
	void setEventId(uint16_t eventId);
};

typedef std::list<OpenTvTitle *> OpenTvTitleList;
typedef OpenTvTitleList::iterator OpenTvTitleListIterator;
typedef OpenTvTitleList::const_iterator OpenTvTitleListConstIterator;

class OpenTvTitleSection : public LongCrcSection , public DescriptorContainer
{
protected:
	unsigned channelId		: 16;
	unsigned startTimeMjd		: 16;
	unsigned eventId		: 16;
	OpenTvTitleList titles;

public:
	OpenTvTitleSection(const uint8_t * const buffer);
	~OpenTvTitleSection(void);

	const OpenTvTitleList *getTitles(void) const;
	uint16_t getTitlesListSize(void) const;
};

class OpenTvSummary : public DescriptorContainer
{
protected:
	unsigned channelId	: 16;
	unsigned eventId	: 16;
	std::string summary;

public:
	OpenTvSummary(const uint8_t *const buffer);
	~OpenTvSummary(void);

	std::string getSummary(void) const;
	uint16_t getChannelId(void) const;
	uint16_t getEventId(void) const;
	void setChannelId(uint16_t channelid);
	void setEventId(uint16_t eventId);
};

typedef std::list<OpenTvSummary *> OpenTvSummaryList;
typedef OpenTvSummaryList::iterator OpenTvSummaryListIterator;
typedef OpenTvSummaryList::const_iterator OpenTvSummaryListConstIterator;

class OpenTvSummarySection : public LongCrcSection , public DescriptorContainer
{
protected:
	unsigned channelId		: 16;
	unsigned startTimeMjd		: 16;
	unsigned eventId		: 16;
	OpenTvSummaryList summaries;

public:
	OpenTvSummarySection(const uint8_t * const buffer);
	~OpenTvSummarySection(void);

	const OpenTvSummaryList *getSummaries(void) const;
	uint16_t getSummariesListSize(void) const;
};

#endif /* __OPENTV_H__ */
