/*
 * $Id: vbi_teletext_descriptor.cpp,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#include <lib/dvb_si/vbi_teletext_descriptor.h>

VbiTeletext::VbiTeletext(const uint8_t * const buffer)
{
	iso639LanguageCode.assign((char *)&buffer[0], 3);
	teletextType = (buffer[3] >> 3) & 0x1F;
	teletextMagazineNumber = buffer[3] & 0x07;
	teletextPageNumber = buffer[4];
}

std::string VbiTeletext::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

uint8_t VbiTeletext::getTeletextType(void) const
{
	return teletextType;
}

uint8_t VbiTeletext::getTeletextMagazineNumber(void) const
{
	return teletextMagazineNumber;
}

uint8_t VbiTeletext::getTeletextPageNumber(void) const
{
	return teletextPageNumber;
}

VbiTeletextDescriptor::VbiTeletextDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	for (uint16_t i = 0; i < descriptorLength; i += 5)
		vbiTeletexts.push_back(new VbiTeletext(&buffer[i + 2]));
}

VbiTeletextDescriptor::~VbiTeletextDescriptor(void)
{
	for (VbiTeletextIterator i = vbiTeletexts.begin(); i != vbiTeletexts.end(); ++i)
		delete *i;
}

const VbiTeletextVector *VbiTeletextDescriptor::getVbiTeletexts(void) const
{
	return &vbiTeletexts;
}

