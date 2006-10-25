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

void bitstream_init(bitstream *bit, const void *buffer, int size)
{
	bit->data = (__u8*) buffer;
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

static int extract_pts(pts_t &pts, __u8 *pkt)
{
	pkt += 7;
	int flags = *pkt++;

	pkt++; // header length

	if (flags & 0x80) /* PTS present? */
	{
			/* damn gcc bug */
		pts  = ((unsigned long long)(((pkt[0] >> 1) & 7))) << 30;
		pts |=   pkt[1] << 22;
		pts |=  (pkt[2]>>1) << 15;
		pts |=   pkt[3] << 7;
		pts |=  (pkt[5]>>1);

		return 0;
	} else
		return -1;
}

void eDVBSubtitleParser::subtitle_process_line(subtitle_page *page, int object_id, int line, __u8 *data, int len)
{
	subtitle_region *region = page->regions;
//	eDebug("line for %d:%d", page->page_id, object_id);
	while (region)
	{
		subtitle_region_object *object = region->region_objects;
		while (object)
		{
			if (object->object_id == object_id)
			{
				int x = object->object_horizontal_position;
				int y = object->object_vertical_position + line;
				if (x + len > region->region_width)
				{
					//eDebug("[SUB] !!!! XCLIP %d + %d > %d", x, len, region->region_width);
					len = region->region_width - x;
				}
				if (len < 0)
					break;
				if (y >= region->region_height)
				{
					//eDebug("[SUB] !!!! YCLIP %d >= %d", y, region->region_height);
					break;
				}
//				//eDebug("inserting %d bytes (into region %d)", len, region->region_id);
				memcpy((__u8*)region->region_buffer->surface->data + region->region_width * y + x, data, len);
			}
			object = object->next;
		}
		region = region->next;
	}
}

int eDVBSubtitleParser::subtitle_process_pixel_data(subtitle_page *page, int object_id, int *linenr, int *linep, __u8 *data)
{
	int data_type = *data++;
	static __u8 line[720];

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
			while (len && ((*linep) < 720))
			{
				line[(*linep)++] = col;
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
			while (len && ((*linep) < 720))
			{
				line[(*linep)++] = col;
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
			while (len && ((*linep) < 720))
			{
				line[(*linep)++] = col;
				len--;
			}
		}
		return bit.consumed + 1;
	case 0x20:  // ignore 2 -> 4bit map table
		bitstream_init(&bit, data, 4);
		for ( int i=0; i < 4; ++i )
			bitstream_get(&bit);
		break;
	case 0x21:  // ignore 2 -> 8bit map table
		bitstream_init(&bit, data, 8);
		for ( int i=0; i < 4; ++i )
			bitstream_get(&bit);
		break;
	case 0x22:  // ignore 4 -> 8bit map table
		bitstream_init(&bit, data, 8);
		for ( int i=0; i < 16; ++i )
			bitstream_get(&bit);
		break;
	case 0xF0:
		subtitle_process_line(page, object_id, *linenr, line, *linep);
/*		{
			int i;
			for (i=0; i<720; ++i)
				//eDebugNoNewLine("%d ", line[i]);
			//eDebug("");
		} */
		(*linenr)+=2; // interlaced
		*linep = 0;
//		//eDebug("[SUB] EOL");
		return 1;
	default:
		eDebug("subtitle_process_pixel_data: invalid data_type %02x", data_type);
		return -1;
	}
	return 0;
}

int eDVBSubtitleParser::subtitle_process_segment(__u8 *segment)
{
	int segment_type, page_id, segment_length, processed_length;
	if (*segment++ !=  0x0F)
	{
		eDebug("out of sync.");
		return -1;
	}
	segment_type = *segment++;
	page_id  = *segment++ << 8;
	page_id |= *segment++;
	segment_length  = *segment++ << 8;
	segment_length |= *segment++;
	if (segment_type == 0xFF)
		return segment_length + 6;
//	//eDebug("have %d bytes of segment data", segment_length);

//	//eDebug("page_id %d, segtype %02x", page_id, segment_type);

	subtitle_page *page, **ppage;

	page = this->pages; ppage = &this->pages;

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
		//eDebug("pcs with %d bytes data (%d:%d:%d)", segment_length, page_id, page_version_number, page_state);
		segment++;
		processed_length++;

		//eDebug("page time out: %d", page_time_out);
		//eDebug("page_version_number: %d" ,page_version_number);
		//eDebug("page_state: %d", page_state);

		if (!page)
		{
			//eDebug("page not found");
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
				eDebug("skip data... ");
				break;
			}
		}

//		eDebug("page updated: old: %d, new: %d", page->page_version_number, page_version_number);
			// when acquisition point or mode change: remove all displayed pages.
		if ((page_state == 1) || (page_state == 2))
		{
			while (page->page_regions)
			{
				subtitle_page_region *p = page->page_regions->next;
				delete page->page_regions;
				page->page_regions = p;
			}
		}

//		eDebug("new page.. (%d)", page_state);

		page->page_time_out = page_time_out;

		page->page_version_number = page_version_number;

		subtitle_page_region **r = &page->page_regions;

		//eDebug("%d  / %d data left", processed_length, segment_length);

			// go to last entry
		while (*r)
			r = &(*r)->next;

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

			//eDebug("appended active region");
		}

		if (processed_length != segment_length)
			eDebug("%d != %d", processed_length, segment_length);
		break;
	}
	case 0x11: // region composition segment
	{
		int region_id = *segment++; processed_length++;
		int region_version_number = *segment >> 4;
		int region_fill_flag = (*segment >> 3) & 1;
		segment++; processed_length++;

			// if we didn't yet received the pcs for this page, drop the region
		if (!page)
		{
			eDebug("ignoring region %x, since page %02x doesn't yet exist.", region_id, page_id);
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
		}
		else if (region->region_version_number != region_version_number)
		{
			subtitle_region_object *objects = region->region_objects;
			while (objects)
			{
				subtitle_region_object *n = objects->next;
				delete objects;
				objects = n;
			}
			if (region->region_buffer)
			{
				if (region->region_buffer->surface)
					delete region->region_buffer->surface;
				region->region_buffer=0;
			}
		}
		else
			break;

		//eDebug("region %d:%d update", page_id, region_id);

		region->region_id = region_id;
		region->region_version_number = region_version_number;

		region->region_width  = *segment++ << 8;
		region->region_width |= *segment++;
		processed_length += 2;

		region->region_height  = *segment++ << 8;
		region->region_height |= *segment++;
		processed_length += 2;

		region->region_buffer = new gPixmap(eSize(region->region_width, region->region_height), 8);

		int region_level_of_compatibility, region_depth;

		region_level_of_compatibility = (*segment >> 5) & 7;
		region_depth = (*segment++ >> 2) & 7;
		region->region_depth = (subtitle_region::depth) region_depth;
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
			if (region_depth == 1)
				memset(region->region_buffer->surface->data, region_2bit_pixel_code, region->region_height * region->region_width);
			else if (region_depth == 2)
				memset(region->region_buffer->surface->data, region_4bit_pixel_code, region->region_height * region->region_width);
			else if (region_depth == 3)
				memset(region->region_buffer->surface->data, region_8bit_pixel_code, region->region_height * region->region_width);
			else
				eDebug("!!!! invalid depth");
		}

		//eDebug("region %02x, version %d, %dx%d", region->region_id, region->region_version_number, region->region_width, region->region_height);

		region->region_objects = 0;
		subtitle_region_object **pobject = &region->region_objects;

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
			eDebug("too less data! (%d < %d)", segment_length, processed_length);

		break;
	}
	case 0x12: // CLUT definition segment
	{
		int CLUT_id, CLUT_version_number;
		subtitle_clut *clut, **pclut;

		if (!page)
			break;

		//eDebug("CLUT: %02x", *segment);
		CLUT_id = *segment++;

		CLUT_version_number = *segment++ >> 4;
		processed_length += 2;

		//eDebug("page %d, CLUT %02x, version %d", page->page_id, CLUT_id, CLUT_version_number);

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

		//eDebug("new clut");
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
				ASSERT(CLUT_entry_id < 256);
				clut->entries_8bit[CLUT_entry_id].Y = v_Y;
				clut->entries_8bit[CLUT_entry_id].Cr = v_Cr;
				clut->entries_8bit[CLUT_entry_id].Cb = v_Cb;
				clut->entries_8bit[CLUT_entry_id].T = v_T;
				clut->entries_8bit[CLUT_entry_id].valid = 1;
			}
			if (entry_CLUT_flag & 2) // 4bit
			{
				ASSERT(CLUT_entry_id < 16);
				clut->entries_4bit[CLUT_entry_id].Y = v_Y;
				clut->entries_4bit[CLUT_entry_id].Cr = v_Cr;
				clut->entries_4bit[CLUT_entry_id].Cb = v_Cb;
				clut->entries_4bit[CLUT_entry_id].T = v_T;
				clut->entries_4bit[CLUT_entry_id].valid = 1;
			}
			if (entry_CLUT_flag & 4) // 2bit
			{
				ASSERT(CLUT_entry_id < 4);
				clut->entries_2bit[CLUT_entry_id].Y = v_Y;
				clut->entries_2bit[CLUT_entry_id].Cr = v_Cr;
				clut->entries_2bit[CLUT_entry_id].Cb = v_Cb;
				clut->entries_2bit[CLUT_entry_id].T = v_T;
				clut->entries_2bit[CLUT_entry_id].valid = 1;
			}
			//eDebug("  %04x %02x %02x %02x %02x", CLUT_entry_id, v_Y, v_Cb, v_Cr, v_T);
		}
		break;
	}
	case 0x13: // object data segment
	{
		int object_id, object_version_number, object_coding_method, non_modifying_color_flag;

		object_id  = *segment++ << 8;
		object_id |= *segment++;
		processed_length += 2;

		object_version_number = *segment >> 4;
		object_coding_method  = (*segment >> 2) & 3;
		non_modifying_color_flag = (*segment++ >> 1) & 1;
		processed_length++;

		//eDebug("object id %04x, version %d, object_coding_method %d (page_id %d)", object_id, object_version_number, object_coding_method, page_id);

		if (object_coding_method == 0)
		{
			int top_field_data_blocklength, bottom_field_data_blocklength;
			int i, line, linep;

			top_field_data_blocklength  = *segment++ << 8;
			top_field_data_blocklength |= *segment++;

			bottom_field_data_blocklength  = *segment++ << 8;
			bottom_field_data_blocklength |= *segment++;
			//eDebug("%d / %d bytes", top_field_data_blocklength, bottom_field_data_blocklength);
			processed_length += 4;

			i = 0;
			line = 0;
			linep = 0;
			while (i < top_field_data_blocklength)
			{
				int len;
				len = subtitle_process_pixel_data(page, object_id, &line, &linep, segment);
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
					len = subtitle_process_pixel_data(page, object_id, &line, &linep, segment);
					if (len < 0)
						return -1;
					segment += len;
					processed_length += len;
					i += len;
				}
			}
			else if (top_field_data_blocklength)
				eDebug("!!!! unimplemented: no bottom field! (%d : %d)", top_field_data_blocklength, bottom_field_data_blocklength);

			if ((top_field_data_blocklength + bottom_field_data_blocklength) & 1)
			{
				segment++; processed_length++;
			}
		}
		else if (object_coding_method == 1)
			eDebug("---- object_coding_method 1 unsupported!");

		break;
	}
	case 0x80: // end of display set segment
	{
//		eDebug("end of display set segment");
		subtitle_redraw_all();
	}
	case 0xFF: // stuffing
		break;
	default:
		eDebug("unhandled segment type %02x", segment_type);
	}

	return segment_length + 6;
}

