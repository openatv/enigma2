/*
 * $Id: telephone_descriptor.cpp,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#include <lib/dvb_si/telephone_descriptor.h>

TelephoneDescriptor::TelephoneDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	reserved = (buffer[2] >> 6) & 0x03;
	foreignAvailability = (buffer[2] >> 5) & 0x01;
	connectionType = buffer[2] & 0x1f;
	reserved2 = (buffer[3] >> 7) & 0x01;
	countryPrefixLength = (buffer[3] >> 5) & 0x03;
	internationalAreaCodeLength = (buffer[3] >> 2) & 0x07;
	operatorCodeLength = buffer[3] & 0x03;
	reserved3 = (buffer[4] >> 7) & 0x01;
	nationalAreaCodeLength = (buffer[4] >> 4) & 0x07;
	coreNumberLength = buffer[4] & 0x0f;

	uint16_t offset = 5;
	countryPrefix.assign((char *)&buffer[offset], countryPrefixLength);
	offset += countryPrefixLength;
	internationalAreaCode.assign((char *)&buffer[offset], internationalAreaCodeLength);
	offset += internationalAreaCodeLength;
	operatorCode.assign((char *)&buffer[offset], operatorCodeLength);
	offset += operatorCodeLength;
	nationalAreaCode.assign((char *)&buffer[offset], nationalAreaCodeLength);
	offset += nationalAreaCodeLength;
	coreNumber.assign((char *)&buffer[offset], coreNumberLength);
}

uint8_t TelephoneDescriptor::getForeignAvailability(void) const
{
	return foreignAvailability;
}

uint8_t TelephoneDescriptor::getConnectionType(void) const
{
	return connectionType;
}

std::string TelephoneDescriptor::getCountryPrefix(void) const
{
	return countryPrefix;
}

std::string TelephoneDescriptor::getInternationalAreaCode(void) const
{
	return internationalAreaCode;
}

std::string TelephoneDescriptor::getOperatorCode(void) const
{
	return operatorCode;
}

std::string TelephoneDescriptor::getNationalAreaCode(void) const
{
	return nationalAreaCode;
}

std::string TelephoneDescriptor::getCoreNumber(void) const
{
	return coreNumber;
}

