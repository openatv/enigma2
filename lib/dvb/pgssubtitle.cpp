#include <algorithm>
#include <cstring>
#include <lib/base/eerror.h>
#include <lib/dvb/pgssubtitle.h>

DEFINE_REF(ePGSSubtitleParser);

ePGSSubtitleParser::ePGSSubtitleParser() {
	clearPalette();
}

/* enigma2 gRGB stores transparency in .a: 0x00 opaque, 0xFF invisible.
   Zeroed entries would render as opaque black boxes, so start fully clear. */
void ePGSSubtitleParser::clearPalette() {
	m_palette.fill(gRGB(0, 0, 0, 0xFF));
}

void ePGSSubtitleParser::reset() {
	m_objects.clear();
	m_composition_objects.clear();
	clearPalette();
	m_palette_id = 0;
	m_composition_state = 0;
	m_display_size = eSize(1920, 1080);
	m_pts = 0;
}

void ePGSSubtitleParser::connectNewPage(const sigc::slot<void(const eDVBSubtitlePage&)>& slot, ePtr<eConnection>& connection) {
	connection = new eConnection(this, m_new_subtitle_page.connect(slot));
}

bool ePGSSubtitleParser::isSegmentType(uint8_t type) {
	return type == PGS_PDS || type == PGS_ODS || type == PGS_PCS || type == PGS_WDS || type == PGS_END;
}

void ePGSSubtitleParser::processBuffer(const uint8_t* data, size_t len, pts_t pts) {
	if (len < 3)
		return;

	m_pts = pts;
	size_t pos = 0;

	/* SUP format prefixes every segment with "PG" + PTS(4) + DTS(4). Some
	   pipelines deliver that instead of bare segments; require a valid segment
	   type behind the header so a raw segment starting with 0x50 is not
	   mistaken for it. */
	bool sup_format = len >= 13 && data[0] == 0x50 && data[1] == 0x47 && isSegmentType(data[10]);

	const size_t header = sup_format ? 13 : 3;

	while (pos + header <= len) {
		if (sup_format && (data[pos] != 0x50 || data[pos + 1] != 0x47)) {
			eWarning("[ePGSSubtitleParser] SUP sync lost at pos %zu", pos);
			return;
		}

		uint8_t segment_type = data[pos + header - 3];
		uint16_t segment_size = (data[pos + header - 2] << 8) | data[pos + header - 1];
		pos += header;

		if (pos + segment_size > len) {
			eWarning("[ePGSSubtitleParser] %ssegment truncated, %zu of %d bytes dropped (type=0x%02x)",
					 sup_format ? "SUP " : "", len - pos, segment_size, segment_type);
			return;
		}

		processSegment(segment_type, data + pos, segment_size);
		pos += segment_size;
	}
}

void ePGSSubtitleParser::processSegment(uint8_t segment_type, const uint8_t* data, int len) {
	switch (segment_type) {
		case PGS_PCS:
			processPCS(data, len);
			break;
		case PGS_PDS:
			processPDS(data, len);
			break;
		case PGS_ODS:
			processODS(data, len);
			break;
		case PGS_WDS:
			/* Window Definition Segment - position info handled via PCS */
			break;
		case PGS_END:
			processEND();
			break;
		default:
			eTrace("[ePGSSubtitleParser] unknown segment type 0x%02x", segment_type);
			break;
	}
}

