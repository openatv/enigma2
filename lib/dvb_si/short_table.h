/*
 * $Id: short_table.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_table_short_table_h__
#define __dvb_table_short_table_h__

#include <lib/dvb_si/packet_id.h>
#include <lib/dvb_si/table_id.h>
#include <inttypes.h>
#include <vector>

class ShortTable
{
	protected:
		unsigned tableId				: 8;
		unsigned sectionSyntaxIndicator			: 1;
		unsigned reserved1				: 1;
		unsigned reserved2				: 2;
		unsigned sectionLength				: 12;

	public:
		ShortTable(const uint8_t * const buffer);

		static const uint8_t CRC32 = 0;
		static const uint16_t LENGTH = 1024;
		static const enum PacketId PID = PID_RESERVED;
		static const uint8_t SYNTAX = 0;
		static const enum TableId TID = TID_RESERVED;
		static const uint32_t TIMEOUT = 0;

		uint8_t getTableId(void) const;
		uint8_t getSectionSyntaxIndicator(void) const;
		uint16_t getSectionLength(void) const;
};

typedef std::vector<ShortTable *> ShortTableVector;
typedef ShortTableVector::iterator ShortTableIterator;
typedef ShortTableVector::const_iterator ShortTableConstIterator;

#endif /* __dvb_table_short_table_h__ */
