/*
 * $Id: ac3_descriptor.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/ac3_descriptor.h>

Ac3Descriptor::Ac3Descriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	if (buffer[1] >= 1)
	{
		ac3TypeFlag = (buffer[2] >> 7) & 0x01;
		bsidFlag = (buffer[2] >> 6) & 0x01;
		mainidFlag = (buffer[2] >> 5) & 0x01;
		asvcFlag = (buffer[2] >> 4) & 0x01;
		reserved = buffer[2] & 0x0F;
		if (ac3TypeFlag == 1)
			ac3Type = buffer[3];

		if (bsidFlag == 1)
			bsid = buffer[ac3TypeFlag + 3];

		if (mainidFlag == 1)
			mainid = buffer[ac3TypeFlag + mainidFlag + 3];

		if (asvcFlag == 1)
			avsc = buffer[ac3TypeFlag + bsidFlag + mainidFlag + 3];
		
		if (descriptorLength > ac3TypeFlag + bsidFlag + mainidFlag + asvcFlag)
			for (uint16_t i = 0; i < descriptorLength - ac3TypeFlag - bsidFlag - mainidFlag - asvcFlag - 1; ++i)
				additionalInfo.push_back(buffer[ac3TypeFlag + bsidFlag + mainidFlag + asvcFlag + i + 3]);
	} else
	{
		ac3TypeFlag = 0;
		bsidFlag = 0;
		mainidFlag = 0;
		asvcFlag = 0;
		reserved = 0;
	}
}

uint8_t Ac3Descriptor::getAc3TypeFlag(void) const
{
	return ac3TypeFlag;
}

uint8_t Ac3Descriptor::getBsidFlag(void) const
{
	return bsidFlag;
}

uint8_t Ac3Descriptor::getMainidFlag(void) const
{
	return mainidFlag;
}

uint8_t Ac3Descriptor::getAsvcFlag(void) const
{
	return asvcFlag;
}

uint8_t Ac3Descriptor::getAc3Type(void) const
{
	return ac3Type;
}

uint8_t Ac3Descriptor::getBsid(void) const
{
	return bsid;
}

uint8_t Ac3Descriptor::getMainid(void) const
{
	return mainid;
}

uint8_t Ac3Descriptor::getAvsc(void) const
{
	return avsc;
}

const AdditionalInfoVector *Ac3Descriptor::getAdditionalInfo(void) const
{
	return &additionalInfo;
}