void ePGSSubtitleParser::processPCS(const uint8_t* data, int len) {
	if (len < 11)
		return;

	int width = (data[0] << 8) | data[1];
	int height = (data[2] << 8) | data[3];
	/* data[4] = frame rate id, ignored */
	/* data[5..6] = composition number */
	m_composition_state = data[7];
	/* data[8] = palette update flag */
	m_palette_id = data[9];
	int num_objects = data[10];

	/* eSubtitleWidget scales by these, they must not become 0 */
	if (width > 0 && height > 0)
		m_display_size = eSize(width, height);

	eTrace("[ePGSSubtitleParser] PCS: %dx%d state=0x%02x palette=%d objects=%d pts=%lld", width, height, m_composition_state, m_palette_id, num_objects, (long long)m_pts);

	/* epoch start: nothing from the previous epoch stays valid */
	if (m_composition_state == 0x80) {
		m_objects.clear();
		clearPalette();
	}

	m_composition_objects.clear();

	int pos = 11;
	int parsed = 0;
	while (parsed < num_objects && pos + 8 <= len) {
		parsed++;
		PGSCompositionObject comp;
		comp.object_id = (data[pos] << 8) | data[pos + 1];
		comp.window_id = data[pos + 2];
		uint8_t flags = data[pos + 3];
		comp.x = (data[pos + 4] << 8) | data[pos + 5];
		comp.y = (data[pos + 6] << 8) | data[pos + 7];
		comp.cropped = (flags & 0x80) != 0;
		pos += 8;

		if (comp.cropped && pos + 8 <= len) {
			comp.crop_x = (data[pos] << 8) | data[pos + 1];
			comp.crop_y = (data[pos + 2] << 8) | data[pos + 3];
			comp.crop_w = (data[pos + 4] << 8) | data[pos + 5];
			comp.crop_h = (data[pos + 6] << 8) | data[pos + 7];
			pos += 8;
		}

		m_composition_objects.push_back(comp);
	}
}

void ePGSSubtitleParser::processPDS(const uint8_t* data, int len) {
	if (len < 2)
		return;

	if (uint8_t palette_id = data[0]; palette_id != m_palette_id) {
		eTrace("[ePGSSubtitleParser] PDS: palette ID %d does not match current palette ID %d", palette_id, m_palette_id);
		return;
	}

	/* data[0] = palette ID, data[1] = palette version */
	int pos = 2;
	while (pos + 5 <= len) {
		uint8_t index = data[pos];
		uint8_t Y = data[pos + 1];
		uint8_t Cr = data[pos + 2];
		uint8_t Cb = data[pos + 3];
		uint8_t A = data[pos + 4];
		pos += 5;

		/* Convert YCbCr to RGB using the same formula as DVB subtitles */
		int r = 0, g = 0, b = 0;
		if (Y != 0) {
			int y = Y - 16;
			int cr = Cr - 128;
			int cb = Cb - 128;
			r = std::max(0, std::min(255, (298 * y + 460 * cr) / 256));
			g = std::max(0, std::min(255, (298 * y - 55 * cb - 137 * cr) / 256));
			b = std::max(0, std::min(255, (298 * y + 543 * cb) / 256));
		}

		/* PGS alpha is opacity, gRGB .a is transparency */
		m_palette[index] = gRGB(r, g, b, 255 - A);
	}
}

void ePGSSubtitleParser::processODS(const uint8_t* data, int len) {
	if (len < 4)
		return;

	int object_id = (data[0] << 8) | data[1];
	uint8_t seq_flag = data[3];

	if (seq_flag & 0x80) { /* first segment */
		if (len < 11)
			return;
		if (m_objects.size() >= MAX_OBJECTS && !m_objects.contains(object_id)) {
			eTrace("[ePGSSubtitleParser] ODS: too many objects, ignoring %d", object_id);
			return;
		}
		PGSObject& obj = m_objects[object_id];
		obj.width = (data[7] << 8) | data[8];
		obj.height = (data[9] << 8) | data[10];
		obj.rle_data.clear();
		obj.overflow = false;
		obj.complete = (seq_flag & 0x40) != 0;
		obj.rle_data.insert(obj.rle_data.end(), data + 11, data + len);
		if (obj.complete)
			eTrace("[ePGSSubtitleParser] ODS: object %d complete %dx%d rle=%zd bytes", object_id, obj.width, obj.height, obj.rle_data.size());
	} else { /* continuation segment */
		auto it = m_objects.find(object_id);
		if (it == m_objects.end() || it->second.width == 0) {
			eTrace("[ePGSSubtitleParser] ODS: continuation for object %d without valid first segment", object_id);
			return;
		}
		PGSObject& obj = it->second;
		if (obj.rle_data.size() + (len - 4) > MAX_OBJECT_RLE) {
			if (!obj.overflow) {
				eWarning("[ePGSSubtitleParser] ODS: object %d exceeds %zu bytes, dropping", object_id, MAX_OBJECT_RLE);
				obj.overflow = true;
				obj.rle_data.clear();
				obj.complete = false;
			}
			return;
		}
		obj.rle_data.insert(obj.rle_data.end(), data + 4, data + len);
		if (seq_flag & 0x40) {
			obj.complete = true;
			eTrace("[ePGSSubtitleParser] ODS: object %d complete %dx%d rle=%zd bytes", object_id, obj.width, obj.height, obj.rle_data.size());
		}
	}
}

