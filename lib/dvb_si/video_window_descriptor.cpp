/*
 * $Id: video_window_descriptor.cpp,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#include <lib/dvb_si/video_window_descriptor.h>

VideoWindowDescriptor::VideoWindowDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	horizontalOffset = ((buffer[2] << 8) | (buffer[3] & 0xF3)) >> 2;
	verticalOffset = (((buffer[3] & 0x03) << 16) | (buffer[4] << 8) | (buffer[5] & 0xF0)) >> 4;
	windowPriority = buffer[5] & 0x0F;
}

uint16_t VideoWindowDescriptor::getHorizontalOffset(void) const
{
	return horizontalOffset;
}

uint16_t VideoWindowDescriptor::getVerticalOffset(void) const
{
	return verticalOffset;
}

uint8_t VideoWindowDescriptor::getWindowPriority(void) const
{
	return windowPriority;
}

