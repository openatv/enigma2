/*
 * $Id: cell_frequency_link_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
 *
 * (C) 2003 Andreas Oberritter <obi@saftware.de>
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

#include <lib/dvb_si/cell_frequency_link_descriptor.h>

SubcellInfo::SubcellInfo(const uint8_t * const buffer)
{
	cellIdExtenstion = buffer[0];
	transposerFrequency = (buffer[1] << 24) | (buffer[2] << 16) | (buffer[3] << 8) | buffer[4];
}

uint8_t SubcellInfo::getCellIdExtension(void) const
{
	return cellIdExtenstion;
}

uint32_t SubcellInfo::getTransposerFrequency(void) const
{
	return transposerFrequency;
}

CellFrequencyLink::CellFrequencyLink(const uint8_t * const buffer)
{
	cellId = (buffer[0] << 8) | buffer[1];
	frequency = (buffer[2] << 24) | (buffer[3] << 16) | (buffer[4] << 8) | buffer[5];
	subcellInfoLoopLength = buffer[6];

	for (uint16_t i = 0; i < subcellInfoLoopLength; i += 5)
		subcells.push_back(new SubcellInfo(&buffer[i + 7]));
}

CellFrequencyLink::~CellFrequencyLink(void)
{
	for (SubcellInfoIterator i = subcells.begin(); i != subcells.end(); ++i)
		delete *i;
}

uint16_t CellFrequencyLink::getCellId(void) const
{
	return cellId;
}

uint32_t CellFrequencyLink::getFrequency(void) const
{
	return frequency;
}

const SubcellInfoVector *CellFrequencyLink::getSubcells(void) const
{
	return &subcells;
}

CellFrequencyLinkDescriptor::CellFrequencyLinkDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	for (uint16_t i = 0; i < descriptorLength; i += buffer[i + 10] + 6)
		cellFrequencyLinks.push_back(new CellFrequencyLink(&buffer[i + 2]));
}

CellFrequencyLinkDescriptor::~CellFrequencyLinkDescriptor(void)
{
	for (CellFrequencyLinkIterator i = cellFrequencyLinks.begin(); i != cellFrequencyLinks.end(); ++i)
		delete *i;
}

const CellFrequencyLinkVector *CellFrequencyLinkDescriptor::getCellFrequencyLinks(void) const
{
	return &cellFrequencyLinks;
}

