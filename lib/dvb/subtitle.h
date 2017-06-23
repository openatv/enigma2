#ifndef __lib_dvb_subtitle_h
#define __lib_dvb_subtitle_h

#include <stdint.h>
#include <lib/base/object.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/pesparse.h>
#include <lib/gdi/gpixmap.h>

struct subtitle_clut_entry
{
	uint8_t Y, Cr, Cb, T;
	uint8_t valid;
};

struct subtitle_clut
{
	unsigned char clut_id;
	unsigned char CLUT_version_number;
	subtitle_clut_entry entries_2bit[4];
	subtitle_clut_entry entries_4bit[16];
	subtitle_clut_entry entries_8bit[256];
	subtitle_clut *next;
};

struct subtitle_page_region
{
	int region_id;
	int region_horizontal_address;
	int region_vertical_address;
	subtitle_page_region *next;
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

	subtitle_region_object *next;
};

struct subtitle_region
{
	int region_id;
	int version_number;
	int height, width;
	enum tDepth { bpp2=1, bpp4=2, bpp8=3 } depth;

	ePtr<gPixmap> buffer;

	int clut_id;

	subtitle_region_object *objects;

	subtitle_region *next;

	bool committed;
};

struct subtitle_page
{
	int page_id;
	time_t page_time_out;
	int page_version_number;
	int state;
	int pcs_size;
	subtitle_page_region *page_regions;

	subtitle_region *regions;

	subtitle_clut *cluts;

	subtitle_page *next;
};

struct bitstream
{
	uint8_t *data;
	int size;
	int avail;
	int consumed;
};

struct eDVBSubtitleRegion
{
	ePtr<gPixmap> m_pixmap;
	ePoint m_position;
	eDVBSubtitleRegion &operator=(const eDVBSubtitleRegion &s)
	{
		m_pixmap = s.m_pixmap;
		m_position = s.m_position;
		return *this;
	}
};

struct eDVBSubtitlePage
{
	std::list<eDVBSubtitleRegion> m_regions;
	pts_t m_show_time;
	eSize m_display_size;
};

class eDVBSubtitleParser
	:public iObject, public ePESParser, public sigc::trackable
{
	DECLARE_REF(eDVBSubtitleParser);
	subtitle_page *m_pages;
	ePtr<iDVBPESReader> m_pes_reader;
	ePtr<eConnection> m_read_connection;
	pts_t m_show_time;
	sigc::signal1<void,const eDVBSubtitlePage&> m_new_subtitle_page;
	int m_composition_page_id, m_ancillary_page_id;
	bool m_seen_eod;
	eSize m_display_size;
public:
	eDVBSubtitleParser(iDVBDemux *demux);
	virtual ~eDVBSubtitleParser();
	int start(int pid, int composition_page_id, int ancillary_page_id);
	int stop();
	void connectNewPage(const sigc::slot1<void, const eDVBSubtitlePage&> &slot, ePtr<eConnection> &connection);
private:
	void subtitle_process_line(subtitle_region *region, subtitle_region_object *object, int line, uint8_t *data, int len);
	int subtitle_process_pixel_data(subtitle_region *region, subtitle_region_object *object, int *linenr, int *linep, uint8_t *data);
	int subtitle_process_segment(uint8_t *segment);
	void subtitle_process_pes(uint8_t *buffer, int len);
	void subtitle_redraw_all();
	void subtitle_reset();
	void subtitle_redraw(int page_id);
	void processPESPacket(uint8_t *pkt, int len) { subtitle_process_pes(pkt, len); }
};

#endif
