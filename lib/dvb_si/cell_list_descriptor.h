/*
 * $Id: cell_list_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_cell_list_descriptor_h__
#define __dvb_descriptor_cell_list_descriptor_h__

#include "descriptor.h"

class Subcell
{
	protected:
		unsigned cellIdExtension			: 8;
		unsigned subcellLatitude			: 16;
		unsigned subcellLongitude			: 16;
		unsigned subcellExtendOfLatitude		: 12;
		unsigned subcellExtendOfLongitude		: 12;

	public:
		Subcell(const uint8_t * const buffer);

		uint8_t getCellIdExtension(void) const;
		uint16_t getSubcellLatitude(void) const;
		uint16_t getSubcellLongtitude(void) const;
		uint16_t getSubcellExtendOfLatitude(void) const;
		uint16_t getSubcellExtendOfLongtitude(void) const;
};

typedef std::vector<Subcell *> SubcellVector;
typedef SubcellVector::iterator SubcellIterator;
typedef SubcellVector::const_iterator SubcellConstIterator;

class Cell
{
	protected:
		unsigned cellId					: 16;
		unsigned cellLatitude				: 16;
		unsigned cellLongtitude				: 16;
		unsigned cellExtendOfLatitude			: 12;
		unsigned cellExtendOfLongtitude			: 12;
		unsigned subcellInfoLoopLength			: 8;
		SubcellVector subcells;

	public:
		Cell(const uint8_t * const buffer);
		~Cell(void);

		uint16_t getCellId(void) const;
		uint16_t getCellLatitude(void) const;
		uint16_t getCellLongtitude(void) const;
		uint16_t getCellExtendOfLatitude(void) const;
		uint16_t getCellExtendOfLongtitude(void) const;
		const SubcellVector *getSubcells(void) const;
};

typedef std::vector<Cell *> CellVector;
typedef CellVector::iterator CellIterator;
typedef CellVector::const_iterator CellConstIterator;

class CellListDescriptor : public Descriptor
{
	protected:
		CellVector cells;

	public:
		CellListDescriptor(const uint8_t * const buffer);
		~CellListDescriptor(void);

		const CellVector *getCells(void) const;
};

#endif /* __dvb_descriptor_cell_list_descriptor_h__ */
