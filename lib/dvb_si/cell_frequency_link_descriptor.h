/*
 * $Id: cell_frequency_link_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_cell_frequency_link_descriptor_h__
#define __dvb_descriptor_cell_frequency_link_descriptor_h__

#include "descriptor.h"

class SubcellInfo
{
	protected:
		unsigned cellIdExtenstion			: 8;
		unsigned transposerFrequency			: 32;

	public:
		SubcellInfo(const uint8_t * const buffer);

		uint8_t getCellIdExtension(void) const;
		uint32_t getTransposerFrequency(void) const;
};

typedef std::vector<SubcellInfo *> SubcellInfoVector;
typedef SubcellInfoVector::iterator SubcellInfoIterator;
typedef SubcellInfoVector::const_iterator SubcellInfoConstIterator;

class CellFrequencyLink
{
	protected:
		unsigned cellId					: 16;
		unsigned frequency				: 32;
		unsigned subcellInfoLoopLength			: 8;
		SubcellInfoVector subcells;

	public:
		CellFrequencyLink(const uint8_t * const buffer);
		~CellFrequencyLink(void);

		uint16_t getCellId(void) const;
		uint32_t getFrequency(void) const;
		const SubcellInfoVector *getSubcells(void) const;

};

typedef std::vector<CellFrequencyLink *> CellFrequencyLinkVector;
typedef CellFrequencyLinkVector::iterator CellFrequencyLinkIterator;
typedef CellFrequencyLinkVector::const_iterator CellFrequencyLinkConstIterator;

class CellFrequencyLinkDescriptor : public Descriptor
{
	protected:
		CellFrequencyLinkVector cellFrequencyLinks;

	public:
		CellFrequencyLinkDescriptor(const uint8_t * const buffer);
		~CellFrequencyLinkDescriptor(void);

		const CellFrequencyLinkVector *getCellFrequencyLinks(void) const;
};

#endif /* __dvb_descriptor_cell_frequency_link_descriptor_h__ */
