/*
 * $Id: iso639_language_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/iso639_language_descriptor.h>

Iso639Language::Iso639Language(const uint8_t * const buffer)
{
	iso639LanguageCode.assign((char *)&buffer[0], 3);
	audioType = buffer[3];
}

std::string Iso639Language::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

uint8_t Iso639Language::getAudioType(void) const
{
	return audioType;
}

Iso639LanguageDescriptor::Iso639LanguageDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	for (uint16_t i = 0; i < descriptorLength; i += 4)
		iso639Languages.push_back(new Iso639Language(&buffer[i + 2]));
}

Iso639LanguageDescriptor::~Iso639LanguageDescriptor(void)
{
	for (Iso639LanguageIterator i = iso639Languages.begin(); i != iso639Languages.end(); ++i)
		delete *i;
}

const Iso639LanguageVector *Iso639LanguageDescriptor::getIso639Languages(void) const
{
	return &iso639Languages;
}

