/*
 * $Id: terrestrial_delivery_system_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_terrestrial_delivery_system_descriptor_h__
#define __dvb_descriptor_terrestrial_delivery_system_descriptor_h__

#include "descriptor.h"

class TerrestrialDeliverySystemDescriptor : public Descriptor
{
	protected:
		unsigned centreFrequency			: 32;
		unsigned bandwidth				: 3;
		unsigned reserved				: 5;
		unsigned constellation				: 2;
		unsigned hierarchyInformation			: 3;
		unsigned codeRateHpStream			: 3;
		unsigned codeRateLpStream			: 3;
		unsigned guardInterval				: 2;
		unsigned transmissionMode			: 2;
		unsigned otherFrequencyFlag			: 1;
		unsigned reserved2				: 32;

	public:
		TerrestrialDeliverySystemDescriptor(const uint8_t * const buffer);

		uint32_t getCentreFrequency(void) const;
		uint8_t getBandwidth(void) const;
		uint8_t getConstellation(void) const;
		uint8_t getHierarchyInformation(void) const;
		uint8_t getCodeRateHpStream(void) const;
		uint8_t getCodeRateLpStream(void) const;
		uint8_t getGuardInterval(void) const;
		uint8_t getTransmissionMode(void) const;
		uint8_t getOtherFrequencyFlag(void) const;
};

#endif /* __dvb_descriptor_terrestrial_delivery_system_descriptor_h__ */
