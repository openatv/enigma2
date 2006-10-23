#ifndef __lib_dvb_subtitle_h
#define __lib_dvb_subtitle_h

#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/gdi/gpixmap.h>

typedef unsigned char __u8;

struct subtitle_clut_entry
{
	__u8 Y, Cr, Cb, T;
};

struct subtitle_clut
{
	unsigned char clut_id;
	unsigned char size_2, size_4, size_8;
	unsigned char CLUT_version_number;
	struct subtitle_clut_entry entries_2bit[4];
	struct subtitle_clut_entry entries_4bit[16];
	struct subtitle_clut_entry entries_8bit[256];
	struct subtitle_clut *next;
};

struct subtitle_page_region
{
	int region_id;
	int region_horizontal_address;
	int region_vertical_address;
	struct subtitle_page_region *next;
};

struct subtitle_region_object
{
	int object_id;
	int object_type;
	int object_provider_flag;
	
	int object_horizontal_position;
	int object_vertical_position;
	
		// not supported right now...
	int foreground_pixel_value;
	int background_pixel_value;

	struct subtitle_region_object *next;
};

struct subtitle_region
{
	int region_id;
	int region_version_number;
	int region_height, region_width;
	enum depth { bpp2=1, bpp4=2, bpp8=3 } region_depth;
	ePtr<gPixmap> region_buffer;
	
	int clut_id;
	
	struct subtitle_region_object *region_objects;
	
	struct subtitle_region *next;
};

struct subtitle_page
{
	int page_id;
	time_t page_time_out;
	int page_version_number;
	int pcs_size;
	struct subtitle_page_region *page_regions;
	
	struct subtitle_region *regions;

	struct subtitle_clut *cluts;

	struct subtitle_page *next;
};

struct bitstream
{
	__u8 *data;
	int size;
	int avail;
	int consumed;
};

struct eDVBSubtitleRegion
{
	pts_t show_time;
	int timeout;
	ePtr<gPixmap> region;
};

class eDVBSubtitleParser
	:public iObject, public ePESParser, public Object
{
	DECLARE_REF(eDVBSubtitleParser);
	struct subtitle_page *pages;
	int current_clut_id, current_clut_page_id;
	int screen_width, screen_height;
	int bbox_left, bbox_top, bbox_right, bbox_bottom;
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
	pts_t show_time;
	Signal1<void,const eDVBSubtitleRegion&> m_new_subtitle_region;
public:
	eDVBSubtitleParser(iDVBDemux *demux);
	virtual ~eDVBSubtitleParser();
	int start(int pid);
	void connectNewRegion(const Slot1<void, const eDVBSubtitleRegion&> &slot, ePtr<eConnection> &connection);
private:
	void subtitle_process_line(struct subtitle_page *page, int object_id, int line, __u8 *data, int len);
	int subtitle_process_pixel_data(struct subtitle_page *page, int object_id, int *linenr, int *linep, __u8 *data);
	int subtitle_process_segment(__u8 *segment);
	void subtitle_process_pes(__u8 *buffer, int len);
	void subtitle_clear_screen();
	void subtitle_redraw_all();
	void subtitle_reset();
	void subtitle_redraw(int page_id);
	void processPESPacket(__u8 *pkt, int len) { subtitle_process_pes(pkt, len); }
};

#endif
