#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <memory.h>
#include <time.h>

#include <asm/types.h>
#include <lib/dvb/idemux.h>
#include <lib/dvb/subtitle.h>
#include <lib/base/smartptr.h>
#include <lib/base/eerror.h>
#include <lib/gdi/gpixmap.h>
#include <lib/base/nconfig.h>

void bitstream_init(bitstream *bit, const void *buffer, int size)
{
	bit->data = (uint8_t*) buffer;
	bit->size = size;
	bit->avail = 8;
	bit->consumed = 0;
}

int bitstream_get(bitstream *bit)
{
	int val;
	bit->avail -= bit->size;
	val = ((*bit->data) >> bit->avail) & ((1<<bit->size) - 1);
	if (!bit->avail)
	{
		bit->data++;
		bit->consumed++;
		bit->avail = 8;
	}
	return val;
}

static int extract_pts(pts_t &pts, uint8_t *pkt)
{
	if (pkt[7] & 0x80) /* PTS present? */
	{
		pts = ((unsigned long long)(pkt[9] & 0xe)) << 29;
		pts |= ((unsigned long long)(pkt[10] & 0xff)) << 22;
		pts |= ((unsigned long long)(pkt[11] & 0xfe)) << 14;
		pts |= ((unsigned long long)(pkt[12] & 0xff)) << 7;
		pts |= ((unsigned long long)(pkt[13] & 0xfe)) >> 1;

		return 0;
	} else
		return -1;
}

void eDVBSubtitleParser::subtitle_process_line(subtitle_region *region, subtitle_region_object *object, int line, uint8_t *data, int len)
{
	bool subcentered = eConfigManager::getConfigBoolValue("config.subtitles.dvb_subtitles_centered");
	int x = subcentered ? (region->width - len) /2 : object->object_horizontal_position;
	int y = object->object_vertical_position + line;
	if (x + len > region->width)
	{
		len = region->width - x;
	}
	if (len < 0)
		return;
	if (y >= region->height)
	{
		return;
	}
	if( subcentered && region->region_id && line < 3 )
	{
		for (int i = 0; i < len; i++ )
			if( data[i] <= 8)
			{
				data[i] = 0;
			}
	}
	memcpy((uint8_t*)region->buffer->surface->data + region->buffer->surface->stride * y + x, data, len);
}

static int map_2_to_4_bit_table[4];
static int map_2_to_8_bit_table[4];
static int map_4_to_8_bit_table[16];

