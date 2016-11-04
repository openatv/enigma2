
/*
 * EVENT INFORMATION TABLE
 *
 * Copyright (C) 1998  Thomas Mirlacher
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
 * The author may be reached as dent@cosy.sbg.ac.at, or
 * Thomas Mirlacher, Jakob-Haringerstr. 2, A-5020 Salzburg,
 * Austria
 *
 *------------------------------------------------------------
 *
 */

#ifndef __EIT_H__
#define __EIT_H__

// Service Description Section
#include <sys/types.h>

typedef struct {
	u_char	table_id			: 8;

#if BYTE_ORDER == BIG_ENDIAN
	u_char	section_syntax_indicator	: 1;
	u_char					: 3;
	u_char	section_length_hi		: 4;
#else
	u_char	section_length_hi		: 4;
	u_char					: 3;
	u_char	section_syntax_indicator	: 1;
#endif

	u_char	section_length_lo		: 8;

	u_char	service_id_hi			: 8;
	u_char	service_id_lo			: 8;

#if BYTE_ORDER == BIG_ENDIAN
	u_char					: 2;
	u_char	version_number			: 5;
	u_char	current_next_indicator		: 1;
#else
	u_char	current_next_indicator		: 1;
	u_char	version_number			: 5;
	u_char					: 2;
#endif

	u_char	section_number			: 8;
	u_char	last_section_number		: 8;
	u_char	transport_stream_id_hi		: 8;
	u_char	transport_stream_id_lo		: 8;
	u_char	original_network_id_hi		: 8;
	u_char	original_network_id_lo		: 8;
	u_char	segment_last_section_number	: 8;
	u_char	segment_last_table_id		: 8;

	int getSectionLength() const		{ return section_length_hi << 8 | section_length_lo; };
	int getServiceId() const		{ return service_id_hi << 8 | service_id_lo; };
	int getTransportStreamId() const	{ return transport_stream_id_hi << 8 | transport_stream_id_lo; };
	int getOriginalNetworkId() const	{ return original_network_id_hi << 8 | original_network_id_lo; };

	void setSectionLength(int length)	{ section_length_hi = length >> 8; section_length_lo = length & 0xFF; };
	void setServiceId(int serviceId)	{ service_id_hi = serviceId >> 8; service_id_lo = serviceId & 0xFF; };
	void setTransportStreamId(int tsi)	{ transport_stream_id_hi = tsi >> 8; transport_stream_id_lo = tsi & 0xFF; };
	void setOriginalNetworkId(int oni)	{ original_network_id_hi = oni >> 8; original_network_id_lo = oni & 0xFF; };
} eit_t;

#define EIT_SIZE 14

struct eit_loop_struct1 {
	u_char	service_id_hi			: 8;
	u_char	service_id_lo			: 8;

#if BYTE_ORDER == BIG_ENDIAN
	u_char					: 6;
	u_char	eit_schedule_flag		: 1;
	u_char	eit_present_following_flag	: 1;

	u_char	running_status			: 3;
	u_char	free_ca_mode			: 1;
	u_char	descriptors_loop_length_hi	: 4;
#else
	u_char	eit_present_following_flag	: 1;
	u_char	eit_schedule_flag		: 1;
	u_char					: 6;

	u_char	descriptors_loop_length_hi	: 4;
	u_char	free_ca_mode			: 1;
	u_char	running_status			: 3;
#endif

	u_char	descriptors_loop_length_lo	: 8;
};

#define EIT_SHORT_EVENT_DESCRIPTOR 0x4d
#define EIT_SHORT_EVENT_DESCRIPTOR_SIZE 6

struct eit_short_event_descriptor_struct {
	u_char	descriptor_tag			: 8;
	u_char	descriptor_length		: 8;

	u_char	language_code_1			: 8;
	u_char	language_code_2			: 8;
	u_char	language_code_3			: 8;

	u_char	event_name_length		: 8;
};

#define EIT_EXTENDED_EVENT_DESCRIPOR 0x4e

typedef struct eit_event_struct {
	u_char	event_id_hi			: 8;
	u_char	event_id_lo			: 8;

	u_char	start_time_1			: 8;
	u_char	start_time_2			: 8;
	u_char	start_time_3			: 8;
	u_char	start_time_4			: 8;
	u_char	start_time_5			: 8;

	u_char	duration_1			: 8;
	u_char	duration_2			: 8;
	u_char	duration_3			: 8;

#if BYTE_ORDER == BIG_ENDIAN
	u_char	running_status			: 3;
	u_char	free_CA_mode			: 1;
	u_char	descriptors_loop_length_hi	: 4;
#else
	u_char	descriptors_loop_length_hi	: 4;
	u_char	free_CA_mode			: 1;
	u_char	running_status			: 3;
#endif

	u_char	descriptors_loop_length_lo	: 8;

	uint16_t getEventId() const		{ return event_id_hi << 8 | event_id_lo; };
	int getDescriptorsLoopLength() const	{ return descriptors_loop_length_hi << 8 | descriptors_loop_length_lo; };

	void setEventId(uint16_t eventId)	{ event_id_hi = eventId >> 8; event_id_lo = eventId & 0xFF; };
	void setDescriptorsLoopLength(int dll)	{ descriptors_loop_length_hi = dll >> 8; descriptors_loop_length_lo = dll & 0xFF; };
} eit_event_t;
#define EIT_LOOP_SIZE 12

#define EIT_EXTENDED_EVENT_DESCRIPOR 0x4e

struct eit_extended_descriptor_struct {
	u_char descriptor_tag : 8;
	u_char descriptor_length : 8;
#if BYTE_ORDER == BIG_ENDIAN
	u_char descriptor_number : 4;
	u_char last_descriptor_number : 4;
#else
	u_char last_descriptor_number : 4;
	u_char descriptor_number : 4;
#endif
	u_char iso_639_2_language_code_1 : 8;
	u_char iso_639_2_language_code_2 : 8;
	u_char iso_639_2_language_code_3 : 8;
};


#endif
