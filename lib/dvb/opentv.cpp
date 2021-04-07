#include <lib/dvb/opentv.h>

#include <lib/base/huffman.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>

#include <iostream>
#include <string>

#include <byteswap.h>
#include <dvbsi++/byte_stream.h>

extern const uint32_t crc32_table[256];

static uint32_t opentv_crc(const uint8_t *data, int size)
{
	uint32_t crc = 0;
	for (int i = 0; i < size; ++i)
		crc = (crc << 8) ^ crc32_table[((crc >> 24) ^ data[i]) & 0xFF];
	return crc;
}

OpenTvChannel::OpenTvChannel(const uint8_t * const buffer)
{
	serviceId = UINT16(&buffer[0]);
	serviceType = buffer[2] & 0x3f;
	channelId = UINT16(&buffer[3]);
	//uint16_t lcn = UINT16(&buffer[5]) & 0x3ff;
}

OpenTvChannel::~OpenTvChannel(void)
{
}

uint16_t OpenTvChannel::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t OpenTvChannel::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

uint16_t OpenTvChannel::getServiceId(void) const
{
	return serviceId;
}

uint16_t OpenTvChannel::getChannelId(void) const
{
	return channelId;
}

uint8_t OpenTvChannel::getServiceType(void) const
{
	return serviceType;
}

void OpenTvChannel::setTransportStreamId(uint16_t transportstreamid)
{
	transportStreamId = transportstreamid;
}

void OpenTvChannel::setOriginalNetworkId(uint16_t originalnetworkid)
{
	originalNetworkId = originalnetworkid;
}

OpenTvChannelSection::OpenTvChannelSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	uint16_t pos = 10;
	uint16_t loopLength = 0;
	uint16_t bytesLeft = sectionLength > 11 ? sectionLength - 11 : 0;
	uint16_t bytesLeft2 = sectionLength > 9 ? DVB_LENGTH(&buffer[8]) : 0;

	while (bytesLeft >= bytesLeft2 && bytesLeft2 > 1 && bytesLeft2 >= (loopLength = 2 + buffer[pos+1]))
	{
		pos += loopLength;
		bytesLeft -= loopLength;
		bytesLeft2 -= loopLength;
	}

	if (!bytesLeft2 && bytesLeft > 1)
	{
		bytesLeft2 = DVB_LENGTH(&buffer[pos]);
		bytesLeft -= 2;
		pos += 2;

		while (bytesLeft >= bytesLeft2 && bytesLeft2 > 4 && bytesLeft2 >= (loopLength = 6 + DVB_LENGTH(&buffer[pos+4])))
		{
			transportStreamId = UINT16(&buffer[pos]);
			originalNetworkId = UINT16(&buffer[pos+2]);
			transportDescriptorsLength = DVB_LENGTH(&buffer[pos+4]);

			for (int i = 6; i < loopLength; i += buffer[pos+i+1] + 2)
			{
				switch (buffer[pos+i])
				{
					case OPENTV_LOGICAL_CHANNEL_DESCRIPTOR:
					{
						descriptorLength = buffer[pos+i+1];
						if (descriptorLength >= 11)
						{
							//uint8_t regionFlag = buffer[pos+i+2];
							//uint8_t regionId = buffer[pos+i+3];

							uint32_t pos2 = pos + i + 4;
							uint16_t bytesLeft3 = descriptorLength - 2;
							uint16_t loopLength2 = 9;

							while (bytesLeft3 >= loopLength2 && bytesLeft3 % loopLength2 == 0)
							{
								OpenTvChannel *channel = new OpenTvChannel(&buffer[pos2]);
								channel->setTransportStreamId(transportStreamId);
								channel->setOriginalNetworkId(originalNetworkId);
								channels.push_back(channel);
								bytesLeft3 -= loopLength2;
								pos2 += loopLength2;
							}
						}
						break;
					}
					default:
						break;
				}
			}
			bytesLeft -= loopLength;
			bytesLeft2 -= loopLength;
			pos += loopLength;
		}
	}
}

OpenTvChannelSection::~OpenTvChannelSection(void)
{
	for (OpenTvChannelListIterator i = channels.begin(); i != channels.end(); ++i)
		delete *i;
}

