/*
 * $Id: announcement_support_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_announcement_support_descriptor_h__
#define __dvb_descriptor_announcement_support_descriptor_h__

#include "descriptor.h"

class Announcement
{
	protected:
		unsigned announcementType			: 4;
		unsigned reserved				: 1;
		unsigned referenceType				: 3;
		unsigned originalNetworkId			: 16;
		unsigned transportStreamId			: 16;
		unsigned serviceId				: 16;
		unsigned componentTag				: 8;

	public:
		Announcement(const uint8_t * const buffer);

		uint8_t getAnnouncementType(void) const;
		uint8_t getReferenceType(void) const;
		uint16_t getOriginalNetworkId(void) const;
		uint16_t getTransportStreamId(void) const;
		uint16_t getServiceId(void) const;
		uint8_t getComponentTag(void) const;
};

typedef std::vector<Announcement *> AnnouncementVector;
typedef AnnouncementVector::iterator AnnouncementIterator;
typedef AnnouncementVector::const_iterator AnnouncementConstIterator;

class AnnouncementSupportDescriptor : public Descriptor
{
	protected:
		unsigned announcementSupportIndicator		: 16;
		AnnouncementVector announcements;

	public:
		AnnouncementSupportDescriptor(const uint8_t * const buffer);
		~AnnouncementSupportDescriptor(void);

		uint16_t getAnnouncementSupportIndicator(void) const;
		const AnnouncementVector *getAnnouncements(void) const;
};

#endif /* __dvb_descriptor_announcement_support_descriptor_h__ */
