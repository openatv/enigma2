/*
 * $Id: capmt.cpp,v 1.1 2003-10-17 15:36:37 tmbinc Exp $
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

#include <lib/dvb_si/descriptor_tag.h>
#include <lib/dvb_si/capmt.h>

CaLengthField::CaLengthField(const uint64_t length)
{
	if (length < 0x80) {
		sizeIndicator = 0;
		lengthValue = length;
	}

	else {
		uint64_t mask = 0xFF;

		sizeIndicator = 1;
		lengthFieldSize = 1;

		while ((length & mask) != length) {
			lengthFieldSize++;
			mask = ((uint64_t)(mask << 8)) | ((uint64_t)0xFFULL);
		}

		for (uint8_t i = lengthFieldSize; i > 0; i--)
			lengthValueByte.push_back((length >> ((i - 1) << 3)) & 0xFF);
	}
}

CaElementaryStreamInfo::CaElementaryStreamInfo(const ElementaryStreamInfo * const info, const uint8_t cmdId)
{
	streamType = info->streamType;
	reserved1 = info->reserved1;
	elementaryPid = info->elementaryPid;
	reserved2 = info->reserved2;
	esInfoLength = 0;

	for (DescriptorConstIterator i = info->getDescriptors()->begin(); i != info->getDescriptors()->end(); ++i)
		if ((*i)->getTag() == CA_DESCRIPTOR) {
			descriptors.push_back(new CaDescriptor(*(CaDescriptor *)*i));
			esInfoLength += (*i)->getLength() + 2;
		}

	if (esInfoLength) {
		caPmtCmdId = cmdId;
		esInfoLength++;
	}
}

CaElementaryStreamInfo::~CaElementaryStreamInfo(void)
{
	for (CaDescriptorIterator i = descriptors.begin(); i != descriptors.end(); ++i)
		delete *i;
}

uint16_t CaElementaryStreamInfo::getLength(void) const
{
	return esInfoLength + 5;
}

CaProgramMapTable::CaProgramMapTable(const ProgramMapTable * const pmt, const uint8_t listManagement, const uint8_t cmdId)
{
	uint64_t length = 6;

	caPmtTag = 0x9F80C3;
	caPmtListManagement = listManagement;

	programNumber = pmt->tableIdExtension;
	reserved1 = pmt->reserved3;
	versionNumber = pmt->versionNumber;
	currentNextIndicator = pmt->currentNextIndicator;
	reserved2 = pmt->reserved5;
	programInfoLength = 0;

	for (DescriptorConstIterator i = pmt->getDescriptors()->begin(); i != pmt->getDescriptors()->end(); ++i)
		if ((*i)->getTag() == CA_DESCRIPTOR) {
			descriptors.push_back(new CaDescriptor(*(CaDescriptor *)*i));
			programInfoLength += (*i)->getLength() + 2;
		}

	if (programInfoLength) {
		caPmtCmdId = cmdId;
		programInfoLength++;
		length += programInfoLength;
	}

	for (ElementaryStreamInfoConstIterator i = pmt->esInfo.begin(); i != pmt->esInfo.end(); ++i) {
		CaElementaryStreamInfo *info = new CaElementaryStreamInfo(*i, cmdId);
		esInfo.push_back(info);
		length += info->getLength();
	}

	lengthField = new CaLengthField(length);
}

CaProgramMapTable::~CaProgramMapTable(void)
{
	for (CaDescriptorIterator i = descriptors.begin(); i != descriptors.end(); ++i)
		delete *i;

	for (CaElementaryStreamInfoIterator i = esInfo.begin(); i != esInfo.end(); ++i)
		delete *i;

	delete lengthField;
}

