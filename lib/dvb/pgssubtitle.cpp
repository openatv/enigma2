#include <lib/dvb/pgssubtitle.h>
#include <lib/base/eerror.h>
#include <algorithm>
#include <cstring>

DEFINE_REF(ePGSSubtitleParser);

ePGSSubtitleParser::ePGSSubtitleParser()
	: m_display_size(1920, 1080), m_palette_id(0), m_composition_state(0), m_pts(0)
{
	memset(static_cast<void*>(m_palette), 0, sizeof(m_palette));
}

ePGSSubtitleParser::~ePGSSubtitleParser()
{
}

void ePGSSubtitleParser::reset()
{
	m_objects.clear();
	m_composition_objects.clear();
	memset(static_cast<void*>(m_palette), 0, sizeof(m_palette));
	m_composition_state = 0;
}

void ePGSSubtitleParser::connectNewPage(const sigc::slot<void(const eDVBSubtitlePage&)> &slot, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_new_subtitle_page.connect(slot));
}

void ePGSSubtitleParser::processBuffer(uint8_t *data, size_t len, pts_t pts)
{
	if (len < 3)
		return;

	m_pts = pts;
	size_t pos = 0;

	/*
	 * Detect SUP format: segments prefixed with "PG" magic + PTS + DTS (10 bytes).
	 * Some GStreamer pipelines may deliver PGS data in SUP format instead of raw segments.
	 */
	bool sup_format = (len >= 13 && data[0] == 0x50 && data[1] == 0x47);

	if (sup_format)
	{
		/* SUP format: each segment has a 10-byte header before the segment type */
		while (pos + 13 <= len)
		{
			if (data[pos] != 0x50 || data[pos + 1] != 0x47)
			{
				eDebug("[ePGSSubtitleParser] SUP sync lost at pos %zd", pos);
				break;
			}

			/* Skip PG(2) + PTS(4) + DTS(4) = 10 bytes header */
			uint8_t segment_type = data[pos + 10];
			uint16_t segment_size = (data[pos + 11] << 8) | data[pos + 12];
			pos += 13;

			if (pos + segment_size > len)
				break;

			processSegment(segment_type, data + pos, segment_size);
			pos += segment_size;
		}
	}
	else
	{
		/* Raw PGS format: segments start directly with type byte */
		while (pos + 3 <= len)
		{
			uint8_t segment_type = data[pos];
			uint16_t segment_size = (data[pos + 1] << 8) | data[pos + 2];
			pos += 3;

			if (pos + segment_size > len)
			{
				eDebug("[ePGSSubtitleParser] segment overflows buffer (type=0x%02x, size=%d, remaining=%zd)",
					segment_type, segment_size, len - pos);
				break;
			}

			processSegment(segment_type, data + pos, segment_size);
			pos += segment_size;
		}
	}
}

void ePGSSubtitleParser::processSegment(uint8_t segment_type, const uint8_t *data, int len)
{
	switch (segment_type)
	{
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
		eDebug("[ePGSSubtitleParser] unknown segment type 0x%02x", segment_type);
		break;
	}
}

void ePGSSubtitleParser::processPCS(const uint8_t *data, int len)
{
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

	m_display_size = eSize(width, height);

	eDebug("[ePGSSubtitleParser] PCS: %dx%d state=0x%02x palette=%d objects=%d pts=%lld",
		width, height, m_composition_state, m_palette_id, num_objects, (long long)m_pts);

	/* Epoch start: clear all cached objects */
	if (m_composition_state == 0x80)
	{
		m_objects.clear();
	}

	m_composition_objects.clear();

	int pos = 11;
	for (int i = 0; i < num_objects && pos + 8 <= len; i++)
	{
		PGSCompositionObject comp;
		comp.object_id = (data[pos] << 8) | data[pos + 1];
		comp.window_id = data[pos + 2];
		uint8_t flags = data[pos + 3];
		comp.x = (data[pos + 4] << 8) | data[pos + 5];
		comp.y = (data[pos + 6] << 8) | data[pos + 7];
		comp.cropped = (flags & 0x80) != 0;
		comp.crop_x = comp.crop_y = comp.crop_w = comp.crop_h = 0;
		pos += 8;

		if (comp.cropped && pos + 8 <= len)
		{
			comp.crop_x = (data[pos] << 8) | data[pos + 1];
			comp.crop_y = (data[pos + 2] << 8) | data[pos + 3];
			comp.crop_w = (data[pos + 4] << 8) | data[pos + 5];
			comp.crop_h = (data[pos + 6] << 8) | data[pos + 7];
			pos += 8;
		}

		m_composition_objects.push_back(comp);
	}
}

void ePGSSubtitleParser::processPDS(const uint8_t *data, int len)
{
	if (len < 2)
		return;

	/* data[0] = palette ID, data[1] = palette version */
	int pos = 2;
	while (pos + 5 <= len)
	{
		uint8_t index = data[pos];
		uint8_t Y  = data[pos + 1];
		uint8_t Cr = data[pos + 2];
		uint8_t Cb = data[pos + 3];
		uint8_t A  = data[pos + 4];
		pos += 5;

		/* Convert YCbCr to RGB using the same formula as DVB subtitles */
		int r, g, b;
		if (Y == 0)
		{
			r = g = b = 0;
		}
		else
		{
			int y = Y - 16;
			int cr = Cr - 128;
			int cb = Cb - 128;
			r = std::max(0, std::min(255, (298 * y + 460 * cr) / 256));
			g = std::max(0, std::min(255, (298 * y - 55 * cb - 137 * cr) / 256));
			b = std::max(0, std::min(255, (298 * y + 543 * cb) / 256));
		}

		/*
		 * enigma2 gRGB alpha convention: 0xFF = transparent, 0x00 = opaque
		 * PGS alpha convention: 0xFF = opaque, 0x00 = transparent
		 */
		m_palette[index] = gRGB(r, g, b, 255 - A);
	}
}