void ePGSSubtitleParser::emitPage(std::list<eDVBSubtitleRegion>&& regions) const {
	eDVBSubtitlePage page;
	page.m_show_time = m_pts;
	page.m_display_size = m_display_size;
	page.m_regions = std::move(regions);
	m_new_subtitle_page(page);
}

void ePGSSubtitleParser::processEND() {
	if (m_composition_objects.empty()) {
		/* empty composition = clear the display */
		eTrace("[ePGSSubtitleParser] END: clear screen");
		emitPage({});
		return;
	}

	std::list<eDVBSubtitleRegion> regions;

	for (const auto& comp : m_composition_objects) {
		auto it = m_objects.find(comp.object_id);
		if (it == m_objects.end() || !it->second.complete) {
			eTrace("[ePGSSubtitleParser] END: object %d not found or incomplete", comp.object_id);
			continue;
		}

		const PGSObject& obj = it->second;
		ePtr<gPixmap> pixmap;

		if (!decodeRLE(obj, pixmap)) {
			eTrace("[ePGSSubtitleParser] END: RLE decode failed for object %d (%dx%d)", comp.object_id, obj.width, obj.height);
			continue;
		}

		eDVBSubtitleRegion region;
		region.m_pixmap = pixmap;
		region.m_position = ePoint(comp.x, comp.y);
		regions.push_back(region);
	}

	eTrace("[ePGSSubtitleParser] END: %zd regions, show_time=%lld", regions.size(), (long long)m_pts);

	/* an empty result still has to reach the widget, otherwise the previous
	   subtitle stays on screen until its hide timer expires */
	emitPage(std::move(regions));
}

bool ePGSSubtitleParser::decodeRLE(const PGSObject& obj, ePtr<gPixmap>& pixmap) const {
	if (obj.width <= 0 || obj.height <= 0 || obj.width > 3840 || obj.height > 2160)
		return false;

	pixmap = new gPixmap(eSize(obj.width, obj.height), 8, 1);
	memset(pixmap->surface->data, 0, obj.height * pixmap->surface->stride);

	/* Set up the 256-entry palette on the pixmap */
	pixmap->surface->clut.colors = 256;
	pixmap->surface->clut.data = new gRGB[256]; //NOSONAR
	memcpy(static_cast<void*>(pixmap->surface->clut.data), m_palette.data(), m_palette.size() * sizeof(gRGB));

	const uint8_t* rle = obj.rle_data.data();
	size_t rle_size = obj.rle_data.size();
	size_t pos = 0;
	int x = 0, y = 0;

	while (pos < rle_size && y < obj.height) {
		uint8_t* line = (uint8_t*)pixmap->surface->data + y * pixmap->surface->stride;

		uint8_t byte = rle[pos++];

		if (byte != 0) {
			/* Single pixel with palette index */
			if (x < obj.width)
				line[x] = byte;
			x++;
			continue;
		}

		int run_length = 0;
		uint8_t color = 0;
		bool end_of_line = false;

		if (!readRun(rle, rle_size, pos, run_length, color, end_of_line))
			break;

		if (end_of_line) {
			x = 0;
			y++;
			continue;
		}

		/* Fill run */
		int end = std::min(x + run_length, obj.width);
		while (x < end)
			line[x++] = color;
	}

	return true;
}

bool ePGSSubtitleParser::readRun(const uint8_t* rle, size_t rle_size, size_t& pos, int& run_length, uint8_t& color, bool& end_of_line) {
	if (pos >= rle_size)
		return false;

	uint8_t flags = rle[pos++];

	if (flags == 0) {
		end_of_line = true;
		return true;
	}

	if (flags & 0x40) { /* long run length */
		if (pos >= rle_size)
			return false;
		run_length = ((flags & 0x3F) << 8) | rle[pos++];
	} else { /* short run length */
		run_length = flags & 0x3F;
	}

	if (flags & 0x80) { /* non-zero color */
		if (pos >= rle_size)
			return false;
		color = rle[pos++];
	}

	return true;
}
