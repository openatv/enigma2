/*
 * $Id: extended_event_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/extended_event_descriptor.h>

ExtendedEvent::ExtendedEvent(const uint8_t * const buffer)
{
	itemDescriptionLength = buffer[0];
	itemDescription.assign((char *)&buffer[1], itemDescriptionLength);
	itemLength = buffer[itemDescriptionLength + 1];
	item.assign((char *)&buffer[itemDescriptionLength + 2], itemLength);
}

std::string ExtendedEvent::getItemDescription(void) const
{
	return itemDescription;
}

std::string ExtendedEvent::getItem(void) const
{
	return item;
}

ExtendedEventDescriptor::ExtendedEventDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	descriptorNumber = (buffer[2] >> 4) & 0x0f;
	lastDescriptorNumber = buffer[2] & 0x0f;
	iso639LanguageCode.assign((char *)&buffer[3], 3);
	lengthOfItems = buffer[6];

	ExtendedEvent *e;

	for (uint16_t i = 0; i < lengthOfItems; i += e->itemDescriptionLength + e->itemLength + 2) {
		e = new ExtendedEvent(&buffer[i + 7]);
		items.push_back(e);
	}

	textLength = buffer[lengthOfItems + 7];
	text.assign((char *)&buffer[lengthOfItems + 8], textLength);
}

ExtendedEventDescriptor::~ExtendedEventDescriptor(void)
{
	for (ExtendedEventIterator i = items.begin(); i != items.end(); ++i)
		delete *i;
}

uint8_t ExtendedEventDescriptor::getDescriptorNumber(void) const
{
	return descriptorNumber;
}

uint8_t ExtendedEventDescriptor::getLastDescriptorNumber(void) const
{
	return lastDescriptorNumber;
}

std::string ExtendedEventDescriptor::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

const ExtendedEventVector *ExtendedEventDescriptor::getItems(void) const
{
	return &items;
}

std::string ExtendedEventDescriptor::getText(void) const
{
	return text;
}