void eDVBSubtitleParser::subtitle_process_pes(__u8 *pkt, int len)
{
//	eDebug("subtitle_process_pes");
	if (!extract_pts(show_time, pkt))
	{
		pkt += 6; len -= 6;
		// skip PES header
		pkt++; len--;
		pkt++; len--;

		int hdr_len = *pkt++; len--;

		pkt+=hdr_len; len-=hdr_len;

		if (*pkt != 0x20)
		{
			//eDebug("data identifier is 0x%02x, but not 0x20", *pkt);
			return;
		}
		pkt++; len--; // data identifier
		*pkt++; len--; // stream id;

		if (len <= 0)
		{
			//eDebug("no data left (%d)", len);
			return;
		}

		while (len && *pkt == 0x0F)
		{
			int l = subtitle_process_segment(pkt);
			if (l < 0)
				break;
			pkt += l;
			len -= l;
		}
	//	if (len && *pkt != 0xFF)
	//		eDebug("strange data at the end");
	}
	else
		eDebug("dvb subtitle packet without PTS.. ignore!!");
}

void eDVBSubtitleParser::subtitle_redraw_all()
{
#if 1
	subtitle_page *page = this->pages;
	while(page)
	{
		subtitle_redraw(page->page_id);
		page = page->next;
	}
#else
	subtitle_page *page = this->pages;
	//eDebug("----------- end of display set");
	//eDebug("active pages:");
	while (page)
	{
		//eDebug("  page_id %02x", page->page_id);
		//eDebug("  page_version_number: %d", page->page_version_number);
		//eDebug("  active regions:");
		{
			subtitle_page_region *region = page->page_regions;
			while (region)
			{
				//eDebug("    region_id: %04x", region->region_id);
				//eDebug("    region_horizontal_address: %d", region->region_horizontal_address);
				//eDebug("    region_vertical_address: %d", region->region_vertical_address);

				region = region->next;
			}
		}

		subtitle_redraw(page->page_id);
		//eDebug("defined regions:");
		subtitle_region *region = page->regions;
		while (region)
		{
			//eDebug("  region_id %04x, version %d, %dx%d", region->region_id, region->region_version_number, region->region_width, region->region_height);

			subtitle_region_object *object = region->region_objects;
			while (object)
			{
				//eDebug("  object %02x, type %d, %d:%d", object->object_id, object->object_type, object->object_horizontal_position, object->object_vertical_position);
				object = object->next;
			}
			region = region->next;
		}
		page = page->next;
	}
#endif
}

