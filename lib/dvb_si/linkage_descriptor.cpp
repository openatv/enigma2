/*
 * $Id: linkage_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
 *
 * (C) 2003 Andreas Oberritter <obi@saftware.de>
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

#include <lib/dvb_si/linkage_descriptor.h>

LinkageDescriptor::LinkageDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	transportStreamId = (buffer[2] << 8) | buffer[3];
	originalNetworkId = (buffer[4] << 8) | buffer[5];
	serviceId = (buffer[6] << 8) | buffer[7];
	linkageType = buffer[8];

	if (linkageType != 0x08)
	{
		if (descriptorLength < 7)
			return;

		for (uint16_t i = 0; i < descriptorLength - 7; ++i)
			privateDataBytes.push_back(buffer[i + 9]);
	}

	else {
		handOverType = (buffer[9] >> 4) & 0x0f;
		reserved = (buffer[9] >> 1) & 0x07;
		originType = buffer[9] & 0x01;

		uint8_t offset = 0;

		if ((handOverType >= 0x01) && (handOverType <= 0x03)) {
			networkId = (buffer[10] << 8) | buffer[11];
			offset += 2;
		}

		if (originType == 0x00) {
			initialServiceId = (buffer[offset + 10] << 8) | buffer[offset + 11];
			offset += 2;
		}
		
		if (descriptorLength >= (unsigned)(offset+8))
			for (uint16_t i = 0; i < descriptorLength - (offset + 8); ++i)
				privateDataBytes.push_back(buffer[i + offset + 10]);
	}
}

uint16_t LinkageDescriptor::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t LinkageDescriptor::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

uint16_t LinkageDescriptor::getServiceId(void) const
{
	return serviceId;
}

uint8_t LinkageDescriptor::getLinkageType(void) const
{
	return linkageType;
}

const PrivateDataByteVector *LinkageDescriptor::getPrivateDataBytes(void) const
{
	return &privateDataBytes;
}

uint8_t LinkageDescriptor::getHandOverType(void) const
{
	return handOverType;
}

uint8_t LinkageDescriptor::getOriginType(void) const
{
	return originType;
}

uint16_t LinkageDescriptor::getNetworkId(void) const
{
	return networkId;
}

uint16_t LinkageDescriptor::getInitialServiceId(void) const
{
	return initialServiceId;
}

