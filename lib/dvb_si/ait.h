/*
 * $Id: ait.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_table_ait_h__
#define __dvb_table_ait_h__

#include <lib/dvb_si/container.h>
#include "long_crc_table.h"

class ApplicationIdentifier
{
	protected:
		unsigned organisationId				: 32;
		unsigned applicationId				: 16;

	public:
		ApplicationIdentifier(const uint8_t * const buffer);

		uint32_t getOrganisationId(void) const;
		uint16_t getApplicationId(void) const;
};

class ApplicationInformation : public DescriptorContainer
{
	protected:
		ApplicationIdentifier *applicationIdentifier;
		unsigned applicationControlCode			: 8;
		unsigned reserved				: 4;
		unsigned applicationDescriptorsLoopLength	: 12;

	public:
		ApplicationInformation(const uint8_t * const buffer);
		~ApplicationInformation(void);

		const ApplicationIdentifier *getApplicationIdentifier(void) const;
		uint8_t getApplicationControlCode(void) const;

	friend class ApplicationInformationTable;
};

typedef std::vector<ApplicationInformation *> ApplicationInformationVector;
typedef ApplicationInformationVector::iterator ApplicationInformationIterator;
typedef ApplicationInformationVector::const_iterator ApplicationInformationConstIterator;

class ApplicationInformationTable : public LongCrcTable, public DescriptorContainer
{
	protected:
		unsigned reserved4				: 4;
		unsigned commonDescriptorsLength		: 12;
		unsigned reserved5				: 4;
		unsigned applicationLoopLength			: 12;
		ApplicationInformationVector applicationInformation;

	public:
		ApplicationInformationTable(const uint8_t * const buffer);
		~ApplicationInformationTable(void);

		static const enum TableId TID = TID_AIT;
		static const uint32_t TIMEOUT = 12000;

		const ApplicationInformationVector *getApplicationInformation(void) const;
};

typedef std::vector<ApplicationInformationTable *> ApplicationInformationTableVector;
typedef ApplicationInformationTableVector::iterator ApplicationInformationTableIterator;
typedef ApplicationInformationTableVector::const_iterator ApplicationInformationTableConstIterator;

#endif /* __dvb_table_ait_h__ */
