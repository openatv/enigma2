/*
 * $Id: capmt.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_table_capmt_h__
#define __dvb_table_capmt_h__

#include <lib/dvb_si/ca_descriptor.h>
#include "pmt.h"

class CaLengthField
{
	protected:
		unsigned sizeIndicator				: 1;
		unsigned lengthValue				: 7;
		unsigned lengthFieldSize			: 7;
		std::vector<uint8_t> lengthValueByte;

	public:
		CaLengthField(const uint64_t length);
};

class CaElementaryStreamInfo
{
	protected:
		unsigned streamType				: 8;
		unsigned reserved1				: 3;
		unsigned elementaryPid				: 13;
		unsigned reserved2				: 4;
		unsigned esInfoLength				: 12;
		unsigned caPmtCmdId				: 8;
		CaDescriptorVector descriptors;

	public:
		CaElementaryStreamInfo(const ElementaryStreamInfo * const info, const uint8_t cmdId);
		~CaElementaryStreamInfo(void);

		uint16_t getLength(void) const;
};

typedef std::vector<CaElementaryStreamInfo *> CaElementaryStreamInfoVector;
typedef CaElementaryStreamInfoVector::iterator CaElementaryStreamInfoIterator;
typedef CaElementaryStreamInfoVector::const_iterator CaElementaryStreamInfoConstIterator;

class CaProgramMapTable
{
	protected:
		unsigned caPmtTag				: 24;
		CaLengthField *lengthField;
		unsigned caPmtListManagement			: 8;
		unsigned programNumber				: 16;
		unsigned reserved1				: 2;
		unsigned versionNumber				: 5;
		unsigned currentNextIndicator			: 1;
		unsigned reserved2				: 4;
		unsigned programInfoLength			: 12;
		unsigned caPmtCmdId				: 8;
		CaDescriptorVector descriptors;
		CaElementaryStreamInfoVector esInfo;

	public:
		CaProgramMapTable(const ProgramMapTable * const pmt, const uint8_t listManagement, const uint8_t cmdId);
		~CaProgramMapTable(void);
};

typedef std::vector<CaProgramMapTable *> CaProgramMapTableVector;
typedef CaProgramMapTableVector::iterator CaProgramMapTableIterator;
typedef CaProgramMapTableVector::const_iterator CaProgramMapTableConstIterator;

#endif /* __dvb_table_capmt_h__ */
