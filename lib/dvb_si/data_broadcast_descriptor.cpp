/*
 * $Id: data_broadcast_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/data_broadcast_descriptor.h>

DataBroadcastDescriptor::DataBroadcastDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	dataBroadcastId = (buffer[2] << 8) | buffer[3];
	componentTag = buffer[3];
	selectorLength = buffer[4];

	for (uint16_t i = 0; i < selectorLength; ++i)
		selectorBytes.push_back(buffer[i + 5]);

	iso639LanguageCode.assign((char *)&buffer[selectorLength + 5], 3);
	textLength = buffer[selectorLength + 8];
	text.assign((char *)&buffer[selectorLength + 9], textLength);
}

uint16_t DataBroadcastDescriptor::getDataBroadcastId(void) const
{
	return dataBroadcastId;
}

uint8_t DataBroadcastDescriptor::getComponentTag(void) const
{
	return componentTag;
}

const selectorByteVector *DataBroadcastDescriptor::getSelectorBytes(void) const
{
	return &selectorBytes;
}

std::string DataBroadcastDescriptor::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

std::string DataBroadcastDescriptor::getText(void) const
{
	return text;
}

