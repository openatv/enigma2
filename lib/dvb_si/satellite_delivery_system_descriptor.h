/*
 * $Id: satellite_delivery_system_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_satellite_delivery_system_descriptor_h__
#define __dvb_descriptor_satellite_delivery_system_descriptor_h__

#include "descriptor.h"

class SatelliteDeliverySystemDescriptor : public Descriptor
{
	protected:
		unsigned frequency				: 32;
		unsigned orbitalPosition			: 16;
		unsigned westEastFlag				: 1;
		unsigned polarization				: 2;
		unsigned modulation				: 5;
		unsigned symbolRate				: 28;
		unsigned fecInner				: 4;

	public:
		SatelliteDeliverySystemDescriptor(const uint8_t * const buffer);

		uint32_t getFrequency(void) const;
		uint16_t getOrbitalPosition(void) const;
		uint8_t getWestEastFlag(void) const;
		uint8_t getPolarization(void) const;
		uint8_t getModulation(void) const;
		uint32_t getSymbolRate(void) const;
		uint8_t getFecInner(void) const;
};

#endif /* __dvb_descriptor_satellite_delivery_system_descriptor_h__ */
