/*
 * $Id: service_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/service_descriptor.h>

ServiceDescriptor::ServiceDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	serviceType = buffer[2];
	serviceProviderNameLength = buffer[3];
	serviceProviderName.assign((char *)&buffer[4], serviceProviderNameLength);
	serviceNameLength = buffer[serviceProviderNameLength + 4];
	serviceName.assign((char *)&buffer[serviceProviderNameLength + 5], serviceNameLength);
}

uint8_t ServiceDescriptor::getServiceType(void) const
{
	return serviceType;
}

std::string ServiceDescriptor::getServiceProviderName(void) const
{
	return serviceProviderName;
}

std::string ServiceDescriptor::getServiceName(void) const
{
	return serviceName;
}