void eDVBSubtitleParser::subtitle_reset()
{
	while (subtitle_page *page = this->pages)
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

			while (region->region_objects)
			{
				subtitle_region_object *obj = region->region_objects;
				region->region_objects = obj->next;
				delete obj;
			}

			if (region->region_buffer)
			{
				if (region->region_buffer->surface)
					delete region->region_buffer->surface;
				region->region_buffer=0;
			}

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

		this->pages = page->next;
		delete page;
	}
}

void eDVBSubtitleParser::subtitle_redraw(int page_id)
{
	subtitle_page *page = this->pages;

	//eDebug("displaying page id %d", page_id);

	while (page)
	{
		if (page->page_id == page_id)
			break;
		page = page->next;
	}
	if (!page)
	{
		//eDebug("page not found");
		return;
	}

	//eDebug("iterating regions..");
		/* iterate all regions in this pcs */
	subtitle_page_region *region = page->page_regions;

	eDVBSubtitlePage Page;
	Page.m_show_time = show_time;
	for (; region; region=region->next)
	{
//		eDebug("region %d", region->region_id);
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
//			eDebug("copy region %d to %d, %d", region->region_id, region->region_horizontal_address, region->region_vertical_address);

			int x0 = region->region_horizontal_address;
			int y0 = region->region_vertical_address;
			int x1 = x0 + reg->region_width;
			int y1 = y0 + reg->region_height;

			if ((x0 < 0) || (y0 < 0))
			{
//				eDebug("x0 %d, y0 %d",
//					x0, y0);
				continue;
			}

			/* find corresponding clut */
			subtitle_clut *clut = page->cluts;
			while (clut)
			{
			//eDebug("have %d, want %d", clut->clut_id, main_clut_id);
				if (clut->clut_id == reg->clut_id)
					break;
				clut = clut->next;
			}

			int clut_size = reg->region_buffer->surface->clut.colors = reg->region_depth == subtitle_region::bpp2 ?
				4 : reg->region_depth == subtitle_region::bpp4 ? 16 : 256;

			if (reg->region_buffer->surface->clut.data &&
				clut_size != reg->region_buffer->surface->clut.colors)
			{
				delete [] reg->region_buffer->surface->clut.data;
				reg->region_buffer->surface->clut.data = 0;
			}

			if (!reg->region_buffer->surface->clut.data)
				reg->region_buffer->surface->clut.data = new gRGB[clut_size];

			gRGB *palette = reg->region_buffer->surface->clut.data;

			subtitle_clut_entry *entries=0;
			switch(reg->region_depth)
			{
				case subtitle_region::bpp2:
//					eDebug("2BPP");
					entries = clut->entries_2bit;
					memset(palette, 0, 4*sizeof(gRGB));
					palette[0].a = 0xFF;
					palette[2].r = palette[2].g = palette[2].b = 0xFF;
					palette[3].r = palette[3].g = palette[3].b = 0x80;
					break;
				case subtitle_region::bpp4:
//					eDebug("4BPP");
					entries = clut->entries_4bit;
					memset(palette, 0, 16*sizeof(gRGB));
					for (int i=0; i < 16; ++i)
					{
						if (!i)
							palette[i].a = 0xFF;
						else if (i & 1)
						{
							if (i & 8)
								palette[i].r = 0x80;
							if (i & 4)
								palette[i].g = 0x80;
							if (i & 2)
								palette[i].b = 0x80;
						}
						else
						{
							if (i & 8)
								palette[i].r = 0xFF;
							if (i & 4)
								palette[i].g = 0xFF;
							if (i & 2)
								palette[i].b = 0xFF;
						}
					}
					break;
				case subtitle_region::bpp8:
//					eDebug("8BPP");
					entries = clut->entries_8bit;
					memset(palette, 0, 16*sizeof(gRGB));
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

			if (clut)
			{
				for (int i=0; i<clut_size; ++i)
				{
					if (entries[i].valid)
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
							palette[i].b = MAX(MIN(((298 * y + 543 * cb           ) / 256), 255), 0);
							palette[i].a = (entries[i].T) & 0xFF;
//							eDebug("override clut entry %d RGBA %02x%02x%02x%02x", i,
//								palette[i].r, palette[i].g, palette[i].b, palette[i].a);
						}
						else
						{
//							eDebug("mist %d", i);
							palette[i].r = 0;
							palette[i].g = 0;
							palette[i].b = 0;
							palette[i].a = 0xFF;
						}
					}
				}
			}
			
			eDVBSubtitleRegion Region;
			Region.m_pixmap = reg->region_buffer;
			Region.m_position.setX(x0);
			Region.m_position.setY(y0);
			Page.m_regions.push_back(Region);
		}
		else
			eDebug("region not found");
	}
	m_new_subtitle_page(Page);
	Page.m_regions.clear();
//	eDebug("page timeout is %d", page->page_time_out);
//	Page.m_show_time += (page->page_time_out * 90000);
//	m_new_subtitle_page(Page);
	//eDebug("schon gut.");
}

DEFINE_REF(eDVBSubtitleParser);

eDVBSubtitleParser::eDVBSubtitleParser(iDVBDemux *demux)
	:pages(0)
{
	setStreamID(0xBD);

	if (demux->createPESReader(eApp, m_pes_reader))
		eDebug("failed to create dvb subtitle PES reader!");
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
		eDebug("disable dvb subtitles");
		return m_pes_reader->stop();
	}
	return -1;
}

int eDVBSubtitleParser::start(int pid)
{
	if (m_pes_reader)
	{
		eDebug("start dvb subtitles on pid 0x%04x", pid);
		return m_pes_reader->start(pid);
	}
	return -1;
}

void eDVBSubtitleParser::connectNewPage(const Slot1<void, const eDVBSubtitlePage&> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_new_subtitle_page.connect(slot));
}
