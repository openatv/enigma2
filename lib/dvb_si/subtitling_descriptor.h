/*
 * $Id: subtitling_descriptor.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_descriptor_subtitling_descriptor_h__
#define __dvb_descriptor_subtitling_descriptor_h__

#include "descriptor.h"

class Subtitling
{
	protected:
		std::string iso639LanguageCode;
		unsigned subtitlingType				: 8;
		unsigned compositionPageId			: 16;
		unsigned ancillaryPageId			: 16;

	public:
		Subtitling(const uint8_t * const buffer);

		std::string getIso639LanguageCode(void) const;
		uint8_t getSubtitlingType(void) const;
		uint16_t getCompositionPageId(void) const;
		uint16_t getAncillaryPageId(void) const;
};

typedef std::vector<Subtitling *> SubtitlingVector;
typedef SubtitlingVector::iterator SubtitlingIterator;
typedef SubtitlingVector::const_iterator SubtitlingConstIterator;

class SubtitlingDescriptor : public Descriptor
{
	protected:
		SubtitlingVector subtitlings;

	public:
		SubtitlingDescriptor(const uint8_t * const buffer);
		~SubtitlingDescriptor(void);

		const SubtitlingVector *getSubtitlings(void) const;
};

#endif /* __dvb_descriptor_subtitling_descriptor_h__ */
