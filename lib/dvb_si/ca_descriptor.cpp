/*
 * $Id: ca_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/ca_descriptor.h>

CaDescriptor::CaDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	caSystemId = (buffer[2] << 8) | buffer[3];
	reserved = buffer[4] >> 5;
	caPid = ((buffer[4] & 0x1F) << 8) | buffer[5];

	if (descriptorLength < 4)
		return;
	for (uint16_t i = 0; i < descriptorLength - 4; ++i)
		privateDataBytes.push_back(buffer[i + 6]);
}

uint16_t CaDescriptor::getCaSystemId(void) const
{
	return caSystemId;
}

uint16_t CaDescriptor::getCaPid(void) const
{
	return caPid;
}

const PrivateDataByteVector *CaDescriptor::getPrivateDataBytes(void) const
{
	return &privateDataBytes;
}

