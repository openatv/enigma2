/*
 * $Id: service_type.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_id_service_type_h__
#define __dvb_id_service_type_h__

enum ServiceType {
	/* 0x00 - 0x10: ETSI EN 300 468 V1.5.1 (2003-01) */
	ST_RESERVED			= 0x00,
	ST_DIGITAL_TELEVISION_SERVICE	= 0x01,
	ST_DIGITAL_RADIO_SOUND_SERVICE	= 0x02,
	ST_TELETEXT_SERVICE		= 0x03,
	ST_NVOD_REFERENCE_SERVICE	= 0x04,
	ST_NVOD_TIME_SHIFTED_SERVICE	= 0x05,
	ST_MOSAIC_SERVICE		= 0x06,
	ST_PAL_CODED_SIGNAL		= 0x07,
	ST_SECAM_CODED_SIGNAL		= 0x08,
	ST_D_D2_MAC			= 0x09,
	ST_FM_RADIO			= 0x0A,
	ST_NTSC_CODED_SIGNAL		= 0x0B,
	ST_DATA_BROADCAST_SERVICE	= 0x0C,
	ST_COMMON_INTERFACE_RESERVED	= 0x0D,
	ST_RCS_MAP			= 0x0E,
	ST_RCS_FLS			= 0x0F,
	ST_DVB_MHP_SERVICE		= 0x10,
	/* 0x11 - 0x7F: reserved for future use */
	ST_MULTIFEED			= 0x69
	/* 0x80 - 0xFE: user defined */
	/* 0xFF: reserved for future use */
};

#endif /* __dvb_id_service_type_h__ */