int eDVBSubtitleParser::subtitle_process_pixel_data(subtitle_region *region, subtitle_region_object *object, int *linenr, int *linep, uint8_t *data)
{
	int data_type = *data++;
	static uint8_t line[1920];

	bitstream bit;
	bit.size=0;
	switch (data_type)
	{
	case 0x10: // 2bit pixel data
		bitstream_init(&bit, data, 2);
		while (1)
		{
			int len=0, col=0;
			int code = bitstream_get(&bit);
			if (code)
			{
				col = code;
				len = 1;
			} else
			{
				code = bitstream_get(&bit);
				if (!code)
				{
					code = bitstream_get(&bit);
					if (code == 1)
					{
						col = 0;
						len = 2;
					} else if (code == 2)
					{
						len = bitstream_get(&bit) << 2;
						len |= bitstream_get(&bit);
						len += 12;
						col = bitstream_get(&bit);
					} else if (code == 3)
					{
						len = bitstream_get(&bit) << 6;
						len |= bitstream_get(&bit) << 4;
						len |= bitstream_get(&bit) << 2;
						len |= bitstream_get(&bit);
						len += 29;
						col = bitstream_get(&bit);
					} else
						break;
				} else if (code==1)
				{
					col = 0;
					len = 1;
				} else if (code&2)
				{
					if (code&1)
						len = 3 + 4 + bitstream_get(&bit);
					else
						len = 3 + bitstream_get(&bit);
					col = bitstream_get(&bit);
				}
			}
			uint8_t c = region->depth == subtitle_region::bpp4 ?
				map_2_to_4_bit_table[col] :
				region->depth == subtitle_region::bpp8 ?
				map_2_to_8_bit_table[col] : col;
			while (len && ((*linep) < m_display_size.width()))
			{
				line[(*linep)++] = c;
				len--;
			}
		}
		while (bit.avail != 8)
			bitstream_get(&bit);
		return bit.consumed + 1;
	case 0x11: // 4bit pixel data
		bitstream_init(&bit, data, 4);
		while (1)
		{
			int len=0, col=0;
			int code = bitstream_get(&bit);
			if (code)
			{
				col = code;
				len = 1;
			} else
			{
				code = bitstream_get(&bit);
				if (!code)
					break;
				else if (code == 0xC)
				{
					col = 0;
					len = 1;
				} else if (code == 0xD)
				{
					col = 0;
					len = 2;
				} else if (code < 8)
				{
					col = 0;
					len = (code & 7) + 2;
				} else if ((code & 0xC) == 0x8)
				{
					col = bitstream_get(&bit);
					len = (code & 3) + 4;
				} else if (code == 0xE)
				{
					len = bitstream_get(&bit) + 9;
					col = bitstream_get(&bit);
				} else if (code == 0xF)
				{
					len  = bitstream_get(&bit) << 4;
					len |= bitstream_get(&bit);
					len += 25;
					col  = bitstream_get(&bit);
				}
			}
			uint8_t c = region->depth == subtitle_region::bpp8 ?
				map_4_to_8_bit_table[col] : col;
			while (len && ((*linep) < m_display_size.width()))
			{
				line[(*linep)++] = c;
				len--;
			}
		}
		while (bit.avail != 8)
			bitstream_get(&bit);
		return bit.consumed + 1;
	case 0x12: // 8bit pixel data
		bitstream_init(&bit, data, 8);
		while(1)
		{
			int len=0, col=0;
			int code = bitstream_get(&bit);
			if (code)
			{
				col = code;
				len = 1;
			} else
			{
				code = bitstream_get(&bit);
				if ((code & 0x80) == 0x80)
				{
					len = code&0x7F;
					col = bitstream_get(&bit);
				} else if (code&0x7F)
				{
					len = code&0x7F;
					col = 0;
				} else
					break;
			}
			while (len && ((*linep) < m_display_size.width()))
			{
				line[(*linep)++] = col;
				len--;
			}
		}
		return bit.consumed + 1;
	case 0x20:
		bitstream_init(&bit, data, 4);
		for ( int i=0; i < 4; ++i )
		{
			map_2_to_4_bit_table[i] = bitstream_get(&bit);
		}
		return bit.consumed + 1;
	case 0x21:
		bitstream_init(&bit, data, 8);
		for ( int i=0; i < 4; ++i )
		{
			map_2_to_8_bit_table[i] = bitstream_get(&bit);
		}
		return bit.consumed + 1;
	case 0x22:
		bitstream_init(&bit, data, 8);
		for ( int i=0; i < 16; ++i )
		{
			map_4_to_8_bit_table[i] = bitstream_get(&bit);
		}
		return bit.consumed + 1;
	case 0xF0:
		subtitle_process_line(region, object, *linenr, line, *linep);
		(*linenr)+=2; // interlaced
		*linep = 0;
		return 1;
	default:
		return -1;
	}
	return 0;
}

