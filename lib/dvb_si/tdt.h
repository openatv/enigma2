/*
 * $Id: tdt.h,v 1.1 2003-10-17 15:36:39 tmbinc Exp $
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

#ifndef __dvb_table_tdt_h__
#define __dvb_table_tdt_h__

#include "short_table.h"

class TimeAndDateTable : public ShortTable
{
	protected:
		unsigned utcTimeMjd				: 16;
		unsigned utcTimeBcd				: 24;

	public:
		TimeAndDateTable(const uint8_t * const buffer);

		static const enum PacketId PID = PID_TDT;
		static const enum TableId TID = TID_TDT;
		static const uint32_t TIMEOUT = 36000;

		uint16_t getUtcTimeMjd(void) const;
		uint32_t getUtcTimeBcd(void) const;
};

typedef std::vector<TimeAndDateTable *> TimeAndDateTableVector;
typedef TimeAndDateTableVector::iterator TimeAndDateTableIterator;
typedef TimeAndDateTableVector::const_iterator TimeAndDateTableConstIterator;

#endif /* __dvb_table_tdt_h__ */