void ePGSSubtitleParser::processODS(const uint8_t *data, int len)
{
	if (len < 4)
		return;

	int object_id = (data[0] << 8) | data[1];
	/* data[2] = version number */
	uint8_t seq_flag = data[3];

	PGSObject &obj = m_objects[object_id];

	if (seq_flag & 0x80) /* first segment */
	{
		if (len < 11)
			return;
		/* data[4..6] = object data length (3 bytes) */
		obj.width = (data[7] << 8) | data[8];
		obj.height = (data[9] << 8) | data[10];
		obj.rle_data.clear();
		obj.complete = false;
		obj.rle_data.insert(obj.rle_data.end(), data + 11, data + len);
	}
	else /* continuation segment */
	{
		obj.rle_data.insert(obj.rle_data.end(), data + 4, data + len);
	}

	if (seq_flag & 0x40) /* last segment */
	{
		obj.complete = true;
		eDebug("[ePGSSubtitleParser] ODS: object %d complete %dx%d rle=%zd bytes",
			object_id, obj.width, obj.height, obj.rle_data.size());
	}
}

void ePGSSubtitleParser::processEND()
{
	if (m_composition_objects.empty())
	{
		/* Empty composition = clear subtitle display */
		eDebug("[ePGSSubtitleParser] END: clear screen");
		eDVBSubtitlePage page;
		page.m_show_time = m_pts;
		page.m_display_size = m_display_size;
		m_new_subtitle_page(page);
		return;
	}

	eDVBSubtitlePage page;
	page.m_show_time = m_pts;
	page.m_display_size = m_display_size;

	for (const auto &comp : m_composition_objects)
	{
		auto it = m_objects.find(comp.object_id);
		if (it == m_objects.end() || !it->second.complete)
		{
			eDebug("[ePGSSubtitleParser] END: object %d not found or incomplete", comp.object_id);
			continue;
		}

		const PGSObject &obj = it->second;
		ePtr<gPixmap> pixmap;

		if (!decodeRLE(obj, pixmap))
		{
			eDebug("[ePGSSubtitleParser] END: RLE decode failed for object %d (%dx%d)",
				comp.object_id, obj.width, obj.height);
			continue;
		}

		eDVBSubtitleRegion region;
		region.m_pixmap = pixmap;
		region.m_position = ePoint(comp.x, comp.y);
		page.m_regions.push_back(region);
	}

	eDebug("[ePGSSubtitleParser] END: %zd regions, show_time=%lld",
		page.m_regions.size(), (long long)m_pts);

	if (!page.m_regions.empty())
	{
		m_new_subtitle_page(page);
	}
}

bool ePGSSubtitleParser::decodeRLE(const PGSObject &obj, ePtr<gPixmap> &pixmap)
{
	if (obj.width <= 0 || obj.height <= 0 || obj.width > 3840 || obj.height > 2160)
		return false;

	pixmap = new gPixmap(eSize(obj.width, obj.height), 8, 1);
	memset(pixmap->surface->data, 0, obj.height * pixmap->surface->stride);

	/* Set up the 256-entry palette on the pixmap */
	pixmap->surface->clut.colors = 256;
	pixmap->surface->clut.data = new gRGB[256];
	memcpy(static_cast<void*>(pixmap->surface->clut.data), m_palette, 256 * sizeof(gRGB));

	const uint8_t *rle = obj.rle_data.data();
	size_t rle_size = obj.rle_data.size();
	size_t pos = 0;
	int x = 0, y = 0;

	while (pos < rle_size && y < obj.height)
	{
		uint8_t *line = (uint8_t *)pixmap->surface->data + y * pixmap->surface->stride;

		uint8_t byte = rle[pos++];

		if (byte != 0)
		{
			/* Single pixel with palette index */
			if (x < obj.width)
				line[x] = byte;
			x++;
		}
		else
		{
			/* Control byte follows */
			if (pos >= rle_size)
				break;

			uint8_t flags = rle[pos++];

			if (flags == 0)
			{
				/* End of line */
				x = 0;
				y++;
				continue;
			}

			int run_length;
			uint8_t color;

			if (flags & 0x40) /* long run length */
			{
				if (pos >= rle_size)
					break;
				run_length = ((flags & 0x3F) << 8) | rle[pos++];
			}
			else /* short run length */
			{
				run_length = flags & 0x3F;
			}

			if (flags & 0x80) /* non-zero color */
			{
				if (pos >= rle_size)
					break;
				color = rle[pos++];
			}
			else
			{
				color = 0;
			}

			/* Fill run */
			int end = std::min(x + run_length, obj.width);
			while (x < end)
				line[x++] = color;
		}
	}

	return true;
}