int eDVBSubtitleParser::subtitle_process_segment(uint8_t *segment)
{
	int segment_type, page_id, segment_length, processed_length;
	if (*segment++ !=  0x0F)
	{
		eDebug("[eDVBSubtitleParser] out of sync.");
		return -1;
	}
	segment_type = *segment++;
	page_id  = *segment++ << 8;
	page_id |= *segment++;
	segment_length  = *segment++ << 8;
	segment_length |= *segment++;
	if (segment_type == 0xFF)
		return segment_length + 6;
	if (page_id != m_composition_page_id && page_id != m_ancillary_page_id)
		return segment_length + 6;

	subtitle_page *page, **ppage;

	page = m_pages; ppage = &m_pages;

	while (page)
	{
		if (page->page_id == page_id)
			break;
		ppage = &page->next;
		page = page->next;
	}

	processed_length = 0;

	switch (segment_type)
	{
	case 0x10: // page composition segment
	{
		int page_time_out = *segment++; processed_length++;
		int page_version_number = *segment >> 4;
		int page_state = (*segment >> 2) & 0x3;
		segment++;
		processed_length++;

		if (!page)
		{
			page = new subtitle_page;
			page->page_regions = 0;
			page->regions = 0;
			page->page_id = page_id;
			page->cluts = 0;
			page->next = 0;
			*ppage = page;
		} else
		{
			if (page->pcs_size != segment_length)
				page->page_version_number = -1;
				// if no update, just skip this data.
			if (page->page_version_number == page_version_number)
			{
				break;
			}
		}

		page->state = page_state;

		// when acquisition point or mode change: remove all displayed pages.
		if ((page_state == 1) || (page_state == 2))
		{
			while (page->page_regions)
			{
				subtitle_page_region *p = page->page_regions->next;
				delete page->page_regions;
				page->page_regions = p;
			}
			while (page->regions)
			{
				subtitle_region *p = page->regions->next;
				while(page->regions->objects)
				{
					subtitle_region_object *ob = page->regions->objects->next;
					delete page->regions->objects;
					page->regions->objects = ob;
				}
				delete page->regions;
				page->regions = p;
			}

		}

		page->page_time_out = page_time_out;

		page->page_version_number = page_version_number;

		subtitle_page_region **r = &page->page_regions;

		// go to last entry
		while (*r)
			r = &(*r)->next;

		if (processed_length == segment_length && !page->page_regions)
			subtitle_redraw(page->page_id);

		while (processed_length < segment_length)
		{
			subtitle_page_region *pr;

				// append new entry to list
			pr = new subtitle_page_region;
			pr->next = 0;
			*r = pr;
			r = &pr->next;

			pr->region_id = *segment++; processed_length++;
			segment++; processed_length++;

			pr->region_horizontal_address  = *segment++ << 8;
			pr->region_horizontal_address |= *segment++;
			processed_length += 2;

			pr->region_vertical_address  = *segment++ << 8;
			pr->region_vertical_address |= *segment++;
			processed_length += 2;
		}

		if (processed_length != segment_length)
			eDebug("[eDVBSubtitleParser] %d != %d", processed_length, segment_length);
		break;
	}
	case 0x11: // region composition segment
	{
		int region_id = *segment++; processed_length++;
		int version_number = *segment >> 4;
		int region_fill_flag = (*segment >> 3) & 1;
		segment++; processed_length++;

		// if we didn't yet received the pcs for this page, drop the region
		if (!page)
		{
			eDebug("[eDVBSubtitleParser] ignoring region %x, since page %02x doesn't yet exist.", region_id, page_id);
			break;
		}

		subtitle_region *region, **pregion;

		region = page->regions; pregion = &page->regions;

		while (region)
		{
			fflush(stdout);
			if (region->region_id == region_id)
				break;
			pregion = &region->next;
			region = region->next;
		}

		if (!region)
		{
			*pregion = region = new subtitle_region;
			region->next = 0;
			region->committed = false;
		}
		else if (region->version_number != version_number)
		{
			subtitle_region_object *objects = region->objects;
			while (objects)
			{
				subtitle_region_object *n = objects->next;
				delete objects;
				objects = n;
			}
			if (region->buffer)
			{
				region->buffer=0;
			}
			region->committed = false;
		}
		else
			break;

		region->region_id = region_id;
		region->version_number = version_number;

		region->width  = *segment++ << 8;
		region->width |= *segment++;
		processed_length += 2;

		region->height  = *segment++ << 8;
		region->height |= *segment++;
		processed_length += 2;

		region->buffer = new gPixmap(eSize(region->width, region->height), 8, 1);
		memset(region->buffer->surface->data, 0, region->height * region->buffer->surface->stride);

		int depth;
		depth = (*segment++ >> 2) & 7;

		region->depth = (subtitle_region::tDepth) depth;
		processed_length++;

		int CLUT_id = *segment++; processed_length++;

		region->clut_id = CLUT_id;

		int region_8bit_pixel_code, region_4bit_pixel_code, region_2bit_pixel_code;
		region_8bit_pixel_code = *segment++; processed_length++;
		region_4bit_pixel_code = *segment >> 4;
		region_2bit_pixel_code = (*segment++ >> 2) & 3;
		processed_length++;

		if (!region_fill_flag)
		{
			region_2bit_pixel_code = region_4bit_pixel_code = region_8bit_pixel_code = 0;
			region_fill_flag = 1;
		}

		if (region_fill_flag)
		{
			if (depth == 1)
				memset(region->buffer->surface->data, region_2bit_pixel_code, region->height * region->width);
			else if (depth == 2)
				memset(region->buffer->surface->data, region_4bit_pixel_code, region->height * region->width);
			else if (depth == 3)
				memset(region->buffer->surface->data, region_8bit_pixel_code, region->height * region->width);
			else
				eDebug("[eDVBSubtitleParser] !!!! invalid depth");
		}

		region->objects = 0;
		subtitle_region_object **pobject = &region->objects;

		while (processed_length < segment_length)
		{
			subtitle_region_object *object;

			object = new subtitle_region_object;

			*pobject = object;
			object->next = 0;
			pobject = &object->next;

			object->object_id  = *segment++ << 8;
			object->object_id |= *segment++; processed_length += 2;

			object->object_type = *segment >> 6;
			object->object_provider_flag = (*segment >> 4) & 3;
			object->object_horizontal_position  = (*segment++ & 0xF) << 8;
			object->object_horizontal_position |= *segment++;
			processed_length += 2;

			object->object_vertical_position  = *segment++ << 8;
			object->object_vertical_position |= *segment++ ;
			processed_length += 2;

			if ((object->object_type == 1) || (object->object_type == 2))
			{
				object->foreground_pixel_value = *segment++;
				object->background_pixel_value = *segment++;
				processed_length += 2;
			}
		}

		if (processed_length != segment_length)
			eDebug("[eDVBSubtitleParser] too less data! (%d < %d)", segment_length, processed_length);

		break;
	}
	case 0x12: // CLUT definition segment
	{
		int CLUT_id, CLUT_version_number;
		subtitle_clut *clut, **pclut;

		if (!page)
			break;

		CLUT_id = *segment++;

		CLUT_version_number = *segment++ >> 4;
		processed_length += 2;

		clut = page->cluts; pclut = &page->cluts;

		while (clut)
		{
			if (clut->clut_id == CLUT_id)
				break;
			pclut = &clut->next;
			clut = clut->next;
		}

		if (!clut)
		{
			*pclut = clut = new subtitle_clut;
			clut->next = 0;
			clut->clut_id = CLUT_id;
		}
		else if (clut->CLUT_version_number == CLUT_version_number)
			break;

		clut->CLUT_version_number=CLUT_version_number;

		memset(clut->entries_2bit, 0, sizeof(clut->entries_2bit));
		memset(clut->entries_4bit, 0, sizeof(clut->entries_4bit));
		memset(clut->entries_8bit, 0, sizeof(clut->entries_8bit));

		while (processed_length < segment_length)
		{
			int CLUT_entry_id, entry_CLUT_flag, full_range;
			int v_Y, v_Cr, v_Cb, v_T;

			CLUT_entry_id = *segment++;
			full_range = *segment & 1;
			entry_CLUT_flag = (*segment++ & 0xE0) >> 5;
			processed_length += 2;

			if (full_range)
			{
				v_Y  = *segment++;
				v_Cr = *segment++;
				v_Cb = *segment++;
				v_T  = *segment++;
				processed_length += 4;
			} else
			{
				v_Y   = *segment & 0xFC;
				v_Cr  = (*segment++ & 3) << 6;
				v_Cr |= (*segment & 0xC0) >> 2;
				v_Cb  = (*segment & 0x3C) << 2;
				v_T   = (*segment++ & 3) << 6;
				processed_length += 2;
			}

			if (entry_CLUT_flag & 1) // 8bit
			{
				clut->entries_8bit[CLUT_entry_id].Y = v_Y;
				clut->entries_8bit[CLUT_entry_id].Cr = v_Cr;
				clut->entries_8bit[CLUT_entry_id].Cb = v_Cb;
				clut->entries_8bit[CLUT_entry_id].T = v_T;
				clut->entries_8bit[CLUT_entry_id].valid = 1;
			}
			if (entry_CLUT_flag & 2) // 4bit
			{
				if (CLUT_entry_id < 16)
				{
					clut->entries_4bit[CLUT_entry_id].Y = v_Y;
					clut->entries_4bit[CLUT_entry_id].Cr = v_Cr;
					clut->entries_4bit[CLUT_entry_id].Cb = v_Cb;
					clut->entries_4bit[CLUT_entry_id].T = v_T;
					clut->entries_4bit[CLUT_entry_id].valid = 1;
				}
				else
					eDebug("[eDVBSubtitleParser] CLUT entry marked as 4 bit with id %d (>15)", CLUT_entry_id);
			}
			if (entry_CLUT_flag & 4) // 2bit
			{
				if (CLUT_entry_id < 4)
				{
					clut->entries_2bit[CLUT_entry_id].Y = v_Y;
					clut->entries_2bit[CLUT_entry_id].Cr = v_Cr;
					clut->entries_2bit[CLUT_entry_id].Cb = v_Cb;
					clut->entries_2bit[CLUT_entry_id].T = v_T;
					clut->entries_2bit[CLUT_entry_id].valid = 1;
				}
				else
					eDebug("[eDVBSubtitleParser] CLUT entry marked as 2 bit with id %d (>3)", CLUT_entry_id);
			}
		}
		break;
	}
	case 0x13: // object data segment
	{
		int object_id;
		int object_coding_method;

		object_id  = *segment++ << 8;
		object_id |= *segment++;
		processed_length += 2;

		object_coding_method  = (*segment >> 2) & 3;
		segment++; // non_modifying_color_flag
		processed_length++;

		subtitle_region *region = page->regions;
		while (region)
		{
			subtitle_region_object *object = region->objects;
			while (object)
			{
				if (object->object_id == object_id)
				{
					if (object_coding_method == 0)
					{
						int top_field_data_blocklength, bottom_field_data_blocklength;
						int i=1, line, linep;

						top_field_data_blocklength  = *segment++ << 8;
						top_field_data_blocklength |= *segment++;

						bottom_field_data_blocklength  = *segment++ << 8;
						bottom_field_data_blocklength |= *segment++;
						processed_length += 4;

						// its working on cyfra channels.. but hmm in EN300743 the default table is 0, 7, 8, 15
						map_2_to_4_bit_table[0] = 0;
						map_2_to_4_bit_table[1] = 8;
						map_2_to_4_bit_table[2] = 7;
						map_2_to_4_bit_table[3] = 15;

						// this map is realy untested...
						map_2_to_8_bit_table[0] = 0;
						map_2_to_8_bit_table[1] = 0x88;
						map_2_to_8_bit_table[2] = 0x77;
						map_2_to_8_bit_table[3] = 0xff;

						map_4_to_8_bit_table[0] = 0;
						for (; i < 16; ++i)
							map_4_to_8_bit_table[i] = i * 0x11;

						i = 0;
						line = 0;
						linep = 0;
						while (i < top_field_data_blocklength)
						{
							int len;
							len = subtitle_process_pixel_data(region, object, &line, &linep, segment);
							if (len < 0)
								return -1;
							segment += len;
							processed_length += len;
							i += len;
						}

						line = 1;
						linep = 0;

						if (bottom_field_data_blocklength)
						{
							i = 0;
							while (i < bottom_field_data_blocklength)
							{
								int len;
								len = subtitle_process_pixel_data(region, object, &line, &linep, segment);
								if (len < 0)
									return -1;
								segment += len;
									processed_length += len;
								i += len;
							}
						}
						else if (top_field_data_blocklength)
							eDebug("[eDVBSubtitleParser] !!!! unimplemented: no bottom field! (%d : %d)", top_field_data_blocklength, bottom_field_data_blocklength);

						if ((top_field_data_blocklength + bottom_field_data_blocklength) & 1)
						{
							segment++; processed_length++;
						}
					}
					else if (object_coding_method == 1)
						eDebug("[eDVBSubtitleParser] ---- object_coding_method 1 unsupported!");
				}
				object = object->next;
			}
			region = region->next;
		}
		break;
	}
	case 0x14: // display definition segment
	{
		if (segment_length > 4)
		{
			int display_window_flag = (segment[0] >> 3) & 1;
			int display_width = (segment[1] << 8) | (segment[2]);
			int display_height = (segment[3] << 8) | (segment[4]);
			processed_length += 5;
			m_display_size = eSize(display_width+1, display_height+1);
			if (display_window_flag)
			{
				if (segment_length > 12)
				{
					int display_window_horizontal_position_min = (segment[4] << 8) | segment[5];
					int display_window_horizontal_position_max = (segment[6] << 8) | segment[7];
					int display_window_vertical_position_min = (segment[8] << 8) | segment[9];
					int display_window_vertical_position_max = (segment[10] << 8) | segment[11];
					eDebug("[eDVBSubtitleParser] NYI hpos min %d, hpos max %d, vpos min %d, vpos max %d",
						display_window_horizontal_position_min,
						display_window_horizontal_position_max,
						display_window_vertical_position_min,
						display_window_vertical_position_max);
					processed_length += 8;
				}
				else
					eDebug("[eDVBSubtitleParser] display window flag set but display definition segment to short %d!", segment_length);
			}
		}
		else
			eDebug("[eDVBSubtitleParser] display definition segment to short %d!", segment_length);
		break;
	}
	case 0x80: // end of display set segment
	{
		subtitle_redraw_all();
		m_seen_eod = true;
	}
	case 0xFF: // stuffing
		break;
	default:
		eDebug("[eDVBSubtitleParser] unhandled segment type %02x", segment_type);
	}

	return segment_length + 6;
}

