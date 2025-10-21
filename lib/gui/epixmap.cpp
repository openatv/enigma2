/*

AniGif of ePixmap

Copyright (c) 2025 jbleyel

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.
*/


#include <lib/base/wrappers.h>
#include <lib/gui/epixmap.h>
#include <lib/gdi/epng.h>
#include <lib/gui/ewidgetdesktop.h>

extern "C" {
#include <gif_lib.h>
}

ePixmap::ePixmap(eWidget *parent)
	: eWidget(parent), m_alphatest(0), m_scale(0), m_animTimer(eTimer::create(eApp))
{
	CONNECT(m_animTimer->timeout, ePixmap::nextFrame);
}

ePixmap::~ePixmap()
{
    m_animTimer->stop();
    m_frames.clear();
    m_delays.clear();
}

void ePixmap::setAlphatest(int alphatest)
{
	m_alphatest = alphatest;
	setTransparent(alphatest);
}

void ePixmap::setScale(int scale)
{
	// support old python code beacause the old code will only support BT_SCALE
	scale = (scale) ? gPainter::BT_SCALE : 0;

	if (m_scale != scale)
	{
		m_scale = scale;
		invalidate();
	}
}

void ePixmap::setPixmapScale(int flags)
{
	if (m_scale != flags)
	{
		m_scale = flags;
		invalidate();
	}
}

void ePixmap::setPixmap(gPixmap *pixmap)
{
    m_animTimer->stop();
	m_pixmap = pixmap;
	event(evtChangedPixmap);
}

void ePixmap::setPixmap(ePtr<gPixmap> &pixmap)
{
    m_animTimer->stop();
	m_pixmap = pixmap;
	event(evtChangedPixmap);
}

void ePixmap::setPixmapFromFile(const char *filename, bool autoDetect)
{
	//SWIG_VOID(int) loadImage(ePtr<gPixmap> &SWIG_OUTPUT, const char *filename, int accel = 0, int width = 0, int height = 0, int cached = -1, float scale = 0, int keepAspect = 0, int align = 0, bool autoDetect = false);

	loadImage(m_pixmap, filename, m_scale, m_scale ? size().width() : 0, m_scale ? size().height() : 0, -1, 0, 0, 0, autoDetect);

	if (!m_pixmap)
	{
		eDebug("[ePixmap] setPixmapFromFile: load %s failed", filename);
		return;
	}

	// TODO: This only works for desktop 0
	getDesktop(0)->makeCompatiblePixmap(*m_pixmap);
	event(evtChangedPixmap);
}

void ePixmap::checkSize()
{
	/* when we have no pixmap, or a pixmap of different size, we need
	   to enable transparency in any case. */
	if (m_pixmap && m_pixmap->size() == size() && !m_alphatest)
		setTransparent(0);
	else
		setTransparent(1);
	/* fall trough. */
}

int ePixmap::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;

		eSize s(size());
		getStyle(style);

		//	we don't clear the background before because of performance reasons.
		//	when the pixmap is too small to fit the whole widget area, the widget is
		//	transparent anyway, so the background is already painted.
		//		eWidget::event(event, data, data2);

		gPainter &painter = *(gPainter *)data2;
		int cornerRadius = getCornerRadius();
		if (m_pixmap)
		{
			int flags = 0;
			if (m_alphatest == 1)
				flags = gPainter::BT_ALPHATEST;
			else if (m_alphatest == 2)
				flags = gPainter::BT_ALPHABLEND;

			flags |= m_scale;
			painter.setRadius(cornerRadius, getCornerRadiusEdges());
			painter.blit(m_pixmap, eRect(ePoint(0, 0), s), eRect(), flags);
		}

		if(cornerRadius)
			return 0; // border not suppored for rounded edges

		if (m_have_border_color)
			painter.setForegroundColor(m_border_color);

		if (m_border_width)
		{
			painter.fill(eRect(0, 0, s.width(), m_border_width));
			painter.fill(eRect(0, m_border_width, m_border_width, s.height() - m_border_width));
			painter.fill(eRect(m_border_width, s.height() - m_border_width, s.width() - m_border_width, m_border_width));
			painter.fill(eRect(s.width() - m_border_width, m_border_width, m_border_width, s.height() - m_border_width));
		}
		return 0;
	}
	case evtChangedPixmap:
		checkSize();
		invalidate();
		return 0;
	case evtChangedSize:
		checkSize();
		[[fallthrough]];
	default:
		return eWidget::event(event, data, data2);
	}
}

