/*
 * $Id: dsng_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_dsng_descriptor_h__
#define __dvb_descriptor_dsng_descriptor_h__

#include "descriptor.h"

typedef std::vector<uint8_t> ByteVector;
typedef ByteVector::iterator ByteIterator;
typedef ByteVector::const_iterator ByteConstIterator;

class DsngDescriptor : public Descriptor
{
	protected:
		ByteVector bytes;

	public:
		DsngDescriptor(const uint8_t * const buffer);

		const ByteVector *getBytes(void) const;
};

#endif /* __dvb_descriptor_dsng_descriptor_h__ */
