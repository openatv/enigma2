/*
 * $Id: system_clock_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_system_clock_descriptor_h__
#define __dvb_descriptor_system_clock_descriptor_h__

#include "descriptor.h"

class SystemClockDescriptor : public Descriptor
{
	protected:
		unsigned externalClockReferenceIndicator	: 1;
		unsigned reserved				: 1;
		unsigned clockAccuracyInteger			: 6;
		unsigned clockAccuracyExponent			: 3;
		unsigned reserved2				: 5;

	public:
		SystemClockDescriptor(const uint8_t * const buffer);

		uint8_t getExternalClockReferenceIndicator(void) const;
		uint8_t getClockAccuracyInteger(void) const;
		uint8_t getClockAccuracyExponent(void) const;
};

#endif /* __dvb_descriptor_system_clock_descriptor_h__ */
