/*
 * $Id: mosaic_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/mosaic_descriptor.h>

ElementaryCellField::ElementaryCellField (const uint8_t * const buffer)
{
	reserved = (buffer[0] >> 6) & 0x03;
	elementaryCellId = buffer[0] & 0x3F;
}

uint8_t ElementaryCellField::getElementaryCellId(void) const
{
	return elementaryCellId;
}

MosaicCell::MosaicCell (const uint8_t * const buffer)
{
	logicalCellId = (buffer[0] >> 2) & 0x3F;
	reserved = (((buffer[0] & 0x03) << 8) | (buffer[1] & 0xF1)) >> 3;
	logicalCellPresentationInfo = buffer[1] & 0x07;
	elementaryCellFieldLength = buffer[2];

	for (uint16_t i = 0; i < elementaryCellFieldLength; ++i)
		elementaryCellFields.push_back(new ElementaryCellField(&buffer[i + 3]));

	cellLinkageInfo = buffer[elementaryCellFieldLength + 3];

	switch (cellLinkageInfo) {
	case 0x01:
		bouquetId = (buffer[elementaryCellFieldLength + 4] << 8) | buffer[elementaryCellFieldLength + 5];
		break;
	case 0x02:
	case 0x03:
	case 0x04:
		originalNetworkId = (buffer[elementaryCellFieldLength + 4] << 8) | buffer[elementaryCellFieldLength + 5];
		transportStreamId = (buffer[elementaryCellFieldLength + 6] << 8) | buffer[elementaryCellFieldLength + 7];
		serviceId = (buffer[elementaryCellFieldLength + 8] << 8) | buffer[elementaryCellFieldLength + 9];
		break;
	default:
		break;
	}

	if (cellLinkageInfo == 0x04)
		eventId = (buffer[elementaryCellFieldLength + 10] << 8) | buffer[elementaryCellFieldLength + 11];
}

MosaicCell::~MosaicCell(void)
{
	for (ElementaryCellFieldIterator i = elementaryCellFields.begin(); i != elementaryCellFields.end(); ++i)
		delete *i;
}

uint8_t MosaicCell::getLogicalCellId(void) const
{
	return logicalCellId;
}

uint8_t MosaicCell::getLogicalCellPresentationInfo(void) const
{
	return logicalCellPresentationInfo;
}

const ElementaryCellFieldVector *MosaicCell::getElementaryCellFields(void) const
{
	return &elementaryCellFields;
}

uint8_t MosaicCell::getCellLinkageInfo(void) const
{
	return cellLinkageInfo;
}

uint16_t MosaicCell::getBouquetId(void) const
{
	return bouquetId;
}

uint16_t MosaicCell::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

uint16_t MosaicCell::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t MosaicCell::getServiceId(void) const
{
	return serviceId;
}

uint16_t MosaicCell::getEventId(void) const
{
	return eventId;
}

MosaicDescriptor::MosaicDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	if (descriptorLength < 1)
		return;
	
	mosaicEntryPoint = (buffer[2] >> 7) & 0x01;
	numberOfHorizontalElementaryCells = (buffer[2] >> 4) & 0x07;
	reserved = (buffer[2] >> 3) & 0x01;
	numberOfVerticalElementaryCells = buffer[2] & 0x07;

	for (uint16_t i = 0; i < descriptorLength - 1; i += buffer[i + 6] + 2) {
		mosaicCells.push_back(new MosaicCell(&buffer[i + 1]));
		switch (buffer[i + 6 + buffer[i + 6] + 1]) {
		case 0x01:
			i += 2;
			break;
		case 0x02:
		case 0x03:
			i += 6;
			break;
		case 0x04:
			i += 8;
			break;
		default:
			break;
		}
	}
}

MosaicDescriptor::~MosaicDescriptor(void)
{
	for (MosaicCellIterator i = mosaicCells.begin(); i != mosaicCells.end(); ++i)
		delete *i;
}

uint8_t MosaicDescriptor::getMosaicEntryPoint(void) const
{
	return mosaicEntryPoint;
}

uint8_t MosaicDescriptor::getNumberOfHorizontalElementaryCells(void) const
{
	return numberOfHorizontalElementaryCells;
}

uint8_t MosaicDescriptor::getNumberOfVerticalElementaryCells(void) const
{
	return numberOfVerticalElementaryCells;
}

const MosaicCellVector *MosaicDescriptor::getMosaicCells(void) const
{
	return &mosaicCells;
}
								
