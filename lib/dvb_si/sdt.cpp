/*
 * $Id: sdt.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/sdt.h>

ServiceDescription::ServiceDescription(const uint8_t * const buffer)
{
	serviceId = (buffer[0] << 8) | buffer[1];
	reserved1 = (buffer[2] >> 2) & 0x3F;
	eitScheduleFlag = (buffer[2] >> 1) & 0x01;
	eitPresentFollowingFlag = buffer[2] & 0x01;
	runningStatus = (buffer[3] >> 5) & 0x07;
	freeCaMode = (buffer[3] >> 4) & 0x01;
	descriptorsLoopLength = ((buffer[3] & 0x0F) << 8) | buffer[4];

	for (uint16_t i = 5; i < descriptorsLoopLength + 5; i += buffer[i + 1] + 2)
		descriptor(&buffer[i]);
}

uint16_t ServiceDescription::getServiceId(void) const
{
	return serviceId;
}

uint8_t ServiceDescription::getEitScheduleFlag(void) const
{
	return eitScheduleFlag;
}

uint8_t ServiceDescription::getEitPresentFollowingFlag(void) const
{
	return eitPresentFollowingFlag;
}

uint8_t ServiceDescription::getRunningStatus(void) const
{
	return runningStatus;
}

uint8_t ServiceDescription::getFreeCaMode(void) const
{
	return freeCaMode;
}

ServiceDescriptionTable::ServiceDescriptionTable(const uint8_t * const buffer) : LongCrcTable (buffer)
{
	originalNetworkId = (buffer[8] << 8) | buffer[9];
	reserved4 = buffer[10];

	for (uint16_t i = 11; i < sectionLength - 1; i += ((buffer[i + 3] & 0x0F) | buffer[i + 4]) + 5)
		description.push_back(new ServiceDescription(&buffer[i]));
}

ServiceDescriptionTable::~ServiceDescriptionTable(void)
{
	for (ServiceDescriptionIterator i = description.begin(); i != description.end(); ++i)
		delete *i;
}

uint16_t ServiceDescriptionTable::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

const ServiceDescriptionVector *ServiceDescriptionTable::getDescriptions(void) const
{
	return &description;
}

