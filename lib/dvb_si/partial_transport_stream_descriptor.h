/*
 * $Id: partial_transport_stream_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_partial_transport_stream_descriptor_h__
#define __dvb_descriptor_partial_transport_stream_descriptor_h__

#include "descriptor.h"

class PartialTransportStreamDescriptor : public Descriptor
{
	protected:
		unsigned reserved				: 2;
		unsigned peakRate				: 22;
		unsigned reserved2				: 2;
		unsigned minimumOverallSmootingRate		: 22;
		unsigned reserved3				: 2;
		unsigned maximumOverallSmoothingBuffer		: 14;

	public:
		PartialTransportStreamDescriptor(const uint8_t * const buffer);

		uint32_t getPeakRate(void) const;
		uint32_t getMinimumOverallSmoothingRate(void) const;
		uint16_t getMaximumOverallSmoothingBuffer(void) const;
};

#endif /* __dvb_descriptor_partial_transport_stream_descriptor_h__ */
