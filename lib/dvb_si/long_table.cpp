/*
 * $Id: long_table.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/long_table.h>

LongTable::LongTable(const uint8_t * const buffer) : ShortTable(buffer)
{
	tableIdExtension = (buffer[3] << 8) | buffer[4];
	reserved3 = (buffer[5] >> 6) & 0x03;
	versionNumber = (buffer[5] >> 1) & 0x1F;
	currentNextIndicator = buffer[5] & 0x01;
	sectionNumber = buffer[6];
	lastSectionNumber = buffer[7];
}

uint16_t LongTable::getTableIdExtension(void) const
{
	return tableIdExtension;
}

uint8_t LongTable::getVersionNumber(void) const
{
	return versionNumber;
}

uint8_t LongTable::getCurrentNextIndicator(void) const
{
	return currentNextIndicator;
}

uint8_t LongTable::getSectionNumber(void) const
{
	return sectionNumber;
}

uint8_t LongTable::getLastSectionNumber(void) const
{
	return lastSectionNumber;
}

bool LongTable::operator< (const LongTable &t) const
{
	return (sectionNumber < t.sectionNumber);
}

bool LongTable::operator> (const LongTable &t) const
{
	return (sectionNumber > t.sectionNumber);
}

bool LongTable::operator<= (const LongTable &t) const
{
	return (sectionNumber <= t.sectionNumber);
}

bool LongTable::operator>= (const LongTable &t) const
{
	return (sectionNumber >= t.sectionNumber);
}

bool LongTable::operator== (const LongTable &t) const
{
	return (sectionNumber == t.sectionNumber);
}

bool LongTable::operator!= (const LongTable &t) const
{
	return (sectionNumber != t.sectionNumber);
}

