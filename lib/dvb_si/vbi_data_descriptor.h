/*
 * $Id: vbi_data_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_vbi_data_descriptor_h__
#define __dvb_descriptor_vbi_data_descriptor_h__

#include "descriptor.h"

class VbiDataLine
{
	protected:
		unsigned reserved				: 2;
		unsigned fieldParity				: 1;
		unsigned lineOffset				: 5;

	public:
		VbiDataLine(const uint8_t * const buffer);

		uint8_t getFieldParity(void) const;
		uint8_t getLineOffset(void) const;
};

typedef std::vector<VbiDataLine *> VbiDataLineVector;
typedef VbiDataLineVector::iterator VbiDataLineIterator;
typedef VbiDataLineVector::const_iterator VbiDataLineConstIterator;

class VbiDataService
{
	protected:
		unsigned dataServiceId				: 8;
		unsigned dataServiceDescriptorLength		: 8;
		VbiDataLineVector vbiDataLines;
		std::vector<uint8_t> reserved;

	public:
		VbiDataService(const uint8_t * const buffer);
		~VbiDataService(void);

		uint8_t getDataServiceId(void) const;
		const VbiDataLineVector *getVbiDataLines(void) const;
};

typedef std::vector<VbiDataService *> VbiDataServiceVector;
typedef VbiDataServiceVector::iterator VbiDataServiceIterator;
typedef VbiDataServiceVector::const_iterator VbiDataServiceConstIterator;

class VbiDataDescriptor : public Descriptor
{
	protected:
		VbiDataServiceVector vbiDataServices;

	public:
		VbiDataDescriptor(const uint8_t * const buffer);
		~VbiDataDescriptor(void);

		const VbiDataServiceVector *getVbiDataServices(void) const;
};

#endif /* __dvb_descriptor_vbi_data_descriptor_h__ */
