/*
 * $Id: nit.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/nit.h>

TransportStreamInfo::TransportStreamInfo(const uint8_t * const buffer)
{
	transportStreamId = (buffer[0] << 8) | buffer[1];
	originalNetworkId = (buffer[2] << 8) | buffer[3];
	reserved1 = (buffer[4] >> 8) & 0x0F;
	transportDescriptorsLength = ((buffer[4] & 0x0F) << 8) | buffer[5];

	for (uint16_t i = 6; i < transportDescriptorsLength + 6; i += buffer[i + 1] + 2)
		descriptor(&buffer[i]);
}

uint16_t TransportStreamInfo::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t TransportStreamInfo::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

NetworkInformationTable::NetworkInformationTable(const uint8_t * const buffer) : LongCrcTable(buffer)
{
	reserved4 = (buffer[8] >> 5) & 0x0F;
	networkDescriptorsLength = ((buffer[8] & 0x0F) << 8) | buffer[9];

	for (uint16_t i = 10; i < networkDescriptorsLength + 10; i += buffer[i + 1] + 2)
		descriptor(&buffer[i]);

	reserved5 = (buffer[networkDescriptorsLength + 10] >> 4) & 0x0F;
	transportStreamLoopLength = ((buffer[networkDescriptorsLength + 10] & 0x0F) << 8) | buffer[networkDescriptorsLength + 11];

	for (uint16_t i = networkDescriptorsLength + 12; i < sectionLength + 3 - 4; i += ((buffer[i + 4] & 0x0F) | buffer[i + 5]) + 6)
		tsInfo.push_back(new TransportStreamInfo(&buffer[i]));
}

NetworkInformationTable::~NetworkInformationTable(void)
{
	for (TransportStreamInfoIterator i = tsInfo.begin(); i != tsInfo.end(); ++i)
		delete *i;
}

const TransportStreamInfoVector *NetworkInformationTable::getTsInfo(void) const
{
	return &tsInfo;
}