void ePixmap::setAniPixmapFromFile(const char* filename, bool autostart) {
	std::vector<ePtr<gPixmap>> frames;
	std::vector<int> delays;

	int error = 0;
	GifFileType* gif = DGifOpenFileName(filename, &error);
	if (!gif)
		return;

	int width = gif->SWidth;
	int height = gif->SHeight;
	const ColorMapObject* globalColorMap = gif->SColorMap;

	GifRecordType recordType;
	int delay = 100; // default delay (ms)

	// GCE state (applies only to next image)
	int disposal = 0;
	int transparentIndex = -1;
	bool has_transparency = false;

	// Canvas holds 32-bit pixels
	std::vector<uint32_t> canvas(width * height, 0x00000000u); // temporary transparent
	std::vector<uint32_t> prevCanvas = canvas; // for disposal=3


	// Convert background color to 32-bit format (B | G<<8 | R<<16 | A<<24)
	uint32_t bgColor = m_have_background_color
						   ? (uint32_t(m_background_color.b)) | (uint32_t(m_background_color.g) << 8) | (uint32_t(m_background_color.r) << 16) | (uint32_t(255 - m_background_color.a) << 24)
						   : 0x00000000u;

	// Read GIF records
	do {
		if (DGifGetRecordType(gif, &recordType) == GIF_ERROR)
			break;

		switch (recordType) {
			case EXTENSION_RECORD_TYPE: {
				int extCode;
				GifByteType* extension = nullptr;
				if (DGifGetExtension(gif, &extCode, &extension) == GIF_ERROR)
					break;

				if (extCode == GRAPHICS_EXT_FUNC_CODE && extension != nullptr) {
					int blockSize = extension[0];
					if (blockSize >= 4) {
						unsigned char packed = extension[1];
						int delay_cs = extension[2] | (extension[3] << 8); // in 1/100s
						int local_transparent = (packed & 0x01) ? extension[4] : -1;

						disposal = (packed >> 2) & 0x07;
						has_transparency = (packed & 0x01) != 0;
						transparentIndex = local_transparent;
						delay = (delay_cs > 0) ? (delay_cs * 10) : 100; // ms
					}
				}

				// consume remaining extension sub-blocks
				while (extension != nullptr) {
					if (DGifGetExtensionNext(gif, &extension) == GIF_ERROR)
						break;
				}
				break;
			}

			case IMAGE_DESC_RECORD_TYPE: {
				if (DGifGetImageDesc(gif) == GIF_ERROR)
					break;

				int left = gif->Image.Left;
				int top = gif->Image.Top;
				int fw = gif->Image.Width;
				int fh = gif->Image.Height;

				// Backup canvas for disposal=3
				if (disposal == 3)
					prevCanvas = canvas;

				// Apply disposal method
				if (disposal == 2) {
					// Fill the image rect with background color
					for (int y = 0; y < fh; ++y) {
						int cy = top + y;
						if (cy < 0 || cy >= height)
							continue;
						for (int x = 0; x < fw; ++x) {
							int cx = left + x;
							if (cx < 0 || cx >= width)
								continue;
							canvas[cy * width + cx] = bgColor;
						}
					}
				} else if (disposal == 3) {
					// Restore previous canvas
					canvas = prevCanvas;
				}
				// disposal 0/1: do nothing

				// choose palette: local or global
				const ColorMapObject* frameColorMap = gif->Image.ColorMap ? gif->Image.ColorMap : globalColorMap;

				// read frame indices, handle interlace
				std::vector<unsigned char> indexBuffer(fw * fh);
				if (gif->Image.Interlace) {
					const int start[] = {0, 4, 2, 1};
					const int step[] = {8, 8, 4, 2};
					for (int p = 0; p < 4; ++p) {
						for (int y = start[p]; y < fh; y += step[p]) {
							if (DGifGetLine(gif, indexBuffer.data() + y * fw, fw) == GIF_ERROR)
								goto after_image_read;
						}
					}
				} else {
					for (int y = 0; y < fh; ++y) {
						if (DGifGetLine(gif, indexBuffer.data() + y * fw, fw) == GIF_ERROR)
							break;
					}
				}
			after_image_read:

				// Composite indices into canvas (skip transparent pixels)
				for (int y = 0; y < fh; ++y) {
					int cy = top + y;
					if (cy < 0 || cy >= height)
						continue;
					for (int x = 0; x < fw; ++x) {
						int cx = left + x;
						if (cx < 0 || cx >= width)
							continue;
						unsigned char idx = indexBuffer[y * fw + x];

						if (has_transparency && (int)idx == transparentIndex) {
							// transparent: leave canvas pixel as-is (bgColor or previous frame)
							continue;
						}
						if (frameColorMap && idx < frameColorMap->ColorCount) {
							GifColorType c = frameColorMap->Colors[idx];
							canvas[cy * width + cx] = (uint32_t(c.Blue)) | (uint32_t(c.Green) << 8) | (uint32_t(c.Red) << 16) | (0xFFu << 24);
						} else {
							canvas[cy * width + cx] = bgColor;
						}
					}
				}

				// create 32-bit gPixmap and copy canvas
				ePtr<gPixmap> pix = new gPixmap(width, height, 32, nullptr, gPixmap::accelAlways);
				uint32_t* pixdata = static_cast<uint32_t*>(pix->surface->data);
				int stride_pixels = pix->surface->stride / 4;
				for (int y = 0; y < height; ++y) {
					for (int x = 0; x < width; ++x) {
						pixdata[y * stride_pixels + x] = canvas[y * width + x];
					}
				}

				frames.push_back(pix);
				delays.push_back(delay);

				// Reset GCE for next frame
				disposal = 0;
				has_transparency = false;
				transparentIndex = -1;
				delay = 100;

				break;
			}

			default:
				break;
		}
	} while (recordType != TERMINATE_RECORD_TYPE);

	DGifCloseFile(gif, &error);

	// assign results
	m_frames = frames;
	m_delays = delays;
	m_currentFrame = 0;

	if (autostart && !m_frames.empty()) {
		m_pixmap = m_frames[0];
		event(evtChangedPixmap);
		if (m_frames.size() > 1)
			startAnimation();
	}
}


void ePixmap::startAnimation(bool once) {
	m_animTimer->stop();
	m_playOnce = once; // remember if we should play only once
	m_currentFrame = 0; // restart from first frame

	if (m_frames.size() > 1 && m_delays.size() == m_frames.size()) {
		// Show the very first frame immediately
		m_pixmap = m_frames[m_currentFrame];
		event(evtChangedPixmap);

		// Start timer for the first frame
		m_animTimer->start(m_delays[m_currentFrame], true);
	}
}

void ePixmap::nextFrame() {
	if (m_frames.empty())
		return;

	// Advance to next frame
	m_currentFrame++;

	if (static_cast<size_t>(m_currentFrame) >= m_frames.size()) {
		if (m_playOnce) {
			// Stop after the last frame when playing once
			m_currentFrame = m_frames.size() - 1; // stay on last frame
			return;
		} else {
			// Loop back to the beginning
			m_currentFrame = 0;
		}
	}

	// Apply the new frame
	m_pixmap = m_frames[m_currentFrame];
	event(evtChangedPixmap);

	// Start timer for this frame
	if (static_cast<size_t>(m_currentFrame) < m_delays.size())
		m_animTimer->start(m_delays[m_currentFrame], true);
}
