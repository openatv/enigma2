/*
 * $Id: table_id.h,v 1.1 2003-10-17 15:36:38 tmbinc Exp $
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

#ifndef __dvb_id_table_id_h__
#define __dvb_id_table_id_h__

enum TableId {
	/* ISO/IEC 13818-1, ITU T-REC H.222.0 */
	TID_PAT			= 0x00,	/* program_association_section */
	TID_CAT			= 0x01,	/* conditional_access_section */
	TID_PMT			= 0x02,	/* TS_program_map_section */
	TID_TSDT		= 0x03,	/* TS_description_section */
	TID_SDT			= 0x04,	/* ISO_IEC_14496_scene_description_section */
	TID_ODT			= 0x05,	/* ISO_IEC_14496_object_descriptor_section */

	/* 0x06 - 0x09: ITU-T Rec. H.222.0 | ISO/IEC 13818-1 reserved */

	/* 0x0A - 0x0D: ISO/IEC 13818-6 */
	TID_DSMCC_MULTIPROTOCOL	= 0x0A,	/* Multiprotocol */
	TID_DSMCC_MSG_HEADER	= 0x0B,	/* DSM-CC Messages Header (U-N) */
	TID_DSMCC_DESCR_LOOP	= 0x0C,	/* DSM-CC Descriptors Loop */
	TID_DSMCC_TBD		= 0x0D,	/* TBD */

	/* 0x0E - 0x37: ITU-T Rec. H.222.0 | ISO/IEC 13818-1 reserved */

	/* 0x38 - 0x3F: Defined in ISO/IEC 13818-6 */
	TID_DSMCC_DL_MESSAGE	= 0x3B,	/* DSM-CC Download Message */
	TID_DSMCC_DL_DATA	= 0x3C,	/* DSM-CC Download Data */
	TID_DSMCC_DL_EVENT	= 0x3D,	/* DSM-CC Download Event */

	/* 0x40 - 0x7F: ETSI EN 300 468 V1.5.1 (2003-01) */
	TID_NIT_ACTUAL		= 0x40,	/* network_information_section - actual_network */
	TID_NIT_OTHER		= 0x41,	/* network_information_section - other_network */
	TID_SDT_ACTUAL		= 0x42,	/* service_description_section - actual_transport_stream */
	TID_SDT_OTHER		= 0x46,	/* service_description_section - other_transport_stream */
	TID_BAT			= 0x4A,	/* bouquet_association_section */
	TID_EIT_ACTUAL		= 0x4E,	/* event_information_section - actual_transport_stream, present/following */
	TID_EIT_OTHER		= 0x4F,	/* event_information_section - other_transport_stream, present/following */
	TID_EIT_ACTUAL_SCHED_0	= 0x50,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_1	= 0x51,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_2	= 0x52,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_3	= 0x53,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_4	= 0x54,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_5	= 0x55,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_6	= 0x56,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_7	= 0x57,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_8	= 0x58,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_9	= 0x59,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_A	= 0x5A,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_B	= 0x5B,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_C	= 0x5C,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_D	= 0x5D,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_E	= 0x5E,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_ACTUAL_SCHED_F	= 0x5F,	/* event_information_section - actual_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_0	= 0x60,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_1	= 0x61,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_2	= 0x62,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_3	= 0x63,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_4	= 0x64,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_5	= 0x65,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_6	= 0x66,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_7	= 0x67,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_8	= 0x68,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_9	= 0x69,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_A	= 0x6A,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_B	= 0x6B,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_C	= 0x6C,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_D	= 0x6D,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_E	= 0x6E,	/* event_information_section - other_transport_stream, schedule */
	TID_EIT_OTHER_SCHED_F	= 0x6F,	/* event_information_section - other_transport_stream, schedule */
	TID_TDT			= 0x70,	/* time_date_section */
	TID_RST			= 0x71,	/* running_status_section */
	TID_ST			= 0x72,	/* stuffing_section */
	TID_TOT			= 0x73,	/* time_offset_section */
	TID_AIT			= 0x74, /* application_information_section */
	TID_DIT			= 0x7E,	/* discontinuity_information_section */
	TID_SIT			= 0x7F,	/* selection_information_section */

	/* 0x80 - 0x8F: ETSI ETR 289 ed.1 (1996-10) */
	TID_CAMT_ECM_0		= 0x80,
	TID_CAMT_ECM_1		= 0x81,
	TID_CAMT_PRIVATE_0	= 0x82,
	TID_CAMT_PRIVATE_1	= 0x83,
	TID_CAMT_PRIVATE_2	= 0x84,
	TID_CAMT_PRIVATE_3	= 0x85,
	TID_CAMT_PRIVATE_4	= 0x86,
	TID_CAMT_PRIVATE_5	= 0x87,
	TID_CAMT_PRIVATE_6	= 0x88,
	TID_CAMT_PRIVATE_7	= 0x89,
	TID_CAMT_PRIVATE_8	= 0x8A,
	TID_CAMT_PRIVATE_9	= 0x8B,
	TID_CAMT_PRIVATE_A	= 0x8C,
	TID_CAMT_PRIVATE_B	= 0x8D,
	TID_CAMT_PRIVATE_C	= 0x8E,
	TID_CAMT_PRIVATE_D	= 0x8F,

	/* 0x90 - 0xFE: PRIVATE */
	TID_TOC			= 0x91,
	TID_HIT			= 0x92,

	/* 0xFF: ISO RESERVED */
	TID_RESERVED		= 0xFF
};

#endif /* __dvb_id_table_id_h__ */
