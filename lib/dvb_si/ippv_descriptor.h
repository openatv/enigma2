/*
 * $Id: ippv_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_ippv_descriptor_h__
#define __dvb_descriptor_ippv_descriptor_h__

#include "descriptor.h"

/* 0xF0 */
class CurrencyEntry
{
	public:
		CurrencyEntry(const uint8_t * const buffer);
};

class CountryEntry
{
	protected:
		unsigned country				: 24;
		unsigned unknown				: 5;
		unsigned currencyAndCostDetail			: 3;
		// if (currencyAndCostDetail & 1)
		unsigned bcdCost				: 32;
		unsigned length					: 8;
		std::vector<CurrencyEntry *> currency;

	public:
		CountryEntry(const uint8_t * const buffer);
};

class IppvDescriptor : public Descriptor
{
	protected:
		unsigned unknown1				: 16;
		unsigned unknown2				: 16;
		unsigned unknown3				: 16;
		unsigned IppvEventId				: 16;
		std::vector<CountryEntry *> country;

	private:
		IppvDescriptor(const uint8_t * const buffer);
};

#endif /* __dvb_descriptor_ippv_descriptor_h__ */