const OpenTvChannelList *OpenTvChannelSection::getChannels(void) const
{
	return &channels;
}

uint16_t OpenTvChannelSection::getChannelsListSize(void) const
{
	return channels.size();
}

OpenTvTitle::OpenTvTitle(const uint8_t * const buffer, uint16_t startMjd)
{
	uint8_t descriptor_tag = buffer[0];

	if (descriptor_tag == OPENTV_EVENT_TITLE_DESCRIPTOR)
	{
		uint8_t descriptor_length = buffer[1];
		uint8_t titleLength = descriptor_length > 7 ? descriptor_length-7 : 0;

		uint32_t startSecond = (UINT16(&buffer[2]) << 1);

		startTimeBcd = ((startMjd - 40587) * 86400) + startSecond;

		// HACK ALERT: There is a bug somewhere in the data that causes some
		// events to be cataloged 0x20000 seconds further into the future
		// than they should be. In these cases "startSecond" will have a value
		// of 86400 seconds or greater. i.e. more than one day. When this
		// happens it indicates that the bug is present for the current event
		// and therefore the excess 0x20000 seconds is removed from "startTimeBcd".
		if (startSecond >= 86400)
			startTimeBcd -= 0x20000;

		duration = UINT16(&buffer[4]) << 1;

		//genre content
		//uint8_t flag1 = buffer[6];
		//uint8_t flag2 = buffer[7];
		//uint8_t flag3 = buffer[8];

		char tmp[OPENTV_EVENT_TITLE_LENGTH];
		memset(tmp, '\0', OPENTV_EVENT_TITLE_LENGTH);

		if (!huffman_decode (buffer + 9, titleLength, tmp, OPENTV_EVENT_TITLE_LENGTH * 2, false))
			tmp[0] = '\0';

		title = convertDVBUTF8(tmp, sizeof(tmp), 5);

		/* storing all the crc unique titles in the title reader phase,
		   would give us a titles reduction of 155,000 down to 13,000!
		   we currently add/delete as we go with reduction size ~5000 */
		uint8_t *otvt = new uint8_t[titleLength];
		memcpy(otvt, buffer + 9, titleLength);
		crc32 = opentv_crc(otvt, titleLength);
		delete [] otvt;
	}
}

OpenTvTitle::~OpenTvTitle(void)
{
}

std::string OpenTvTitle::getTitle(void) const
{
    return title;
}

uint32_t OpenTvTitle::getCRC32(void) const
{
	return crc32;
}

uint16_t OpenTvTitle::getChannelId(void) const
{
	return channelId;
}

uint32_t OpenTvTitle::getStartTime(void) const
{
	return startTimeBcd;
}

uint16_t OpenTvTitle::getEventId(void) const
{
	return eventId;
}

uint16_t OpenTvTitle::getDuration(void) const
{
	return duration;
}

void OpenTvTitle::setChannelId(uint16_t channelid)
{
	channelId = channelid;
}

void OpenTvTitle::setEventId(uint16_t eventid)
{
	eventId = eventid;
}

OpenTvTitleSection::OpenTvTitleSection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	if ((tableId != 0xa0) && (tableId != 0xa1) && (tableId != 0xa2) && (tableId != 0xa3)) return;

	startTimeMjd = UINT16(&buffer[8]);

	if ((tableIdExtension > 0) && (startTimeMjd > 0) && (sectionLength > 14))
	{
		uint16_t pos = 10;
		uint16_t bytesLeft = sectionLength > 11 ? sectionLength-11 : 0;
		uint16_t loopLength = 0;

		while (bytesLeft > 4 && bytesLeft >= (loopLength = buffer[pos+3]+4))
		{
			eventId = UINT16(&buffer[pos]);
			uint8_t descriptor_tag = buffer[pos+2];

			if (descriptor_tag == OPENTV_DESCRIPTOR_LOOP)
			{
				OpenTvTitle *title = new OpenTvTitle(&buffer[pos+4], startTimeMjd);
				title->setChannelId(tableIdExtension);
				title->setEventId(eventId);
				titles.push_back(title);
			}
			bytesLeft -= loopLength;
			pos += loopLength;
		}
	}
}

OpenTvTitleSection::~OpenTvTitleSection(void)
{
	for (OpenTvTitleListIterator i = titles.begin(); i != titles.end(); ++i)
		delete *i;
}

