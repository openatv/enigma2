/*
 * $Id: vbi_data_descriptor.cpp,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#include <lib/dvb_si/vbi_data_descriptor.h>

VbiDataLine::VbiDataLine(const uint8_t * const buffer)
{
	reserved = (buffer[0] >> 6) & 0x03;
	fieldParity = (buffer[0] >> 5) & 0x01;
	lineOffset = buffer[0] & 0x1F;
}

uint8_t VbiDataLine::getFieldParity(void) const
{
	return fieldParity;
}

uint8_t VbiDataLine::getLineOffset(void) const
{
	return lineOffset;
}

VbiDataService::VbiDataService(const uint8_t * const buffer)
{
	uint16_t i;

	dataServiceId = buffer[0];
	dataServiceDescriptorLength = buffer[1];

	switch (dataServiceId) {
	case 0x01:
	case 0x02:
	case 0x04:
	case 0x05:
	case 0x06:
	case 0x07:
		for (i = 0; i < dataServiceDescriptorLength; ++i);
			vbiDataLines.push_back(new VbiDataLine(&buffer[i + 2]));
		break;

	default:
		for (i = 0; i < dataServiceDescriptorLength; ++i)
			reserved.push_back(buffer[i + 2]);
		break;
	}
}

VbiDataService::~VbiDataService(void)
{
	for (VbiDataLineIterator i = vbiDataLines.begin(); i != vbiDataLines.end(); ++i)
		delete *i;
}

uint8_t VbiDataService::getDataServiceId(void) const
{
	return dataServiceId;
}

const VbiDataLineVector *VbiDataService::getVbiDataLines(void) const
{
	return &vbiDataLines;
}

VbiDataDescriptor::VbiDataDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	for (uint16_t i = 0; i < descriptorLength; i += buffer[i + 3] + 2)
		vbiDataServices.push_back(new VbiDataService(&buffer[i + 2]));
}

VbiDataDescriptor::~VbiDataDescriptor(void)
{
	for (VbiDataServiceIterator i = vbiDataServices.begin(); i != vbiDataServices.end(); ++i)
		delete *i;
}

const VbiDataServiceVector *VbiDataDescriptor::getVbiDataServices(void) const
{
	return &vbiDataServices;
}

