/*
 * $Id: tot.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/tot.h>

TimeOffsetTable::TimeOffsetTable(const uint8_t * const buffer) : ShortCrcTable(buffer)
{
	utcTimeMjd = (buffer[3] << 8) | buffer[4];
	utcTimeBcd = (buffer[5] << 16) | (buffer[6] << 8) | buffer[7];
	reserved = (buffer[8] >> 4) & 0x0f;
	descriptorsLoopLength = ((buffer[8] & 0x0f) << 8) | buffer[9];

	for (uint16_t i = 0; i < descriptorsLoopLength; i += buffer[i + 11] + 2)
		descriptor(&buffer[i + 10]);
}

uint16_t TimeOffsetTable::getUtcTimeMjd(void) const
{
	return utcTimeMjd;
}

uint32_t TimeOffsetTable::getUtcTimeBcd(void) const
{
	return utcTimeBcd;
}

