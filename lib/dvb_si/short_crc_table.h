/*
 * $Id: short_crc_table.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_table_short_crc_table_h__
#define __dvb_table_short_crc_table_h__

#include "short_table.h"

class ShortCrcTable : public ShortTable
{
	protected:
		unsigned crc32					: 32;

	public:
		ShortCrcTable(const uint8_t * const buffer);

		static const uint8_t CRC32 = 1;

		uint32_t getCrc32(void) const;
};

typedef std::vector<ShortCrcTable *> ShortCrcTableVector;
typedef ShortCrcTableVector::iterator ShortCrcTableIterator;
typedef ShortCrcTableVector::const_iterator ShortCrcTableConstIterator;

#endif /* __dvb_table_short_crc_table_h__ */
