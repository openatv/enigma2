/*
 * $Id: stream_type.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_id_stream_type_h__
#define __dvb_id_stream_type_h__

enum StreamType {
	STT_RESERVED		= 0x00,
	STT_MPEG1_VIDEO		= 0x01,
	STT_MPEG2_VIDEO		= 0x02,
	STT_MPEG1_AUDIO		= 0x03,
	STT_MPEG2_AUDIO		= 0x04,
	STT_MPEG2_SECTIONS	= 0x05,
	STT_MPEG2_PES		= 0x06,
	STT_MHEG		= 0x07,
	STT_DSM_CC		= 0x08,
	STT_TREC_H_222_1	= 0x09,
	STT_13818_6_A		= 0x0A,
	STT_13818_6_B		= 0x0B,
	STT_13818_6_C		= 0x0C,
	STT_13818_6_D		= 0x0D,
	STT_AUXILIARY		= 0x0E,
	STT_ADTS_AUDIO		= 0x0F,
	STT_MPEG4_VIDEO		= 0x10,
	STT_MPEG4_AUDIO		= 0x11,
	STT_MPEG4_PES		= 0x12,
	STT_MPEG4_SECTIONS	= 0x13,
	STT_SYNC_DOWNLOAD_PROT	= 0x14
	/* 0x15 - 0x7F: ITU-T Rec. H.222.0 | ISO/IEC 13818-1 Reserved */
	/* 0x80 - 0xFF: User Private */
};

#endif /* __dvb_id_stream_type_h__ */
