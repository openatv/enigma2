/*
 * $Id: linkage_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_linkage_descriptor_h__
#define __dvb_descriptor_linkage_descriptor_h__

#include "descriptor.h"

typedef std::vector<uint8_t> PrivateDataByteVector;
typedef PrivateDataByteVector::iterator PrivateDataByteIterator;
typedef PrivateDataByteVector::const_iterator PrivateDataByteConstIterator;

class LinkageDescriptor : public Descriptor
{
	protected:
		unsigned transportStreamId			: 16;
		unsigned originalNetworkId			: 16;
		unsigned serviceId				: 16;
		unsigned linkageType				: 8;
		PrivateDataByteVector privateDataBytes;
		unsigned handOverType				: 4;
		unsigned reserved				: 3;
		unsigned originType				: 1;
		unsigned networkId				: 16;
		unsigned initialServiceId			: 16;

	public:
		LinkageDescriptor(const uint8_t * const buffer);

		uint16_t getTransportStreamId(void) const;
		uint16_t getOriginalNetworkId(void) const;
		uint16_t getServiceId(void) const;
		uint8_t getLinkageType(void) const;
		const PrivateDataByteVector *getPrivateDataBytes(void) const;
		uint8_t getHandOverType(void) const;
		uint8_t getOriginType(void) const;
		uint16_t getNetworkId(void) const;
		uint16_t getInitialServiceId(void) const;
};

#endif /* __dvb_descriptor_linkage_descriptor_h__ */
