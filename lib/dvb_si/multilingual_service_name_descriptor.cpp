/*
 * $Id: multilingual_service_name_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/multilingual_service_name_descriptor.h>

MultilingualServiceName::MultilingualServiceName(const uint8_t * const buffer)
{
	iso639LanguageCode.assign((char *)&buffer[0], 3);
	serviceProviderNameLength = buffer[3];
	serviceProviderName.assign((char *)&buffer[4], serviceProviderNameLength);
	serviceNameLength = buffer[serviceProviderNameLength + 4];
	serviceName.assign((char *)&buffer[serviceProviderNameLength + 5], serviceNameLength);
}

std::string MultilingualServiceName::getIso639LanguageCode(void) const
{
	return iso639LanguageCode;
}

std::string MultilingualServiceName::getServiceProviderName(void) const
{
	return serviceProviderName;
}

std::string MultilingualServiceName::getServiceName(void) const
{
	return serviceName;
}

MultilingualServiceNameDescriptor::MultilingualServiceNameDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	MultilingualServiceName *name;

	for (uint16_t i = 0; i < descriptorLength; i += name->serviceProviderNameLength + name->serviceNameLength + 5) {
		name = new MultilingualServiceName(&buffer[i + 2]);
		multilingualServiceNames.push_back(name);
	}
}

MultilingualServiceNameDescriptor::~MultilingualServiceNameDescriptor(void)
{
	for (MultilingualServiceNameIterator i = multilingualServiceNames.begin(); i != multilingualServiceNames.end(); ++i)
		delete *i;
}

const MultilingualServiceNameVector *MultilingualServiceNameDescriptor::getMultilingualServiceNames(void) const
{
	return &multilingualServiceNames;
}

