/*
 * $Id: service_list_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
 *
 * (C) 2003 Andreas Oberritter <obi@saftware.de>
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

#include <lib/dvb_si/service_list_descriptor.h>

ServiceListItem::ServiceListItem(const uint8_t * const buffer)
{
	serviceId = (buffer[0] << 8) | buffer[1];
	serviceType = buffer[2];
}

uint16_t ServiceListItem::getServiceId(void) const
{
	return serviceId;
}

uint8_t ServiceListItem::getServiceType(void) const
{
	return serviceType;
}

ServiceListDescriptor::ServiceListDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	for (uint16_t i = 0; i < descriptorLength; i += 3)
		serviceList.push_back(new ServiceListItem(&buffer[i + 2]));
}

ServiceListDescriptor::~ServiceListDescriptor(void)
{
	for (ServiceListItemIterator i = serviceList.begin(); i != serviceList.end(); ++i)
		delete *i;
}

const ServiceListItemVector *ServiceListDescriptor::getServiceList(void) const
{
	return &serviceList;
}

