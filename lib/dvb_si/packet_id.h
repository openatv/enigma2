/*
 * $Id: packet_id.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_id_packet_id_h__
#define __dvb_id_packet_id_h__

enum PacketId {
	/* ETSI EN 300 468 V1.5.1 (2003-01) */
	PID_PAT		= 0x0000,
	PID_CAT		= 0x0001,
	PID_TSDT	= 0x0002,
	PID_NIT		= 0x0010,
	PID_BAT		= 0x0011,
	PID_SDT		= 0x0011,
	PID_EIT		= 0x0012,
	PID_RST		= 0x0013,
	PID_TDT		= 0x0014,
	PID_TOT		= 0x0014,
	PID_NS		= 0x0015,	/* network synchronization */
	PID_IS		= 0x001C,	/* inband signaling (SIS-12) */
	PID_M		= 0x001D,	/* measurement (SIS-10) */
	PID_DIT		= 0x001E,
	PID_SIT		= 0x001F,
	PID_RESERVED	= 0x1FFF
};

#endif /* __dvb_id_packet_id_h__ */
