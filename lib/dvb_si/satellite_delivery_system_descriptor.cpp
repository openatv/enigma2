/*
 * $Id: satellite_delivery_system_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/satellite_delivery_system_descriptor.h>

SatelliteDeliverySystemDescriptor::SatelliteDeliverySystemDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	frequency =
	(
		((buffer[2] >> 4)	* 10000000) +
		((buffer[2] & 0x0F)	* 1000000) +
		((buffer[3] >> 4)	* 100000) +
		((buffer[3] & 0x0F)	* 10000) +
		((buffer[4] >> 4)	* 1000) +
		((buffer[4] & 0x0F)	* 100) +
		((buffer[5] >> 4)	* 10) +
		((buffer[5] & 0x0F)	* 1)
	);

	orbitalPosition = (buffer[6] << 8) | buffer[7];
	westEastFlag = (buffer[8] >> 7) & 0x01;
	polarization = (buffer[8] >> 5) & 0x03;
	modulation = buffer[8] & 0x1F;

	symbolRate =
	(
		((buffer[9] >> 4)	* 1000000) +
		((buffer[9] & 0x0F)	* 100000) +
		((buffer[10] >> 4)	* 10000) +
		((buffer[10] & 0x0F)	* 1000) +
		((buffer[11] >> 4)	* 100) +
		((buffer[11] & 0x0F)	* 10) +
		((buffer[12] >> 4)	* 1)
	);

	fecInner = buffer[12] & 0x0F;
}

uint32_t SatelliteDeliverySystemDescriptor::getFrequency(void) const
{
	return frequency;
}

uint16_t SatelliteDeliverySystemDescriptor::getOrbitalPosition(void) const
{
	return orbitalPosition;
}

uint8_t SatelliteDeliverySystemDescriptor::getWestEastFlag(void) const
{
	return westEastFlag;
}

uint8_t SatelliteDeliverySystemDescriptor::getPolarization(void) const
{
	return polarization;
}

uint8_t SatelliteDeliverySystemDescriptor::getModulation(void) const
{
	return modulation;
}

uint32_t SatelliteDeliverySystemDescriptor::getSymbolRate(void) const
{
	return symbolRate;
}

uint8_t SatelliteDeliverySystemDescriptor::getFecInner(void) const
{
	return fecInner;
}