void eDVBSubtitleParser::subtitle_process_pes(uint8_t *pkt, int len)
{
	if (!extract_pts(m_show_time, pkt))
	{
		pkt += 6; len -= 6;
		// skip PES header
		pkt++; len--;
		pkt++; len--;

		int hdr_len = *pkt++; len--;

		pkt+=hdr_len; len-=hdr_len;

		if (*pkt != 0x20)
			return;

		pkt++; len--; // data identifier
		pkt++; len--; // stream id;

		if (len <= 0)
			return;

		m_seen_eod = false;

		while (len && *pkt == 0x0F)
		{
			int l = subtitle_process_segment(pkt);
			if (l < 0)
				break;
			pkt += l;
			len -= l;
		}

		if (len && *pkt != 0xFF)
			eDebug("[eDVBSubtitleParser] strange data at the end");

		if (!m_seen_eod)
			subtitle_redraw_all();
	}
}

void eDVBSubtitleParser::subtitle_redraw_all()
{
	subtitle_page *page = m_pages;

	while(page)
	{
		subtitle_redraw(page->page_id);
		page = page->next;
	}
}

void eDVBSubtitleParser::subtitle_reset()
{
	while (subtitle_page *page = m_pages)
	{
			/* free page regions */
		while (page->page_regions)
		{
			subtitle_page_region *p = page->page_regions->next;
			delete page->page_regions;
			page->page_regions = p;
		}
			/* free regions */
		while (page->regions)
		{
			subtitle_region *region = page->regions;

			while (region->objects)
			{
				subtitle_region_object *obj = region->objects;
				region->objects = obj->next;
				delete obj;
			}

			if (region->buffer)
				region->buffer=0;

			page->regions = region->next;
			delete region;
		}

			/* free CLUTs */
		while (page->cluts)
		{
			subtitle_clut *clut = page->cluts;
			page->cluts = clut->next;
			delete clut;
		}

		m_pages = page->next;
		delete page;
	}
}

