/*
 * $Id: target_background_grid_descriptor.cpp,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#include <lib/dvb_si/target_background_grid_descriptor.h>

TargetBackgroundGridDescriptor::TargetBackgroundGridDescriptor(const uint8_t * const buffer) : Descriptor(buffer)
{
	horizontalSize = ((buffer[2] << 8) | (buffer[3] & 0xF3)) >> 2;
	verticalSize = (((buffer[3] & 0x03) << 16) | (buffer[4] << 8) | (buffer[5] & 0xF0)) >> 4;
	aspectRatioInformation = buffer[5] & 0x0F;
}

uint16_t TargetBackgroundGridDescriptor::getHorizontalSize(void) const
{
	return horizontalSize;
}

uint16_t TargetBackgroundGridDescriptor::getVerticalSize(void) const
{
	return verticalSize;
}

uint8_t TargetBackgroundGridDescriptor::getAspectRatioInformation(void) const
{
	return aspectRatioInformation;
}

