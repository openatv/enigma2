/*
 * $Id: nvod_reference_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/nvod_reference_descriptor.h>


NvodReference::NvodReference(const uint8_t * const buffer)
{
	transportStreamId = (buffer[0] << 8) | buffer[1];
	originalNetworkId = (buffer[2] << 8) | buffer[3];
	serviceId = (buffer[4] << 8) | buffer[5];
}

uint16_t NvodReference::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t NvodReference::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

uint16_t NvodReference::getServiceId(void) const
{
	return serviceId;
}

NvodReferenceDescriptor::NvodReferenceDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	for (uint16_t i = 0; i < descriptorLength; i += 6)
		nvodReferences.push_back(new NvodReference(&buffer[i + 2]));
}

NvodReferenceDescriptor::~NvodReferenceDescriptor(void)
{
	for (NvodReferenceIterator i = nvodReferences.begin(); i != nvodReferences.end(); ++i)
		delete *i;
}

const NvodReferenceVector *NvodReferenceDescriptor::getNvodReferences(void) const
{
	return &nvodReferences;
}