void eDVBSubtitleParser::subtitle_redraw(int page_id)
{
	subtitle_page *page = m_pages;

	while (page)
	{
		if (page->page_id == page_id)
			break;
		page = page->next;
	}
	if (!page)
		return;

	/* iterate all regions in this pcs */
	subtitle_page_region *region = page->page_regions;

	eDVBSubtitlePage Page;
	Page.m_show_time = m_show_time;
	for (; region; region=region->next)
	{
		/* find corresponding region */
		subtitle_region *reg = page->regions;
		while (reg)
		{
			if (reg->region_id == region->region_id)
				break;
			reg = reg->next;
		}
		if (reg)
		{
			if (reg->committed)
				continue;

			int x0 = region->region_horizontal_address;
			int y0 = region->region_vertical_address;

			if ((x0 < 0) || (y0 < 0))
				continue;

			/* find corresponding clut */
			subtitle_clut *clut = page->cluts;
			while (clut)
			{
				if (clut->clut_id == reg->clut_id)
					break;
				clut = clut->next;
			}

			int clut_size = reg->buffer->surface->clut.colors = reg->depth == subtitle_region::bpp2 ?
				4 : reg->depth == subtitle_region::bpp4 ? 16 : 256;

			reg->buffer->surface->clut.data = new gRGB[clut_size];

			gRGB *palette = reg->buffer->surface->clut.data;

			subtitle_clut_entry *entries=0;
			switch(reg->depth)
			{
				case subtitle_region::bpp2:
					if (clut)
						entries = clut->entries_2bit;
					memset(palette, 0, 4 * sizeof(gRGB));
					// this table is tested on cyfra .. but in EN300743 the table palette[2] and palette[1] is swapped.. i dont understand this ;)
					palette[0].a = 0xFF;
					palette[2].r = palette[2].g = palette[2].b = 0xFF;
					palette[3].r = palette[3].g = palette[3].b = 0x80;
					break;
				case subtitle_region::bpp4: // tested on cyfra... but the map is another in EN300743... dont understand this...
					if (clut)
						entries = clut->entries_4bit;
					memset(palette, 0, 16*sizeof(gRGB));
					for (int i=0; i < 16; ++i)
					{
						if (!i)
							palette[i].a = 0xFF;
						else if (i & 8)
						{
							if (i & 1)
								palette[i].r = 0x80;
							if (i & 2)
								palette[i].g = 0x80;
							if (i & 4)
								palette[i].b = 0x80;
						}
						else
						{
							if (i & 1)
								palette[i].r = 0xFF;
							if (i & 2)
								palette[i].g = 0xFF;
							if (i & 4)
								palette[i].b = 0xFF;
						}
					}
					break;
				case subtitle_region::bpp8:  // completely untested.. i never seen 8bit DVB subtitles
					if (clut)
						entries = clut->entries_8bit;
					memset(palette, 0, 256*sizeof(gRGB));
					for (int i=0; i < 256; ++i)
					{
						switch (i & 17)
						{
						case 0: // b1 == 0 && b5 == 0
							if (!(i & 14)) // b2 == 0 && b3 == 0 && b4 == 0
							{
								if (!(i & 224)) // b6 == 0 && b7 == 0 && b8 == 0
									palette[i].a = 0xFF;
								else
								{
									if (i & 128) // R = 100% x b8
										palette[i].r = 0xFF;
									if (i & 64) // G = 100% x b7
										palette[i].g = 0xFF;
									if (i & 32) // B = 100% x b6
										palette[i].b = 0xFF;
									palette[i].a = 0xBF; // T = 75%
								}
								break;
							}
							// fallthrough !!
						case 16: // b1 == 0 && b5 == 1
							if (i & 128) // R = 33% x b8
								palette[i].r = 0x55;
							if (i & 64) // G = 33% x b7
								palette[i].g = 0x55;
							if (i & 32) // B = 33% x b6
								palette[i].b = 0x55;
							if (i & 8) // R + 66,7% x b4
								palette[i].r += 0xAA;
							if (i & 4) // G + 66,7% x b3
								palette[i].g += 0xAA;
							if (i & 2) // B + 66,7% x b2
								palette[i].b += 0xAA;
							if (i & 16) // needed for fall through from case 0!!
								palette[i].a = 0x80; // T = 50%
							break;
						case 1: // b1 == 1 && b5 == 0
							palette[i].r =
							palette[i].g =
							palette[i].b = 0x80; // 50%
							// fall through!!
						case 17: // b1 == 1 && b5 == 1
							if (i & 128) // R += 16.7% x b8
								palette[i].r += 0x2A;
							if (i & 64) // G += 16.7% x b7
								palette[i].g += 0x2A;
							if (i & 32) // B += 16.7% x b6
								palette[i].b += 0x2A;
							if (i & 8) // R += 33% x b4
								palette[i].r += 0x55;
							if (i & 4) // G += 33% x b3
								palette[i].g += 0x55;
							if (i & 2) // B += 33% x b2
								palette[i].b += 0x55;
							break;
						}
					}
					break;
			}

			int bcktrans = eConfigManager::getConfigIntValue("config.subtitles.dvb_subtitles_backtrans");
			bool yellow = eConfigManager::getConfigBoolValue("config.subtitles.dvb_subtitles_yellow");

			for (int i=0; i<clut_size; ++i)
			{
				if (entries && entries[i].valid)
				{
					int y = entries[i].Y,
						cr = entries[i].Cr,
						cb = entries[i].Cb;
					if (y > 0)
					{
						y -= 16;
						cr -= 128;
						cb -= 128;
						palette[i].r = MAX(MIN(((298 * y            + 460 * cr) / 256), 255), 0);
						palette[i].g = MAX(MIN(((298 * y -  55 * cb - 137 * cr) / 256), 255), 0);
						palette[i].b = yellow?0:MAX(MIN(((298 * y + 543 * cb  ) / 256), 255), 0);
						if (bcktrans)
						{
							if (palette[i].r || palette[i].g || palette[i].b)
								palette[i].a = (entries[i].T) & 0xFF;
							else
								palette[i].a = bcktrans;
						}
						else
							palette[i].a = (entries[i].T) & 0xFF;
					}
					else
					{
						palette[i].r = 0;
						palette[i].g = 0;
						palette[i].b = 0;
						palette[i].a = 0xFF;
					}
				}
			}

			eDVBSubtitleRegion Region;
			Region.m_pixmap = reg->buffer;
			Region.m_position.setX(x0);
			Region.m_position.setY(y0);
			Page.m_regions.push_back(Region);
			reg->committed = true;
		}
	}
	Page.m_display_size = m_display_size;
	m_new_subtitle_page(Page);
	Page.m_regions.clear();
}

