/*
 * $Id: video_stream_descriptor.cpp,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#include <lib/dvb_si/video_stream_descriptor.h>

VideoStreamDescriptor::VideoStreamDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	multipleFrameRateFlag = (buffer[2] >> 7) & 0x01;
	frameRateCode = (buffer[2] >> 3) & 0x0F;
	mpeg1OnlyFlag = (buffer[2] >> 2) & 0x01;
	constrainedParameterFlag = (buffer[2] >> 1) & 0x01;

	if (!mpeg1OnlyFlag) {
		profileAndLevelIndication = buffer[3];
		chromaFormat = (buffer[4] >> 6) & 0x03;
		frameRateExtensionFlag = (buffer[4] >> 5) & 0x01;
		reserved = buffer[4] & 0x1F;
	}
}

uint8_t VideoStreamDescriptor::getMultipleFrameRateFlag(void) const
{
	return multipleFrameRateFlag;
}

uint8_t VideoStreamDescriptor::getFrameRateCode(void) const
{
	return frameRateCode;
}

uint8_t VideoStreamDescriptor::getMpeg1OnlyFlag(void) const
{
	return mpeg1OnlyFlag;
}

uint8_t VideoStreamDescriptor::getConstrainedParameterFlag(void) const
{
	return constrainedParameterFlag;
}

uint8_t VideoStreamDescriptor::getProfileAndLevelIndication(void) const
{
	return profileAndLevelIndication;
}

uint8_t VideoStreamDescriptor::getChromaFormat(void) const
{
	return chromaFormat;
}

uint8_t VideoStreamDescriptor::getFrameRateExtensionFlag(void) const
{
	return frameRateExtensionFlag;
}

