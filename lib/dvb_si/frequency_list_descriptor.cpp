/*
 * $Id: frequency_list_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/frequency_list_descriptor.h>

FrequencyListDescriptor::FrequencyListDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	if (descriptorLength < 1)
		return;
	reserved = (buffer[2] >> 2) & 0x3f;
	codingType = buffer[2] & 0x03;

	for (uint16_t i = 0; i < descriptorLength - 1; i += 4)
		centreFrequencies.push_back((buffer[i + 3] << 24) | (buffer[i + 4] << 16) | (buffer[i + 5] << 8) | buffer[i + 6]);
}

uint8_t FrequencyListDescriptor::getCodingType(void) const
{
	return codingType;
}

const CentreFrequencyVector *FrequencyListDescriptor::getCentreFrequencies(void) const
{
	return &centreFrequencies;
}

