/*
 * $Id: component_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/component_descriptor.h>

ComponentDescriptor::ComponentDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	reserved = (buffer[2] >> 4) & 0x0f;
	streamContent = buffer[2] & 0x0f;
	componentType = buffer[3];
	componentTag = buffer[4];
	iso639LanguageCode.assign((char *) &buffer[5], 3);
	if (descriptorLength < 6)
		return;
	text.assign((char *) &buffer[8], descriptorLength - 6);
}

uint8_t ComponentDescriptor::getStreamContent(void) const
{
	return streamContent;
}

uint8_t ComponentDescriptor::getComponentType(void) const
{
	return componentType;
}

uint8_t ComponentDescriptor::getComponentTag(void) const
{
	return componentTag;
}

std::string ComponentDescriptor::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

std::string ComponentDescriptor::getText(void) const
{
	return text;
}

