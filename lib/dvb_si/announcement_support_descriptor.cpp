/*
 * $Id: announcement_support_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/announcement_support_descriptor.h>

Announcement::Announcement(const uint8_t * const buffer)
{
	announcementType = (buffer[0] >> 4) & 0x0f;
	reserved = (buffer[0] >> 3) & 0x01;
	referenceType = buffer[0] & 0x07;

	if ((referenceType >= 0x01) && (referenceType <= 0x03)) {
		originalNetworkId = (buffer[1] << 8) | buffer[2];
		transportStreamId = (buffer[3] << 8) | buffer[4];
		serviceId = (buffer[5] << 8) | buffer[6];
		componentTag = buffer[7];
	}
}

uint8_t Announcement::getAnnouncementType(void) const
{
	return announcementType;
}

uint8_t Announcement::getReferenceType(void) const
{
	return referenceType;
}

uint16_t Announcement::getOriginalNetworkId(void) const
{
	return originalNetworkId;
}

uint16_t Announcement::getTransportStreamId(void) const
{
	return transportStreamId;
}

uint16_t Announcement::getServiceId(void) const
{
	return serviceId;
}

uint8_t Announcement::getComponentTag(void) const
{
	return componentTag;
}

AnnouncementSupportDescriptor::AnnouncementSupportDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	Announcement *a;

	announcementSupportIndicator = (buffer[2] << 8) | buffer[3];
	
	if (descriptorLength < 2)
		return;

	for (uint16_t i = 0; i < descriptorLength - 2; ++i) {
		a = new Announcement(&buffer[i + 4]);
		announcements.push_back(a);
		switch (a->getReferenceType()) {
		case 0x01:
		case 0x02:
		case 0x03:
			i += 7;
			break;
		default:
			break;
		}
	}
}

AnnouncementSupportDescriptor::~AnnouncementSupportDescriptor(void)
{
	for (AnnouncementIterator i = announcements.begin(); i != announcements.end(); ++i)
		delete *i;
}

uint16_t AnnouncementSupportDescriptor::getAnnouncementSupportIndicator(void) const
{
	return announcementSupportIndicator;
}

const AnnouncementVector *AnnouncementSupportDescriptor::getAnnouncements(void) const
{
	return &announcements;
}

