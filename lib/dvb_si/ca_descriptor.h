/*
 * $Id: ca_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_ca_descriptor_h__
#define __dvb_descriptor_ca_descriptor_h__

#include "descriptor.h"

typedef std::vector<uint8_t> PrivateDataByteVector;
typedef PrivateDataByteVector::iterator PrivateDataByteIterator;
typedef PrivateDataByteVector::const_iterator PrivateDataByteConstIterator;

class CaDescriptor : public Descriptor
{
	protected:
		unsigned caSystemId				: 16;
		unsigned reserved				: 3;
		unsigned caPid					: 13;
		PrivateDataByteVector privateDataBytes;

	public:
		CaDescriptor(const uint8_t * const buffer);

		uint16_t getCaSystemId(void) const;
		uint16_t getCaPid(void) const;
		const PrivateDataByteVector *getPrivateDataBytes(void) const;
};

typedef std::vector<CaDescriptor *> CaDescriptorVector;
typedef CaDescriptorVector::iterator CaDescriptorIterator;
typedef CaDescriptorVector::const_iterator CaDescriptorConstIterator;

#endif /* __dvb_descriptor_ca_descriptor_h__ */
