/*
 * $Id: short_table.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/short_table.h>

ShortTable::ShortTable(const uint8_t * const buffer)
{
	tableId = buffer[0];
	sectionSyntaxIndicator = (buffer[1] >> 7) & 0x01;
	reserved1 = (buffer[1] >> 6) & 0x01;
	reserved2 = (buffer[1] >> 4) & 0x03;
	sectionLength = ((buffer[1] & 0x0F) << 8) | buffer[2];
}

uint8_t ShortTable::getTableId(void) const
{
	return tableId;
}

uint8_t ShortTable::getSectionSyntaxIndicator(void) const
{
	return sectionSyntaxIndicator;
}

uint16_t ShortTable::getSectionLength(void) const
{
	return sectionLength;
}

