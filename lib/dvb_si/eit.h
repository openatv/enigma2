/*
 * $Id: eit.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
 *
 * (C) 2002-2003 Andreas Oberritter <obi@saftware.de>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
 *
 */

#ifndef __dvb_table_eit_h__
#define __dvb_table_eit_h__

#include <lib/dvb_si/container.h>
#include "long_crc_table.h"

class Event : public DescriptorContainer
{
	protected:
		unsigned eventId				: 16;
		unsigned startTimeMjd				: 16;
		unsigned startTimeBcd				: 24;
		unsigned duration				: 24;
		unsigned runningStatus				: 3;
		unsigned freeCaMode				: 1;
		unsigned descriptorsLoopLength			: 12;

	public:
		Event(const uint8_t * const buffer);

		uint16_t getEventId(void) const;
		uint16_t getStartTimeMjd(void) const;
		uint32_t getStartTimeBcd(void) const;
		uint32_t getDuration(void) const;
		uint8_t getRunningStatus(void) const;
		uint8_t getFreeCaMode(void) const;
};

typedef std::vector<Event *> EventVector;
typedef EventVector::iterator EventIterator;
typedef EventVector::const_iterator EventConstIterator;

class EventInformationTable : public LongCrcTable
{
	protected:
		unsigned transportStreamId			: 16;
		unsigned originalNetworkId			: 16;
		unsigned segmentLastSectionNumber		: 8;
		unsigned lastTableId				: 8;
		EventVector events;

	public:
		EventInformationTable(const uint8_t * const buffer);
		~EventInformationTable(void);

		static const uint16_t LENGTH = 4096;
		static const enum PacketId PID = PID_EIT;
		static const enum TableId TID = TID_EIT_ACTUAL;
		static const uint32_t TIMEOUT = 3000;

		uint16_t getTransportStreamId(void) const;
		uint16_t getOriginalNetworkId(void) const;
		uint8_t getLastSectionNumber(void) const;
		uint8_t getLastTableId(void) const;
		const EventVector *getEvents(void) const;
};

typedef std::vector<EventInformationTable *> EventInformationTableVector;
typedef EventInformationTableVector::iterator EventInformationTableIterator;
typedef EventInformationTableVector::const_iterator EventInformationTableConstIterator;

#endif /* __dvb_table_eit_h__ */
