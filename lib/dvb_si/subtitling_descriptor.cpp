/*
 * $Id: subtitling_descriptor.cpp,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#include <lib/dvb_si/subtitling_descriptor.h>

Subtitling::Subtitling(const uint8_t * const buffer)
{
	iso639LanguageCode.assign((char *)&buffer[0], 3);
	subtitlingType = buffer[3];
	compositionPageId = (buffer[4] << 8) | buffer[5];
	ancillaryPageId = (buffer[6] << 8) | buffer[7];
}

std::string Subtitling::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

uint8_t Subtitling::getSubtitlingType(void) const
{
	return subtitlingType;
}

uint16_t Subtitling::getCompositionPageId(void) const
{
	return compositionPageId;
}

uint16_t Subtitling::getAncillaryPageId(void) const
{
	return ancillaryPageId;
}

SubtitlingDescriptor::SubtitlingDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	for (uint16_t i = 0; i < descriptorLength; i += 8)
		subtitlings.push_back(new Subtitling(&buffer[i + 2]));
}

SubtitlingDescriptor::~SubtitlingDescriptor(void)
{
	for (SubtitlingIterator i = subtitlings.begin(); i != subtitlings.end(); ++i)
		delete *i;
}

const SubtitlingVector *SubtitlingDescriptor::getSubtitlings(void) const
{
	return &subtitlings;
}