const OpenTvTitleList *OpenTvTitleSection::getTitles(void) const
{
	return &titles;
}

uint16_t OpenTvTitleSection::getTitlesListSize(void) const
{
	return titles.size();
}

OpenTvSummary::OpenTvSummary(const uint8_t * const buffer)
{
	uint16_t bytesLeft = buffer[1];
	uint16_t loopLength = 0;
	uint16_t pos = 2;

	while (bytesLeft > 0 && bytesLeft >= (loopLength = buffer[pos+1]+2))
	{
		uint8_t descriptor_tag = buffer[pos];
		uint8_t descriptorLength = buffer[pos+1];

		switch (descriptor_tag)
		{
			case OPENTV_EVENT_SUMMARY_DESCRIPTOR:
			{
				if (descriptorLength > 0)
				{
					char tmp[OPENTV_EVENT_SUMMARY_LENGTH];
					memset(tmp, '\0', OPENTV_EVENT_SUMMARY_LENGTH);

					if (!huffman_decode (buffer+pos+2, descriptorLength, tmp, OPENTV_EVENT_SUMMARY_LENGTH * 2, false))
						tmp[0] = '\0';

					summary = convertDVBUTF8(tmp, sizeof(tmp), 5);
				}
				break;
			}
			case OPENTV_EVENT_DESCRIPTION_DESCRIPTOR:
			{
				//TODO: read event description descriptor
				//mostly unused, huffman_decode same as summary
				break;
			}
			case OPENTV_EVENT_SERIES_LINK_DESCRIPTOR:
			{
				//TODO: read series link id for future recording
				//uint16_t seriesLink = UINT16(&buffer[pos+2]);
				break;
			}
			case 0xd0:
			{
				//TODO: read first showing 0xbf isNew? event flag
				//tag appears sometimes before summary with "New:" prepended titles.
				break;
			}
			default:
				break;
		}
		bytesLeft -= loopLength;
		pos += loopLength;
	}
}

OpenTvSummary::~OpenTvSummary(void)
{
}

std::string OpenTvSummary::getSummary(void) const
{
    return summary;
}

uint16_t OpenTvSummary::getChannelId(void) const
{
	return channelId;
}

uint16_t OpenTvSummary::getEventId(void) const
{
	return eventId;
}

void OpenTvSummary::setChannelId(uint16_t channelid)
{
	channelId = channelid;
}

void OpenTvSummary::setEventId(uint16_t eventid)
{
	eventId = eventid;
}

OpenTvSummarySection::OpenTvSummarySection(const uint8_t * const buffer) : LongCrcSection(buffer)
{
	if ((tableId != 0xa8) && (tableId != 0xa9) && (tableId != 0xaa) && (tableId != 0xab)) return;

	startTimeMjd = UINT16(&buffer[8]);

	if ((tableIdExtension > 0) && (startTimeMjd > 0) && (sectionLength > 14))
	{
		uint16_t pos = 10;
		uint16_t bytesLeft = sectionLength > 11 ? sectionLength-11 : 0;
		uint16_t loopLength = 0;

		while (bytesLeft > 4 && bytesLeft >= (loopLength = buffer[pos+3]+4))
		{
			eventId = UINT16(&buffer[pos]);

			uint8_t descriptor_tag = buffer[pos+2];
			uint8_t descriptorLength = buffer[pos+3];

			if ((descriptor_tag == OPENTV_DESCRIPTOR_LOOP) && (descriptorLength > 2))
			{
				OpenTvSummary *summary = new OpenTvSummary(&buffer[pos+2]);
				summary->setChannelId(tableIdExtension);
				summary->setEventId(eventId);
				summaries.push_back(summary);
			}
			bytesLeft -= loopLength;
			pos += loopLength;
		}
	}
}

OpenTvSummarySection::~OpenTvSummarySection(void)
{
	for (OpenTvSummaryListIterator i = summaries.begin(); i != summaries.end(); ++i)
		delete *i;
}

const OpenTvSummaryList *OpenTvSummarySection::getSummaries(void) const
{
	return &summaries;
}

uint16_t OpenTvSummarySection::getSummariesListSize(void) const
{
	return summaries.size();
}
