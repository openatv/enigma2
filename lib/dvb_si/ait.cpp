/*
 * $Id: ait.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/ait.h>

ApplicationIdentifier::ApplicationIdentifier(const uint8_t * const buffer)
{
	organisationId = (buffer[0] << 24) | (buffer[1] << 16) | (buffer[2] << 8) | buffer[3];
	applicationId = (buffer[4] << 8) | buffer[5];
}

uint32_t ApplicationIdentifier::getOrganisationId(void) const
{
	return organisationId;
}

uint16_t ApplicationIdentifier::getApplicationId(void) const
{
	return applicationId;
}

ApplicationInformation::ApplicationInformation(const uint8_t * const buffer)
{
	applicationIdentifier = new ApplicationIdentifier(&buffer[0]);
	applicationControlCode = buffer[6];
	reserved = (buffer[7] >> 4) & 0x0f;
	applicationDescriptorsLoopLength = ((buffer[7] & 0x0f) << 8) | buffer[8];

	for (uint16_t i = 0; i < applicationDescriptorsLoopLength; i += buffer[i + 10] + 2)
		descriptor(&buffer[i + 9]);
}

ApplicationInformation::~ApplicationInformation(void)
{
	delete applicationIdentifier;
}

const ApplicationIdentifier *ApplicationInformation::getApplicationIdentifier(void) const
{
	return applicationIdentifier;
}

uint8_t ApplicationInformation::getApplicationControlCode(void) const
{
	return applicationControlCode;
}

ApplicationInformationTable::ApplicationInformationTable(const uint8_t * const buffer) : LongCrcTable(buffer)
{
	reserved4 = (buffer[8] >> 4) & 0x0f;
	commonDescriptorsLength = ((buffer[8] & 0x0f) << 8) | buffer[9];

	for (uint16_t i = 0; i < commonDescriptorsLength; i += buffer[i + 11] + 2)
		descriptor(&buffer[i + 10]);

	reserved5 = (buffer[commonDescriptorsLength + 10] >> 4) & 0x0f;
	applicationLoopLength = ((buffer[commonDescriptorsLength + 10] & 0x0f) << 8) | buffer[commonDescriptorsLength + 11];

	for (uint16_t i = 0; i < applicationLoopLength; i += 9) {
		ApplicationInformation *a = new ApplicationInformation(&buffer[commonDescriptorsLength + 12]);
		applicationInformation.push_back(a);
		i += a->applicationDescriptorsLoopLength;
	}
}

ApplicationInformationTable::~ApplicationInformationTable(void)
{
	for (ApplicationInformationIterator i = applicationInformation.begin(); i != applicationInformation.end(); ++i)
		delete *i;
}

const ApplicationInformationVector *ApplicationInformationTable::getApplicationInformation(void) const
{
	return &applicationInformation;
}

