/*
 * $Id: pmt.h,v 1.2 2005-04-30 17:57:48 tmbinc Exp $
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

#ifndef __dvb_table_pmt_h__
#define __dvb_table_pmt_h__

#include <lib/dvb_si/container.h>
#include "long_crc_table.h"

class ElementaryStreamInfo : public DescriptorContainer
{
	protected:
		unsigned streamType				: 8;
		unsigned reserved1				: 3;
		unsigned elementaryPid				: 13;
		unsigned reserved2				: 4;
		unsigned esInfoLength				: 12;

	public:
		ElementaryStreamInfo(const uint8_t * const buffer);

		uint8_t getType(void) const;
		uint16_t getPid(void) const;

	friend class CaElementaryStreamInfo;

};

typedef std::vector<ElementaryStreamInfo *> ElementaryStreamInfoVector;
typedef ElementaryStreamInfoVector::iterator ElementaryStreamInfoIterator;
typedef ElementaryStreamInfoVector::const_iterator ElementaryStreamInfoConstIterator;

class ProgramMapTable : public LongCrcTable, public DescriptorContainer
{
	protected:
		unsigned reserved4				: 3;
		unsigned pcrPid					: 13;
		unsigned reserved5				: 4;
		unsigned programInfoLength			: 12;
		ElementaryStreamInfoVector esInfo;

	public:
		ProgramMapTable(const uint8_t * const buffer);
		~ProgramMapTable(void);

		static const enum TableId TID = TID_PMT;
		static const uint32_t TIMEOUT = 6000;

		uint16_t getPcrPid(void) const;
		const ElementaryStreamInfoVector *getEsInfo(void) const;

	friend class CaProgramMapTable;
};

typedef std::vector<ProgramMapTable *> ProgramMapTableVector;
typedef ProgramMapTableVector::iterator ProgramMapTableIterator;
typedef ProgramMapTableVector::const_iterator ProgramMapTableConstIterator;

#endif /* __dvb_table_pmt_h__ */
