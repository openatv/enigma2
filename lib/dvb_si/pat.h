/*
 * $Id: pat.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_table_pat_h__
#define __dvb_table_pat_h__

#include "long_crc_table.h"

class NetworkAssociation
{
	protected:
		unsigned programNumber				: 16;
		unsigned reserved				: 3;
		unsigned networkPid				: 13;

	public:
		NetworkAssociation(const uint8_t * buffer);

		uint16_t getNetworkPid(void) const;
};

typedef std::vector<NetworkAssociation *> NetworkAssociationVector;
typedef NetworkAssociationVector::iterator NetworkAssociationIterator;
typedef NetworkAssociationVector::const_iterator NetworkAssociationConstIterator;

class ProgramAssociation
{
	protected:
		unsigned programNumber				: 16;
		unsigned reserved				: 3;
		unsigned programMapPid				: 13;

	public:
		ProgramAssociation(const uint8_t * buffer);

		uint16_t getProgramNumber(void) const;
		uint16_t getProgramMapPid(void) const;
};

typedef std::vector<ProgramAssociation *> ProgramAssociationVector;
typedef ProgramAssociationVector::iterator ProgramAssociationIterator;
typedef ProgramAssociationVector::const_iterator ProgramAssociationConstIterator;

class ProgramAssociationTable : public LongCrcTable
{
	protected:
		NetworkAssociationVector networks;
		ProgramAssociationVector programs;

	public:
		ProgramAssociationTable(const uint8_t * const buffer);
		~ProgramAssociationTable(void);

		static const enum PacketId PID = PID_PAT;
		static const enum TableId TID = TID_PAT;
		static const uint32_t TIMEOUT = 1200;

		const NetworkAssociationVector *getNetworks(void) const;
		const ProgramAssociationVector *getPrograms(void) const;
};

typedef std::vector<ProgramAssociationTable *> ProgramAssociationTableVector;
typedef ProgramAssociationTableVector::iterator ProgramAssociationTableIterator;
typedef ProgramAssociationTableVector::const_iterator ProgramAssociationTableConstIterator;

#endif /* __dvb_table_pat_h__ */