DEFINE_REF(eDVBSubtitleParser);

eDVBSubtitleParser::eDVBSubtitleParser(iDVBDemux *demux)
	:m_pages(0), m_display_size(720,576)
{
	setStreamID(0xBD);

	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("[eDVBSubtitleParser] failed to create PES reader!");
	else
		m_pes_reader->connectRead(slot(*this, &eDVBSubtitleParser::processData), m_read_connection);
}

eDVBSubtitleParser::~eDVBSubtitleParser()
{
	subtitle_reset();
}

int eDVBSubtitleParser::stop()
{
	if (m_pes_reader)
	{
		eDebug("[eDVBSubtitleParser] disable dvb subtitles");
		return m_pes_reader->stop();
	}
	return -1;
}

int eDVBSubtitleParser::start(int pid, int composition_page_id, int ancillary_page_id)
{
	if (m_pes_reader && pid >= 0 && pid < 0x1fff)
	{
		eDebug("[eDVBSubtitleParser] start on pid 0x%04x with composition_page_id %d and ancillary_page_id %d",
			pid, composition_page_id, ancillary_page_id);
		m_composition_page_id = composition_page_id;
		m_ancillary_page_id = ancillary_page_id;
		return m_pes_reader->start(pid);
	}
	return -1;
}

void eDVBSubtitleParser::connectNewPage(const Slot1<void, const eDVBSubtitlePage&> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_new_subtitle_page.connect(slot));
}
