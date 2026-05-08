#ifndef __lib_dvb_pgssubtitle_h
#define __lib_dvb_pgssubtitle_h

#include <lib/base/object.h>
#include <lib/dvb/subtitle.h>
#include <lib/gdi/gpixmap.h>
#include <sigc++/sigc++.h>
#include <vector>
#include <map>

class ePGSSubtitleParser : public iObject, public sigc::trackable
{
	DECLARE_REF(ePGSSubtitleParser);
public:
	ePGSSubtitleParser();
	virtual ~ePGSSubtitleParser();

	void processBuffer(uint8_t *data, size_t len, pts_t pts);
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

	struct PGSCompositionObject
	{
		int object_id;
		int window_id;
		int x, y;
		bool cropped;
		int crop_x, crop_y, crop_w, crop_h;
	};

	struct PGSObject
	{
		int width, height;
		std::vector<uint8_t> rle_data;
		bool complete;
		PGSObject() : width(0), height(0), complete(false) {}
	};

	eSize m_display_size;
	gRGB m_palette[256];
	int m_palette_id;
	std::map<int, PGSObject> m_objects;
	std::vector<PGSCompositionObject> m_composition_objects;
	int m_composition_state;
	pts_t m_pts;

	sigc::signal<void(const eDVBSubtitlePage&)> m_new_subtitle_page;

	void processSegment(uint8_t segment_type, const uint8_t *data, int len);
	void processPCS(const uint8_t *data, int len);
	void processPDS(const uint8_t *data, int len);
	void processODS(const uint8_t *data, int len);
	void processEND();

	bool decodeRLE(const PGSObject &obj, ePtr<gPixmap> &pixmap);
};

#endif
