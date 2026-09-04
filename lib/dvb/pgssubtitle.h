#ifndef __lib_dvb_pgssubtitle_h
#define __lib_dvb_pgssubtitle_h

#include <lib/base/object.h>
#include <lib/dvb/subtitle.h>
#include <lib/gdi/gpixmap.h>
#include <sigc++/sigc++.h>
#include <array>
#include <map>
#include <vector>

class ePGSSubtitleParser : public iObject, public sigc::trackable
{
	DECLARE_REF(ePGSSubtitleParser);
public:
	ePGSSubtitleParser();
	virtual ~ePGSSubtitleParser() = default;

	/* pts in ms, same unit as eDVBSubtitleParser::processBuffer() */
	void processBuffer(const uint8_t *data, size_t len, pts_t pts);
	void reset();
	void connectNewPage(const sigc::slot<void(const eDVBSubtitlePage&)> &slot, ePtr<eConnection> &connection);

private:
	/* PGS segment types */
	enum {
		PGS_PDS = 0x14,  /* Palette Definition Segment */
		PGS_ODS = 0x15,  /* Object Definition Segment */
		PGS_PCS = 0x16,  /* Presentation Composition Segment */
		PGS_WDS = 0x17,  /* Window Definition Segment */
		PGS_END = 0x80,  /* End of Display Set */
	};

	/* a 1920x1080 8bpp object is ~2MB uncompressed; refuse anything beyond that
	   so a broken stream cannot grow rle_data without bound */
	static constexpr size_t MAX_OBJECT_RLE = 4 * 1024 * 1024;
	static constexpr size_t MAX_OBJECTS = 64;

	struct PGSCompositionObject
	{
		int object_id = 0;
		int window_id = 0;
		int x = 0, y = 0;
		bool cropped = false;
		int crop_x = 0, crop_y = 0, crop_w = 0, crop_h = 0;
	};

	struct PGSObject
	{
		int width = 0;
		int height = 0;
		std::vector<uint8_t> rle_data;
		bool complete = false;
		bool overflow = false;
	};

	eSize m_display_size{1920, 1080};
	std::array<gRGB, 256> m_palette;
	int m_palette_id = 0;
	std::map<int, PGSObject> m_objects;
	std::vector<PGSCompositionObject> m_composition_objects;
	int m_composition_state = 0;
	pts_t m_pts = 0;

	sigc::signal<void(const eDVBSubtitlePage&)> m_new_subtitle_page;

	void processSegment(uint8_t segment_type, const uint8_t *data, int len);
	void processPCS(const uint8_t *data, int len);
	void processPDS(const uint8_t *data, int len);
	void processODS(const uint8_t *data, int len);
	void processEND();

	void clearPalette();
	void emitPage(std::list<eDVBSubtitleRegion> &&regions) const;
	bool decodeRLE(const PGSObject &obj, ePtr<gPixmap> &pixmap) const;
	static bool isSegmentType(uint8_t type);
	static bool readRun(const uint8_t *rle, size_t rle_size, size_t &pos, int &run_length, uint8_t &color, bool &end_of_line);
};

#endif
