/*
 * $Id: ancillary_data_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/ancillary_data_descriptor.h>

AncillaryDataDescriptor::AncillaryDataDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	ancillaryDataIdentifier = buffer[2];
}

uint8_t AncillaryDataDescriptor::getAncillaryDataIdentifier(void) const
{
	return ancillaryDataIdentifier;
}

