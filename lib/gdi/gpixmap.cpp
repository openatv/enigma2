#include <cstdlib>
#include <cstring>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/region.h>
#include <lib/gdi/accel.h>
#include <lib/gdi/drawing.h>
#include <byteswap.h>

#ifndef BYTE_ORDER
#error "no BYTE_ORDER defined!"
#endif

/* surface acceleration threshold: do not attempt to accelerate surfaces smaller than the threshold (measured in bytes) */
#ifndef GFX_SURFACE_ACCELERATION_THRESHOLD
#define GFX_SURFACE_ACCELERATION_THRESHOLD 48000
#endif

/* fill acceleration threshold: do not attempt to accelerate fill operations smaller than the threshold (measured in bytes) */
#ifndef GFX_SURFACE_FILL_ACCELERATION_THRESHOLD
#define GFX_SURFACE_FILL_ACCELERATION_THRESHOLD 80000
#endif

/* blit acceleration threshold: do not attempt to accelerate blit operations smaller than the threshold (measured in bytes) */
#ifndef GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD
/* by default: accelerate all blit operations on accelerated surfaces */
#define GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD 0
#endif

// #define GPIXMAP_DEBUG

#ifdef GPIXMAP_DEBUG
#	include "../base/benchmark.h"

/* #define GPIXMAP_CHECK_THRESHOLD */

#ifdef GPIXMAP_CHECK_THRESHOLD

static unsigned int acceltime = 0;

static void adjustFillThreshold(unsigned int cputime, int area)
{
	static int currentfillthreshold = GFX_SURFACE_FILL_ACCELERATION_THRESHOLD;
	if (acceltime > cputime)
	{
		if (area > currentfillthreshold)
		{
			eDebug("[gPixmap] [BLITBENCH] increase fill acceleration threshold from %d to %d", currentfillthreshold, area);
			currentfillthreshold = area;
		}
	}
	else if (acceltime < cputime)
	{
		if (area < currentfillthreshold)
		{
			eDebug("[gPixmap] [BLITBENCH] decrease fill acceleration threshold from %d to %d", currentfillthreshold, area);
			currentfillthreshold = area;
		}
	}
}

static void adjustBlitThreshold(unsigned int cputime, int area)
{
	static int currentblitthreshold = GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD;
	if (acceltime > cputime)
	{
		if (area > currentblitthreshold)
		{
			eDebug("[gPixmap] [BLITBENCH] increase blit acceleration threshold from %d to %d", currentblitthreshold, area);
			currentblitthreshold = area;
		}
	}
	else if (acceltime < cputime)
	{
		if (area < currentblitthreshold)
		{
			eDebug("[gPixmap] [BLITBENCH] decrease blit acceleration threshold from %d to %d", currentblitthreshold, area);
			currentblitthreshold = area;
		}
	}
}

#undef GFX_SURFACE_FILL_ACCELERATION_THRESHOLD
#define GFX_SURFACE_FILL_ACCELERATION_THRESHOLD 0
#undef GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD
#define GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD 0

#endif
#endif

#define ALPHA_TEST_MASK 0xFF000000

gLookup::gLookup()
	:size(0), lookup(0)
{
}

gLookup::gLookup(int size, const gPalette &pal, const gRGB &start, const gRGB &end)
	:size(0), lookup(0)
{
	build(size, pal, start, end);
}

void gLookup::build(int _size, const gPalette &pal, const gRGB &start, const gRGB &end)
{
	if (lookup)
	{
		delete [] lookup;
		lookup=0;
		size=0;
	}
	size=_size;
	if (!size)
		return;
	lookup=new gColor[size];

	lookup[0] = pal.findColor(start);

	const int rsize = end.r - start.r;
	const int gsize = end.g - start.g;
	const int bsize = end.b - start.b;
	const int asize = end.a - start.a;
	const int size_1 = size - 1;

	for (int i=1; i<size; i++)
	{
		gRGB col;
		int rdiff = (rsize * i) / size_1;
		int gdiff = (gsize * i) / size_1;
		int bdiff = (bsize * i) / size_1;
		int adiff = (asize * i) / size_1;
		col.r = start.r + rdiff;
		col.g = start.g + gdiff;
		col.b = start.b + bdiff;
		col.a = start.a + adiff;
		lookup[i] = pal.findColor(col);
	}
}

gUnmanagedSurface::gUnmanagedSurface():
	x(0), y(0), bpp(0), bypp(0), stride(0),
	data(0),
	data_phys(0)
{
}

gUnmanagedSurface::gUnmanagedSurface(int width, int height, int _bpp):
	x(width),
	y(height),
	bpp(_bpp),
	data(0),
	data_phys(0)
{
	switch (_bpp)
	{
	case 8:
		bypp = 1;
		break;
	case 15:
	case 16:
		bypp = 2;
		break;
	case 24:		// never use 24bit mode
	case 32:
		bypp = 4;
		break;
	default:
		bypp = (bpp+7)/8;
	}
	stride = x*bypp;
}

#ifdef GPIXMAP_DEBUG
unsigned int pixmap_total_size = 0;
unsigned int pixmap_total_count = 0;
static void added_pixmap(int size)
{
	++pixmap_total_count;
	pixmap_total_size += size;
	eDebug("[gSurface] Added %dk, total %u pixmaps, %uk", size>>10, pixmap_total_count, pixmap_total_size>>10);
}
static void removed_pixmap(int size)
{
	--pixmap_total_count;
	pixmap_total_size -= size;
	eDebug("[gSurface] Removed %dk, total %u pixmaps, %uk", size>>10, pixmap_total_count, pixmap_total_size>>10);
}
#else
static inline void added_pixmap(int size) {}
static inline void removed_pixmap(int size) {}
#endif

static bool is_a_candidate_for_accel(const gUnmanagedSurface* surface)
{
	if (surface->stride < 48)
		return false;
	switch (surface->bpp)
	{
		case 8:
		case 32:
			return (surface->y * surface->stride) >= GFX_SURFACE_ACCELERATION_THRESHOLD;
		default:
			return false;
	}
}

gSurface::gSurface(int width, int height, int _bpp, int accel):
	gUnmanagedSurface(width, height, _bpp)
{
	if ((accel > gPixmap::accelAuto) ||
		((accel == gPixmap::accelAuto) && (is_a_candidate_for_accel(this))))
	{
		if (gAccel::getInstance()->accelAlloc(this) != 0)
				eDebug("[gSurface] ERROR: accelAlloc failed");
	}
	if (!data)
	{
		data = new unsigned char [y * stride];
		added_pixmap(y * stride);
	}
}

gSurface::~gSurface()
{
	gAccel::getInstance()->accelFree(this);
	if (data)
	{
		delete [] (unsigned char*)data;
		removed_pixmap(y * stride);
	}
	if (clut.data)
	{
		delete [] clut.data;
	}
}

void gPixmap::fill(const gRegion &region, const gColor &color)
{
	unsigned int i;
	for (i = 0; i < region.rects.size(); ++i)
	{
		const eRect &area = region.rects[i];
		if (area.empty())
			continue;

		if (surface->bpp == 8)
		{
			for (int y = area.top(); y < area.bottom(); y++)
				memset(((__u8 *)surface->data) + y * surface->stride + area.left(), color.color, area.width());
		}
		else if (surface->bpp == 16)
		{
			uint32_t icol;

			if (surface->clut.data && color < surface->clut.colors)
				icol = surface->clut.data[color].argb();
			else
				icol = 0x10101 * color;
#if BYTE_ORDER == LITTLE_ENDIAN
			uint16_t col = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
			uint16_t col = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
			for (int y = area.top(); y < area.bottom(); y++)
			{
				uint16_t *dst = (uint16_t *)(((uint8_t *)surface->data) + y * surface->stride + area.left() * surface->bypp);
				int x = area.width();
				while (x--)
					*dst++ = col;
			}
		}
		else if (surface->bpp == 32)
		{
			uint32_t col;

			if (surface->clut.data && color < surface->clut.colors)
				col = surface->clut.data[color].argb();
			else
				col = 0x10101 * color;

			col ^= 0xFF000000;

#ifdef GPIXMAP_DEBUG
			Stopwatch s;
#endif
			if (surface->data_phys && ((area.surface() * surface->bypp) > GFX_SURFACE_FILL_ACCELERATION_THRESHOLD))
				if (!gAccel::getInstance()->fill(surface, area, col))
				{
#ifdef GPIXMAP_DEBUG
					s.stop();
					eDebug("[gPixmap] [BLITBENCH] accel fill %dx%d (%d bytes) took %u us", area.width(), area.height(), area.surface() * surface->bypp, s.elapsed_us());
#endif
#ifdef GPIXMAP_CHECK_THRESHOLD
					acceltime = s.elapsed_us();
					s.start();
#else
					continue;
#endif
				}

			for (int y = area.top(); y < area.bottom(); y++)
			{
				uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + area.left() * surface->bypp);
				int x = area.width();
				while (x--)
					*dst++ = col;
			}
#ifdef GPIXMAP_DEBUG
			s.stop();
			eDebug("[gPixmap] [BLITBENCH] cpu fill %dx%d (%d bytes) took %u us", area.width(), area.height(), area.surface() * surface->bypp, s.elapsed_us());
#ifdef GPIXMAP_CHECK_THRESHOLD
			if (surface->data_phys)
			{
				adjustFillThreshold(s.elapsed_us(), area.surface() * surface->bypp);
			}
#endif
#endif
		}
		else
			eWarning("[gPixmap] couldn't fill %d bpp", surface->bpp);
	}
}

void gPixmap::fill(const gRegion &region, const gRGB &color)
{
	unsigned int i;
	for (i = 0; i < region.rects.size(); ++i)
	{
		const eRect &area = region.rects[i];
		if (area.empty())
			continue;

		if (surface->bpp == 32)
		{
			uint32_t col;

			col = color.argb();
			col ^= 0xFF000000;

#ifdef GPIXMAP_DEBUG
			Stopwatch s;
#endif
			if (surface->data_phys && ((area.surface() * surface->bypp) > GFX_SURFACE_FILL_ACCELERATION_THRESHOLD))
				if (!gAccel::getInstance()->fill(surface, area, col))
				{
#ifdef GPIXMAP_DEBUG
					s.stop();
					eDebug("[gPixmap] [BLITBENCH] accel fill %dx%d (%d bytes) took %u us", area.width(), area.height(), area.surface() * surface->bypp, s.elapsed_us());
#endif
#ifdef GPIXMAP_CHECK_THRESHOLD
					acceltime = s.elapsed_us();
					s.start();
#else
					continue;
#endif
				}

			for (int y = area.top(); y < area.bottom(); y++)
			{
				uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + area.left() * surface->bypp);
				int x = area.width();
				while (x--)
					*dst++ = col;
			}
#ifdef GPIXMAP_DEBUG
			s.stop();
			eDebug("[gPixmap] [BLITBENCH] cpu fill %dx%d (%d bytes) took %u us", area.width(), area.height(), area.surface() * surface->bypp, s.elapsed_us());
#ifdef GPIXMAP_CHECK_THRESHOLD
			if (surface->data_phys)
			{
				adjustFillThreshold(s.elapsed_us(), area.surface() * surface->bypp);
			}
#endif
#endif
		}
		else if (surface->bpp == 16)
		{
			uint32_t icol = color.argb();
#if BYTE_ORDER == LITTLE_ENDIAN
			uint16_t col = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
			uint16_t col = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
			for (int y = area.top(); y < area.bottom(); y++)
			{
				uint16_t *dst = (uint16_t *)(((uint8_t *)surface->data) + y * surface->stride + area.left() * surface->bypp);
				int x = area.width();
				while (x--)
					*dst++ = col;
			}
		}
		else
			eWarning("[gPixmap] couldn't rgbfill %d bpp", surface->bpp);
	}
}

static inline void blit_8i_to_32(uint32_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
		*dst++ = pal[*src++];
}

static inline void blit_8i_to_32_at(uint32_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
	{
		if (!(pal[*src] & 0x80000000))
		{
			src++;
			dst++;
		}
		else
			*dst++ = pal[*src++];
	}
}

static inline void blit_8i_to_16(uint16_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
		*dst++ = pal[*src++] & 0xFFFF;
}

static inline void blit_8i_to_16_at(uint16_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
	{
		if (!(pal[*src] & 0x80000000))
		{
			src++;
			dst++;
		}
		else
			*dst++ = pal[*src++] & 0xFFFF;
	}
}

static void blit_8i_to_32_ab(gRGB *dst, const uint8_t *src, const gRGB *pal, int width)
{
	while (width--)
	{
		dst->alpha_blend(pal[*src++]);
		++dst;
	}
}

static void convert_palette(uint32_t *pal, const gPalette &clut)
{
	int i = 0;
	if (clut.data)
	{
		while (i < clut.colors)
		{
			pal[i] = clut.data[i].argb() ^ 0xFF000000;
			++i;
		}
	}
	for (; i != 256; ++i)
	{
		pal[i] = (0x010101 * i) | 0xFF000000;
	}
}

#define FIX 0x10000

void gPixmap::drawRectangle(const gRegion &region, const eRect &area, const gRGB &backgroundColor, const gRGB &borderColor, int borderWidth, const std::vector<gRGB> &gradientColors, uint8_t direction, int radius, uint8_t edges, bool alphablend, int gradientFullSize)
{
	if (surface->bpp < 32)
	{
		eWarning("[gPixmap] couldn't rgbfill %d bpp", surface->bpp);
		return;
	}

#ifdef GPIXMAP_DEBUG
	Stopwatch s;
#endif
	const uint8_t GRADIENT_VERTICAL = 1;
	uint32_t backColor = backgroundColor.argb();
	backColor ^= 0xFF000000;
	uint32_t borderCol = borderColor.argb();
	borderCol ^= 0xFF000000;
	uint32_t *gradientBuf = nullptr;

	const int maxGradientSize = (direction == GRADIENT_VERTICAL) ? area.height() : area.width();
	const int gradientSize = (gradientFullSize) ? MAX(gradientFullSize, maxGradientSize) : maxGradientSize;
	if(!direction)
		gradientBuf = createGradientBuffer2(gradientSize, backgroundColor, backgroundColor);
	else if(gradientColors.size() == 2 || gradientColors.at(1) == gradientColors.at(2))
		gradientBuf = createGradientBuffer2(gradientSize, gradientColors.at(0), gradientColors.at(1));
	else
		gradientBuf = createGradientBuffer3(gradientSize, gradientColors);

	CornerData cornerData(radius, edges, area.width(), area.height(), borderWidth, borderCol);

	for (unsigned int i = 0; i < region.rects.size(); ++i)
	{
		eRect reg = area;
		reg &= region.rects[i];

		if (reg.empty())
			continue;

		int corners = 0;
		eRect cornerRect;

		if (cornerData.topLeftCornerRadius)
		{
			cornerRect = eRect(area.left(), area.top(), cornerData.topLeftCornerRadius, cornerData.topLeftCornerRadius);
			cornerRect &= region.rects[i];
			if (!cornerRect.empty())
			{
				corners += 1;
				drawAngleTl(surface, gradientBuf, area, direction, cornerRect, cornerData);
			}
		}
		if (cornerData.topRightCornerRadius)
		{
			cornerRect = eRect(area.right() - cornerData.topRightCornerRadius, area.top(), cornerData.topRightCornerRadius, cornerData.topRightCornerRadius);
			cornerRect &= region.rects[i];
			if (!cornerRect.empty())
			{
				corners += 2;
				drawAngleTr(surface, gradientBuf, area, direction, cornerRect, cornerData);
			}
		}
		if (cornerData.bottomLeftCornerRadius)
		{
			cornerRect = eRect(area.left(), area.bottom() - cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius);
			cornerRect &= region.rects[i];
			if (!cornerRect.empty())
			{
				corners += 4;
				drawAngleBl(surface, gradientBuf, area, direction, cornerRect, cornerData);
			}
		}

		if (cornerData.bottomRightCornerRadius)
		{
			cornerRect = eRect(area.right() - cornerData.bottomRightCornerRadius, area.bottom() - cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius);
			cornerRect &= region.rects[i];
			if (!cornerRect.empty())
			{
				corners += 8;
				drawAngleBr(surface, gradientBuf, area, direction, cornerRect, cornerData);
			}
		}

		if (cornerData.isCircle)
			continue;

		const int bottom = MAX(cornerData.bottomRightCornerRadius, cornerData.bottomLeftCornerRadius);
		const int top = MAX(cornerData.topRightCornerRadius, cornerData.topLeftCornerRadius);

		int topw = area.width();
		int topl = area.left();
		int bottomw = area.width();
		int bottoml = area.left();

		if (corners & 1)
		{
			topw -= cornerData.topLeftCornerRadius;
			topl += cornerData.topLeftCornerRadius;
		}
		if (corners & 2)
			topw -= cornerData.topRightCornerRadius;

		if (corners & 4)
		{
			bottomw -= cornerData.bottomLeftCornerRadius;
			bottoml += cornerData.bottomLeftCornerRadius;
		}
		if (corners & 8)
			bottomw -= cornerData.bottomRightCornerRadius;

		eRect topRect = eRect(topl, area.top(), topw, top);
		topRect &= region.rects[i];

		eRect bottomRect = eRect(bottoml, area.bottom() - bottom, bottomw, bottom);
		bottomRect &= region.rects[i];

		eRect mRect = eRect(area.left(), area.top() + top, area.width(), area.height() - top - bottom);
		mRect &= region.rects[i];
		const int blendRatio = 12;

		if (direction == GRADIENT_VERTICAL)
		{

			// draw center rect
			if (!mRect.empty())
			{
				if (alphablend && !cornerData.radiusSet)
				{
					for (int y = mRect.top(); y < mRect.bottom(); ++y)
					{
						uint32_t *dstptr = (uint32_t*)(((uint8_t*)surface->data) + y * surface->stride + mRect.left() * surface->bypp);
						const gRGB *src = (gRGB*)&gradientBuf[y - area.top()];
						gRGB *dst = (gRGB*)dstptr;
						int width = mRect.width();
						const uint8_t alpha = src->a;
						const uint8_t blue = src->b;
						const uint8_t green = src->g;
						const uint8_t red = src->r;

						while (width >= blendRatio)
						{
							for (int i = 0; i < blendRatio; ++i)
							{
								dst[i].b += (((blue - dst[i].b) * alpha) >> 8);
								dst[i].g += (((green - dst[i].g) * alpha) >> 8);
								dst[i].r += (((red - dst[i].r) * alpha) >> 8);
								dst[i].a += (((0xFF - dst[i].a) * alpha) >> 8);
							}

							dst += blendRatio;
							width -= blendRatio;
						}

						while (width > 0)
						{
							dst->b += (((blue - dst->b) * alpha) >> 8);
							dst->g += (((green - dst->g) * alpha) >> 8);
							dst->r += (((red - dst->r) * alpha) >> 8);
							dst->a += (((0xFF - dst->a) * alpha) >> 8);
							
							++dst;
							--width;
						}
					}
				}
				else
				{
					for (int y = mRect.top(); y < mRect.bottom(); y++)
					{
						uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + mRect.left() * surface->bypp);
						int yInOriginalArea = y - area.top();
						backColor = gradientBuf[yInOriginalArea];
						int x = mRect.width();
						while (x)
						{
							*dst++ = backColor;
							x--;
						}
					}
				} // if blitAlphaBlend
			}	  // if center

			if (top && !topRect.empty())
			{
				for (int y = topRect.top(); y < topRect.bottom(); y++)
				{
					uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + topRect.left() * surface->bypp);
					int yInOriginalArea = y - area.top();
					backColor = gradientBuf[yInOriginalArea];
					int x = topRect.width();
					while (x)
					{
						*dst++ = backColor;
						x--;
					}
				}
			} // if top

			if (bottom && !bottomRect.empty())
			{
				for (int y = bottomRect.top(); y < bottomRect.bottom(); y++)
				{
					uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + bottomRect.left() * surface->bypp);
					int yInOriginalArea = y - area.top();
					backColor = gradientBuf[yInOriginalArea];
					int x = bottomRect.width();
					while (x)
					{
						*dst++ = backColor;
						x--;
					}
				}
			} // if bottom
		}
		else
		{

			if (!mRect.empty())
			{
				if (alphablend && !cornerData.radiusSet)
				{
					for (int y = mRect.top(); y < mRect.bottom(); y++)
					{
						uint32_t *dstptr = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + mRect.left() * surface->bypp);
						uint32_t *gradientBuf2 = gradientBuf + mRect.left() - area.left();
						int width = mRect.width();
						gRGB *src = (gRGB *)gradientBuf2;
						gRGB *dst = (gRGB *)dstptr;
						while (width >= blendRatio)
						{
							for (int i = 0; i < blendRatio; ++i)
							{
								dst[i].b += (((src->b - dst[i].b) * src->a) >> 8);
								dst[i].g += (((src->g - dst[i].g) * src->a) >> 8);
								dst[i].r += (((src->r - dst[i].r) * src->a) >> 8);
								dst[i].a += (((0xFF - dst[i].a) * src->a) >> 8);
							}

							dst += blendRatio;
							src += blendRatio;
							width -= blendRatio;
						}

						while (width > 0)
						{
							dst->b += (((src->b - dst->b) * src->a) >> 8);
							dst->g += (((src->g - dst->g) * src->a) >> 8);
							dst->r += (((src->r - dst->r) * src->a) >> 8);
							dst->a += (((0xFF - dst->a) * src->a) >> 8);
							
							++dst;
							++src;
							--width;
						}
					}
				}
				else
				{
					int linesize = mRect.width() * surface->bypp;
					for (int y = mRect.top(); y < mRect.bottom(); y++)
					{
						uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + mRect.left() * surface->bypp);
						uint32_t *gradientBuf2 = gradientBuf + mRect.left() - area.left();
						std::memcpy(dst, gradientBuf2, linesize);
					}
				} // if blitAlphaBlend
			}	  // if center

			if (top && !topRect.empty())
			{
				int linesize = topRect.width() * surface->bypp;
				for (int y = topRect.top(); y < topRect.bottom(); y++)
				{
					uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + topRect.left() * surface->bypp);
					uint32_t *gradientBuf2 = gradientBuf + topRect.left() - area.left();
					std::memcpy(dst, gradientBuf2, linesize);
				}
			} // if top

			if (bottom && !bottomRect.empty())
			{
				int linesize = bottomRect.width() * surface->bypp;
				for (int y = bottomRect.top(); y < bottomRect.bottom(); y++)
				{
					uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + bottomRect.left() * surface->bypp);
					uint32_t *gradientBuf2 = gradientBuf + bottomRect.left() - area.left();
					std::memcpy(dst, gradientBuf2, linesize);
				}
			} // if bottom
		}	  // if direction
	}		  // for region
#ifdef GPIXMAP_DEBUG
	s.stop();
	eDebug("[gPixmap] [BLITBENCH] cpu drawRectangle %dx%d (%d bytes) took %u us", area.width(), area.height(), area.surface() * surface->bypp, s.elapsed_us());
#endif
	if (gradientBuf)
		free(gradientBuf);
}

void gPixmap::blitRounded32Bit(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag)
{
	CornerData cornerData(cornerRadius, edges, pos.width(), pos.height(), 0, 0xFF000000);
	int corners = 0;
	eRect cornerRect;
	if (cornerData.topLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.top(), cornerData.topLeftCornerRadius, cornerData.topLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 1;
			drawAngle32Tl(surface, src, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.topRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.topRightCornerRadius, pos.top(), cornerData.topRightCornerRadius, cornerData.topRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 2;
			drawAngle32Tr(surface, src, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.bottomLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.bottom() - cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 4;
			drawAngle32Bl(surface, src, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.bottomRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.bottomRightCornerRadius, pos.bottom() - cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 8;
			drawAngle32Br(surface, src, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.isCircle)
		return;

	const int bottom = MAX(cornerData.bottomRightCornerRadius, cornerData.bottomLeftCornerRadius);
	const int top = MAX(cornerData.topRightCornerRadius, cornerData.topLeftCornerRadius);

	int topw = pos.width();
	int topl = pos.left();
	int bottomw = pos.width();
	int bottoml = pos.left();

	if (corners & 1)
	{
		topw -= cornerData.topLeftCornerRadius;
		topl += cornerData.topLeftCornerRadius;
	}
	if (corners & 2)
		topw -= cornerData.topRightCornerRadius;

	if (corners & 4)
	{
		bottomw -= cornerData.bottomLeftCornerRadius;
		bottoml += cornerData.bottomLeftCornerRadius;
	}
	if (corners & 8)
		bottomw -= cornerData.bottomRightCornerRadius;

	eRect topRect = eRect(topl, pos.top(), topw, top);
	topRect &= clip;

	eRect bottomRect = eRect(bottoml, pos.bottom() - bottom, bottomw, bottom);
	bottomRect &= clip;

	eRect mRect = eRect(pos.left(), pos.top() + top, pos.width(), pos.height() - top - bottom);
	mRect &= clip;

	const int aLeft = pos.left();
	const int aTop = pos.top();

	if (!mRect.empty())
	{
		const int rLeft = mRect.left();
		const int rTop = mRect.top();
		const int rBottom = mRect.bottom();
		const int rWidth = mRect.width();
		int linesize = rWidth * surface->bypp;
		uint32_t *srcptr = (uint32_t *)src.surface->data;
		uint32_t *dstptr = (uint32_t *)surface->data;

		srcptr += (rLeft - aLeft) + (rTop - aTop) * src.surface->stride / 4;
		dstptr += rLeft + rTop * surface->stride / 4;
		for (int y = rTop; y < rBottom; y++)
		{
			if (flag & blitAlphaTest)
			{
				int width = rWidth;
				uint32_t *src = srcptr;
				uint32_t *dst = dstptr;

				while (width--)
				{
					if (!((*src) & 0xFF000000))
					{
						src++;
						dst++;
					}
					else
						*dst++ = *src++;
				}
			}
			else if (flag & blitAlphaBlend)
			{
				int width = rWidth;
				gRGB *src = (gRGB *)srcptr;
				gRGB *dst = (gRGB *)dstptr;

				while (width--) {
					dst->b += (((src->b - dst->b) * src->a) >> 8);
					dst->g += (((src->g - dst->g) * src->a) >> 8);
					dst->r += (((src->r - dst->r) * src->a) >> 8);
					dst->a += (((0xFF - dst->a) * src->a) >> 8);
					++src;
					++dst;
				}
			}
			else
				std::memcpy(dstptr, srcptr, linesize);
			srcptr = (uint32_t *)((uint8_t *)srcptr + src.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	if (top && !topRect.empty())
	{
		const int rLeft = topRect.left();
		const int rTop = topRect.top();
		const int rBottom = topRect.bottom();
		const int rWidth = topRect.width();
		int linesize = rWidth * surface->bypp;
		uint32_t *srcptr = (uint32_t *)src.surface->data;
		uint32_t *dstptr = (uint32_t *)surface->data;

		srcptr += (rLeft - aLeft) + (rTop - aTop) * src.surface->stride / 4;
		dstptr += rLeft + rTop * surface->stride / 4;
		for (int y = rTop; y < rBottom; y++)
		{
			if (flag & blitAlphaTest)
			{
				int width = rWidth;
				uint32_t *src = srcptr;
				uint32_t *dst = dstptr;

				while (width--)
				{
					if (!((*src) & 0xFF000000))
					{
						src++;
						dst++;
					}
					else
						*dst++ = *src++;
				}
			}
			else if (flag & blitAlphaBlend)
			{
				int width = rWidth;
				gRGB *src = (gRGB *)srcptr;
				gRGB *dst = (gRGB *)dstptr;

				while (width--) {
					dst->b += (((src->b - dst->b) * src->a) >> 8);
					dst->g += (((src->g - dst->g) * src->a) >> 8);
					dst->r += (((src->r - dst->r) * src->a) >> 8);
					dst->a += (((0xFF - dst->a) * src->a) >> 8);
					++src;
					++dst;
				}
			}
			else
				std::memcpy(dstptr, srcptr, linesize);
			srcptr = (uint32_t *)((uint8_t *)srcptr + src.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}

	if (bottom && !bottomRect.empty())
	{
		const int rLeft = bottomRect.left();
		const int rTop = bottomRect.top();
		const int rBottom = bottomRect.bottom();
		const int rWidth = bottomRect.width();
		int linesize = rWidth * surface->bypp;
		uint32_t *srcptr = (uint32_t *)src.surface->data;
		uint32_t *dstptr = (uint32_t *)surface->data;

		srcptr += (rLeft - aLeft) + (rTop - aTop) * src.surface->stride / 4;
		dstptr += rLeft + rTop * surface->stride / 4;
		for (int y = rTop; y < rBottom; y++)
		{
			if (flag & blitAlphaTest)
			{
				int width = rWidth;
				uint32_t *src = srcptr;
				uint32_t *dst = dstptr;

				while (width--)
				{
					if (!((*src) & 0xFF000000))
					{
						src++;
						dst++;
					}
					else
						*dst++ = *src++;
				}
			}
			else if (flag & blitAlphaBlend)
			{
				int width = rWidth;
				gRGB *src = (gRGB *)srcptr;
				gRGB *dst = (gRGB *)dstptr;

				while (width--) {
					dst->b += (((src->b - dst->b) * src->a) >> 8);
					dst->g += (((src->g - dst->g) * src->a) >> 8);
					dst->r += (((src->r - dst->r) * src->a) >> 8);
					dst->a += (((0xFF - dst->a) * src->a) >> 8);
					++src;
					++dst;
				}
			}
			else
				std::memcpy(dstptr, srcptr, linesize);
			srcptr = (uint32_t *)((uint8_t *)srcptr + src.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
}

void gPixmap::blitRounded32BitScaled(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag)
{
	CornerData cornerData(cornerRadius, edges, pos.width(), pos.height(), 0, 0xFF000000);
	int corners = 0;
	eRect cornerRect;
	if (cornerData.topLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.top(), cornerData.topLeftCornerRadius, cornerData.topLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 1;
			drawAngle32ScaledTl(surface, src, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.topRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.topRightCornerRadius, pos.top(), cornerData.topRightCornerRadius, cornerData.topRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 2;
			drawAngle32ScaledTr(surface, src, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.bottomLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.bottom() - cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 4;
			drawAngle32ScaledBl(surface, src, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.bottomRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.bottomRightCornerRadius, pos.bottom() - cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 8;
			drawAngle32ScaledBr(surface, src, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.isCircle)
		return;

	const int bottom = MAX(cornerData.bottomRightCornerRadius, cornerData.bottomLeftCornerRadius);
	const int top = MAX(cornerData.topRightCornerRadius, cornerData.topLeftCornerRadius);

	int topw = pos.width();
	int topl = pos.left();
	int bottomw = pos.width();
	int bottoml = pos.left();

	if (corners & 1)
	{
		topw -= cornerData.topLeftCornerRadius;
		topl += cornerData.topLeftCornerRadius;
	}
	if (corners & 2)
		topw -= cornerData.topRightCornerRadius;

	if (corners & 4)
	{
		bottomw -= cornerData.bottomLeftCornerRadius;
		bottoml += cornerData.bottomLeftCornerRadius;
	}
	if (corners & 8)
		bottomw -= cornerData.bottomRightCornerRadius;

	eRect topRect = eRect(topl, pos.top(), topw, top);
	topRect &= clip;

	eRect bottomRect = eRect(bottoml, pos.bottom() - bottom, bottomw, bottom);
	bottomRect &= clip;

	eRect mRect = eRect(pos.left(), pos.top() + top, pos.width(), pos.height() - top - bottom);
	mRect &= clip;

	const int src_bypp = src.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = src.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)src.size().width() / (float)pos.width();
	const float scaleY = (float)src.size().height() / (float)pos.height();
	const int aLeft = pos.left();
	const int aTop = pos.top();

	if (!mRect.empty())
	{
		const int rLeft = mRect.left();
		const int rRight = mRect.right();
		const int rTop = mRect.top();
		const int rBottom = mRect.bottom();
		uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;
		if (flag & blitAlphaTest)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
					if (*src & 0x80000000)
						*dst = *src;
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else if (flag & blitAlphaBlend)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				gRGB *dst = (gRGB *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const gRGB *src = (gRGB *)(src_row + src_x * src_bypp);
					dst->b += (((src->b - dst->b) * src->a) >> 8);
					dst->g += (((src->g - dst->g) * src->a) >> 8);
					dst->r += (((src->r - dst->r) * src->a) >> 8);
					dst->a += (((0xFF - dst->a) * src->a) >> 8);
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
					*dst++ = *src;
				}
				dst_row += dst_stride;
			}
		}
	}
	if (top && !topRect.empty())
	{
		const int rLeft = topRect.left();
		const int rRight = topRect.right();
		const int rTop = topRect.top();
		const int rBottom = topRect.bottom();
		uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

		if (flag & blitAlphaTest)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
					if (*src & 0x80000000)
						*dst = *src;
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else if (flag & blitAlphaBlend)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				gRGB *dst = (gRGB *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const gRGB *src = (gRGB *)(src_row + src_x * src_bypp);
					dst->b += (((src->b - dst->b) * src->a) >> 8);
					dst->g += (((src->g - dst->g) * src->a) >> 8);
					dst->r += (((src->r - dst->r) * src->a) >> 8);
					dst->a += (((0xFF - dst->a) * src->a) >> 8);
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
					*dst = *src;
					dst++;
				}
				dst_row += dst_stride;
			}
		}
	}
	if (bottom && !bottomRect.empty())
	{
		const int rLeft = bottomRect.left();
		const int rRight = bottomRect.right();
		const int rTop = bottomRect.top();
		const int rBottom = bottomRect.bottom();
		uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

		if (flag & blitAlphaTest)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
					if (*src & 0x80000000)
						*dst = *src;
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else if (flag & blitAlphaBlend)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				gRGB *dst = (gRGB *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const gRGB *src = (gRGB *)(src_row + src_x * src_bypp);
					dst->b += (((src->b - dst->b) * src->a) >> 8);
					dst->g += (((src->g - dst->g) * src->a) >> 8);
					dst->r += (((src->r - dst->r) * src->a) >> 8);
					dst->a += (((0xFF - dst->a) * src->a) >> 8);
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
					*dst = *src;
					dst++;
				}
				dst_row += dst_stride;
			}
		}
	}
}

void gPixmap::blitRounded8Bit(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag)
{

	int corners = 0;
	uint32_t pal[256];
	convert_palette(pal, src.surface->clut);
	CornerData cornerData(cornerRadius, edges, pos.width(), pos.height(), 0, 0xFF000000);
	eRect cornerRect;
	if (cornerData.topLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.top(), cornerData.topLeftCornerRadius, cornerData.topLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 1;
			drawAngle8Tl(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.topRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.topRightCornerRadius, pos.top(), cornerData.topRightCornerRadius, cornerData.topRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 2;
			drawAngle8Tr(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.bottomLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.bottom() - cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 4;
			drawAngle8Bl(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.bottomRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.bottomRightCornerRadius, pos.bottom() - cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 8;
			drawAngle8Br(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.isCircle)
		return;

	const int bottom = MAX(cornerData.bottomRightCornerRadius, cornerData.bottomLeftCornerRadius);
	const int top = MAX(cornerData.topRightCornerRadius, cornerData.topLeftCornerRadius);

	int topw = pos.width();
	int topl = pos.left();
	int bottomw = pos.width();
	int bottoml = pos.left();

	if (corners & 1)
	{
		topw -= cornerData.topLeftCornerRadius;
		topl += cornerData.topLeftCornerRadius;
	}
	if (corners & 2)
		topw -= cornerData.topRightCornerRadius;

	if (corners & 4)
	{
		bottomw -= cornerData.bottomLeftCornerRadius;
		bottoml += cornerData.bottomLeftCornerRadius;
	}
	if (corners & 8)
		bottomw -= cornerData.bottomRightCornerRadius;

	eRect topRect = eRect(topl, pos.top(), topw, top);
	topRect &= clip;

	eRect bottomRect = eRect(bottoml, pos.bottom() - bottom, bottomw, bottom);
	bottomRect &= clip;

	eRect mRect = eRect(pos.left(), pos.top() + top, pos.width(), pos.height() - top - bottom);
	mRect &= clip;

	if (!mRect.empty())
	{
		const uint8_t *srcptr = (uint8_t *)src.surface->data;
		uint32_t *dstptr = (uint32_t *)surface->data;

		srcptr += (mRect.left() - pos.left()) + (mRect.top() - pos.top()) * src.surface->stride;
		dstptr += mRect.left() + mRect.top() * surface->stride / 4;
		for (int y = mRect.bottom(); y > mRect.top(); --y)
		{
			if (flag & blitAlphaTest)
			{
				blit_8i_to_32_at((uint32_t *)dstptr, srcptr, pal, mRect.width());
			}
			else if (flag & blitAlphaBlend)
			{
				blit_8i_to_32_ab((gRGB *)dstptr, srcptr, (const gRGB *)pal, mRect.width());
			}
			else
				blit_8i_to_32((uint32_t *)dstptr, srcptr, pal, mRect.width());
			srcptr += src.surface->stride;
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	if (top && !topRect.empty())
	{
		const uint8_t *srcptr = (uint8_t *)src.surface->data;
		uint32_t *dstptr = (uint32_t *)surface->data;

		srcptr += (topRect.left() - pos.left()) + (topRect.top() - pos.top()) * src.surface->stride;
		dstptr += topRect.left() + topRect.top() * surface->stride / 4;
		for (int y = topRect.top(); y < topRect.bottom(); y++)
		{
			if (flag & blitAlphaTest)
			{
				blit_8i_to_32_at((uint32_t *)dstptr, srcptr, pal, topRect.width());
			}
			else if (flag & blitAlphaBlend)
			{
				blit_8i_to_32_ab((gRGB *)dstptr, srcptr, (const gRGB *)pal, topRect.width());
			}
			else
				blit_8i_to_32((uint32_t *)dstptr, srcptr, pal, topRect.width());
			srcptr += src.surface->stride;
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}

	if (bottom && !bottomRect.empty())
	{
		const uint8_t *srcptr = (uint8_t *)src.surface->data;
		uint32_t *dstptr = (uint32_t *)surface->data;

		srcptr += (bottomRect.left() - pos.left()) + (bottomRect.top() - pos.top()) * src.surface->stride;
		dstptr += bottomRect.left() + (bottomRect.top()) * surface->stride / 4;
		for (int y = (bottomRect.top() - pos.top()); y < (bottomRect.top() - pos.top() + bottom); y++)
		{
			if (flag & blitAlphaTest)
			{
				blit_8i_to_32_at((uint32_t *)dstptr, srcptr, pal, bottomRect.width());
			}
			else if (flag & blitAlphaBlend)
			{
				blit_8i_to_32_ab((gRGB *)dstptr, srcptr, (const gRGB *)pal, bottomRect.width());
			}
			else
				blit_8i_to_32((uint32_t *)dstptr, srcptr, pal, bottomRect.width());
			srcptr += src.surface->stride;
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
}

void gPixmap::blitRounded8BitScaled(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag)
{
	int corners = 0;
	uint32_t pal[256];
	convert_palette(pal, src.surface->clut);
	CornerData cornerData(cornerRadius, edges, pos.width(), pos.height(), 0, 0xFF000000);
	eRect cornerRect;

	if (cornerData.topLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.top(), cornerData.topLeftCornerRadius, cornerData.topLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 1;
			drawAngle8ScaledTl(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.topRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.topRightCornerRadius, pos.top(), cornerData.topRightCornerRadius, cornerData.topRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 2;
			drawAngle8ScaledTr(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}
	if (cornerData.bottomLeftCornerRadius)
	{
		cornerRect = eRect(pos.left(), pos.bottom() - cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius, cornerData.bottomLeftCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 4;
			drawAngle8ScaledBl(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.bottomRightCornerRadius)
	{
		cornerRect = eRect(pos.right() - cornerData.bottomRightCornerRadius, pos.bottom() - cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius, cornerData.bottomRightCornerRadius);
		cornerRect &= clip;
		if (!cornerRect.empty())
		{
			corners += 8;
			drawAngle8ScaledBr(surface, src, pal, pos, cornerRect, cornerData, flag);
		}
	}

	if (cornerData.isCircle)
		return;

	const int bottom = MAX(cornerData.bottomRightCornerRadius, cornerData.bottomLeftCornerRadius);
	const int top = MAX(cornerData.topRightCornerRadius, cornerData.topLeftCornerRadius);

	int topw = pos.width();
	int topl = pos.left();
	int bottomw = pos.width();
	int bottoml = pos.left();

	if (corners & 1)
	{
		topw -= cornerData.topLeftCornerRadius;
		topl += cornerData.topLeftCornerRadius;
	}
	if (corners & 2)
		topw -= cornerData.topRightCornerRadius;

	if (corners & 4)
	{
		bottomw -= cornerData.bottomLeftCornerRadius;
		bottoml += cornerData.bottomLeftCornerRadius;
	}
	if (corners & 8)
		bottomw -= cornerData.bottomRightCornerRadius;

	eRect topRect = eRect(topl, pos.top(), topw, top);
	topRect &= clip;

	eRect bottomRect = eRect(bottoml, pos.bottom() - bottom, bottomw, bottom);
	bottomRect &= clip;

	eRect mRect = eRect(pos.left(), pos.top() + top, pos.width(), pos.height() - top - bottom);
	mRect &= clip;

	const int src_bypp = src.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = src.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)src.size().width() / (float)pos.width();
	const float scaleY = (float)src.size().height() / (float)pos.height();
	const int aLeft = pos.left();
	const int aTop = pos.top();

	if (!mRect.empty())
	{
		const int rLeft = mRect.left();
		const int rRight = mRect.right();
		const int rTop = mRect.top();
		const int rBottom = mRect.bottom();
		uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;
		if (flag & blitAlphaTest)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					if (pal[*src] & 0x80000000)
						*dst = pal[*src];
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else if (flag & blitAlphaBlend)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				gRGB *dst = (gRGB *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					dst->alpha_blend(pal[*src]);
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					*dst = pal[*src];
					dst++;
				}
				dst_row += dst_stride;
			}
		}
	}
	if (top && !topRect.empty())
	{
		const int rLeft = topRect.left();
		const int rRight = topRect.right();
		const int rTop = topRect.top();
		const int rBottom = topRect.bottom();
		uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

		if (flag & blitAlphaTest)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					if (pal[*src] & 0x80000000)
						*dst = pal[*src];
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else if (flag & blitAlphaBlend)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				gRGB *dst = (gRGB *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					dst->alpha_blend(pal[*src]);
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					*dst = pal[*src];
					dst++;
				}
				dst_row += dst_stride;
			}
		}
	}
	if (bottom && !bottomRect.empty())
	{
		const int rLeft = bottomRect.left();
		const int rRight = bottomRect.right();
		const int rTop = bottomRect.top();
		const int rBottom = bottomRect.bottom();
		uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

		if (flag & blitAlphaTest)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					if (pal[*src] & 0x80000000)
						*dst = pal[*src];
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else if (flag & blitAlphaBlend)
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				gRGB *dst = (gRGB *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					dst->alpha_blend(pal[*src]);
					dst++;
				}
				dst_row += dst_stride;
			}
		}
		else
		{
			for (int y = rTop; y < rBottom; ++y)
			{
				int src_y = (int)((y - aTop) * scaleY);
				const uint8_t *src_row = (const uint8_t *)src.surface->data + src_y * src_stride;
				uint32_t *dst = (uint32_t *)dst_row;

				for (int x = rLeft; x < rRight; ++x)
				{
					int src_x = (int)((x - aLeft) * scaleX);
					const uint8_t *src = src_row + src_x * src_bypp;
					*dst = pal[*src];
					dst++;
				}
				dst_row += dst_stride;
			}
		}
	}
}

void gPixmap::blit(const gPixmap &src, const eRect &_pos, const gRegion &clip, int cornerRadius, uint8_t edges, int flag)
{
	bool accel = (surface->data_phys && src.surface->data_phys);
	bool accumulate = accel && (gAccel::getInstance()->accumulate() >= 0);
	int accelerationthreshold = GFX_SURFACE_BLIT_ACCELERATION_THRESHOLD;
	//	eDebug("[gPixmap] blit: -> %d,%d+%d,%d -> %d,%d+%d,%d, flags=0x%x, accel=%d",
	//		_pos.x(), _pos.y(), _pos.width(), _pos.height(),
	//		clip.extends.x(), clip.extends.y(), clip.extends.width(), clip.extends.height(),
	//		flag, accel);
	eRect pos = _pos;

	//	eDebug("[gPixmap] source size: %d %d", src.size().width(), src.size().height());

	int scale_x = FIX, scale_y = FIX;

	if (!(flag & blitScale))
	{
		// pos' size is ignored if left or top aligning.
		// if its size isn't set, centre and right/bottom aligning is ignored

		if (_pos.size().isValid())
		{
			if (flag & blitHAlignCenter)
				pos.setLeft(_pos.left() + (_pos.width() - src.size().width()) / 2);
			else if (flag & blitHAlignRight)
				pos.setLeft(_pos.right() - src.size().width());

			if (flag & blitVAlignCenter)
				pos.setTop(_pos.top() + (_pos.height() - src.size().height()) / 2);
			else if (flag & blitVAlignBottom)
				pos.setTop(_pos.bottom() - src.size().height());
		}

		pos.setWidth(src.size().width());
		pos.setHeight(src.size().height());
	}
	else if (pos.size() == src.size()) /* no scaling required */
		flag &= ~blitScale;
	else // blitScale is set
	{
		ASSERT(src.size().width());
		ASSERT(src.size().height());
		scale_x = pos.size().width() * FIX / src.size().width();   // NOSONAR
		scale_y = pos.size().height() * FIX / src.size().height(); // NOSONAR
		if (flag & blitKeepAspectRatio)
		{
			if (scale_x > scale_y)
			{
				// vertical is full height, adjust horizontal to be smaller
				scale_x = scale_y;
				pos.setWidth(src.size().width() * _pos.height() / src.size().height());
				if (flag & blitHAlignCenter)
					pos.moveBy((_pos.width() - pos.width()) / 2, 0);
				else if (flag & blitHAlignRight)
					pos.moveBy(_pos.width() - pos.width(), 0);
			}
			else
			{
				// horizontal is full width, adjust vertical to be smaller
				scale_y = scale_x;
				pos.setHeight(src.size().height() * _pos.width() / src.size().width());
				if (flag & blitVAlignCenter)
					pos.moveBy(0, (_pos.height() - pos.height()) / 2);
				else if (flag & blitVAlignBottom)
					pos.moveBy(0, _pos.height() - pos.height());
			}
		}
	}

	if (accumulate)
	{
		int totalsurface = 0;
		for (unsigned int i = 0; i < clip.rects.size(); ++i)
		{
			eRect area = pos; /* pos is the virtual (pre-clipping) area on the dest, which can be larger/smaller than src if scaling is enabled */
			area &= clip.rects[i];
			area &= eRect(ePoint(0, 0), size());

			if (area.empty())
				continue;

			eRect srcarea = area;

			if (flag & blitScale)
				srcarea = eRect(srcarea.x() * FIX / scale_x, srcarea.y() * FIX / scale_y, srcarea.width() * FIX / scale_x, srcarea.height() * FIX / scale_y);

			totalsurface += srcarea.surface() * src.surface->bypp;
		}
		if (totalsurface < accelerationthreshold)
		{
			accel = false;
		}
		else
		{
			/* total surface is larger than the threshold, no longer apply the threshold on individual clip rects */
			accelerationthreshold = 0;
		}
	}

	//	eDebug("[gPixmap] SCALE %x %x", scale_x, scale_y);

	for (unsigned int i = 0; i < clip.rects.size(); ++i)
	{
		//		eDebug("[gPixmap] clip rect: %d %d %d %d", clip.rects[i].x(), clip.rects[i].y(), clip.rects[i].width(), clip.rects[i].height());
		eRect area = pos; /* pos is the virtual (pre-clipping) area on the dest, which can be larger/smaller than src if scaling is enabled */
		area &= clip.rects[i];
		area &= eRect(ePoint(0, 0), size());

		if (area.empty())
			continue;

		eRect srcarea = area;
		srcarea.moveBy(-pos.x(), -pos.y());

		//		eDebug("[gPixmap] srcarea before scale: %d %d %d %d",
		//			srcarea.x(), srcarea.y(), srcarea.width(), srcarea.height());

		if (flag & blitScale)
			srcarea = eRect(srcarea.x() * FIX / scale_x, srcarea.y() * FIX / scale_y, srcarea.width() * FIX / scale_x, srcarea.height() * FIX / scale_y);

		//		eDebug("[gPixmap] srcarea after scale: %d %d %d %d",
		//			srcarea.x(), srcarea.y(), srcarea.width(), srcarea.height());

		if (cornerRadius && surface->bpp == 32)
		{
#ifdef GPIXMAP_DEBUG
			Stopwatch s;
#endif
			if (src.surface->bpp == 32)
			{
				if (flag & blitScale)
					blitRounded32BitScaled(src, pos, clip.rects[i], cornerRadius, edges, flag);
				else
					blitRounded32Bit(src, pos, clip.rects[i], cornerRadius, edges, flag);
			}
			else
			{
				if (flag & blitScale)
					blitRounded8BitScaled(src, pos, clip.rects[i], cornerRadius, edges, flag);
				else
					blitRounded8Bit(src, pos, clip.rects[i], cornerRadius, edges, flag);
			}
#ifdef GPIXMAP_DEBUG
			s.stop();
			eDebug("[gPixmap] [BLITBENCH] cpu blitRounded %dx%d transparent %d (%d bytes) took %u us", pos.width(), pos.height(), src.surface->transparent, srcarea.surface() * src.surface->bypp, s.elapsed_us());
#endif
			continue;
		}

#ifdef FORCE_NO_ACCELNEVER
		accel = false;
#else
		if (accel)
		{
			if (srcarea.surface() * src.surface->bypp < accelerationthreshold)
			{
				accel = false;
			}
		}
		if (accel)
		{
			/* we have hardware acceleration for this blit operation */
			if (flag & (blitAlphaTest | blitAlphaBlend))
			{
				/* alpha blending is requested */
				if (gAccel::getInstance()->hasAlphaBlendingSupport())
				{
#ifdef FORCE_ALPHABLENDING_ACCELERATION
					/* Hardware alpha blending is broken on the few
					 * boxes that support it, so only use it
					 * when scaling */

					accel = true;
#else
					if (flag & blitScale)
						accel = true;
					else if (flag & blitAlphaTest) /* Alpha test only on 8-bit */
						accel = (src.surface->bpp == 8);
					else
						accel = false;
#endif
				}
				else
				{
					/* our hardware does not support alphablending */
					accel = false;
				}
			}
		}

#ifdef GPIXMAP_CHECK_THRESHOLD
		accel = (surface->data_phys && src.surface->data_phys);
#endif
#endif

#ifdef GPIXMAP_DEBUG
		Stopwatch s;
#endif
		if (accel)
		{
			flag &= 7; // remove all flags except the blit flags
			if (!gAccel::getInstance()->blit(surface, src.surface, area, srcarea, flag))
			{
#ifdef GPIXMAP_DEBUG
				s.stop();
				eDebug("[gPixmap] [BLITBENCH] accel blit (%d bytes) took %u us", srcarea.surface() * src.surface->bypp, s.elapsed_us());
#endif
#ifdef GPIXMAP_CHECK_THRESHOLD
				acceltime = s.elapsed_us();
				s.start();
#else
				continue;
#endif
			}
		}

		if (flag & blitScale)
		{
			if ((surface->bpp == 32) && (src.surface->bpp == 8))
			{
				const uint8_t *srcptr = (uint8_t *)src.surface->data;
				uint8_t *dstptr = (uint8_t *)surface->data; // !!
				uint32_t pal[256];
				convert_palette(pal, src.surface->clut);

				const int src_stride = src.surface->stride;
				srcptr += srcarea.left() * src.surface->bypp + srcarea.top() * src_stride;
				dstptr += area.left() * surface->bypp + area.top() * surface->stride;
				const int width = area.width();
				const int height = area.height();
				const int src_height = srcarea.height();
				const int src_width = srcarea.width();
				if (flag & blitAlphaTest)
				{
					for (int y = 0; y < height; ++y)
					{
						const uint8_t *src_row_ptr = srcptr + (((y * src_height) / height) * src_stride);
						uint32_t *dst = (uint32_t *)dstptr;
						for (int x = 0; x < width; ++x)
						{
							uint32_t pixel = pal[src_row_ptr[(x * src_width) / width]];
							if (pixel & 0x80000000)
								*dst = pixel;
							++dst;
						}
						dstptr += surface->stride;
					}
				}
				else if (flag & blitAlphaBlend)
				{
					for (int y = 0; y < height; ++y)
					{
						const uint8_t *src_row_ptr = srcptr + (((y * src_height) / height) * src_stride);
						gRGB *dst = (gRGB *)dstptr;
						for (int x = 0; x < width; ++x)
						{
							dst->alpha_blend(pal[src_row_ptr[(x * src_width) / width]]);
							++dst;
						}
						dstptr += surface->stride;
					}
				}
				else
				{
					for (int y = 0; y < height; ++y)
					{
						const uint8_t *src_row_ptr = srcptr + (((y * src_height) / height) * src_stride);
						uint32_t *dst = (uint32_t *)dstptr;
						for (int x = 0; x < width; ++x)
						{
							*dst = pal[src_row_ptr[(x * src_width) / width]];
							++dst;
						}
						dstptr += surface->stride;
					}
				}
			}
			else if ((surface->bpp == 32) && (src.surface->bpp == 32))
			{
				const int src_stride = src.surface->stride;
				const uint8_t *srcptr = (const uint8_t *)src.surface->data + srcarea.left() * src.surface->bypp + srcarea.top() * src_stride;
				uint8_t *dstptr = (uint8_t *)surface->data + area.left() * surface->bypp + area.top() * surface->stride;
				const int width = area.width();
				const int height = area.height();
				const int src_height = srcarea.height();
				const int src_width = srcarea.width();
				if (flag & blitAlphaTest)
				{
					for (int y = 0; y < height; ++y)
					{
						const uint32_t *src_row_ptr = (uint32_t *)(srcptr + (((y * src_height) / height) * src_stride));
						uint32_t *dst = (uint32_t *)dstptr;
						for (int x = 0; x < width; ++x)
						{
							uint32_t pixel = src_row_ptr[(x * src_width) / width];
							if (pixel & 0x80000000)
								*dst = pixel;
							++dst;
						}
						dstptr += surface->stride;
					}
				}
				else if (flag & blitAlphaBlend)
				{
					for (int y = 0; y < height; ++y)
					{
						const gRGB *src_row_ptr = (gRGB *)(srcptr + (((y * src_height) / height) * src_stride));
						gRGB *dst = (gRGB *)dstptr;

						for (int x = 0; x < width; ++x)
						{
							const gRGB &src_pixel = src_row_ptr[(x * src_width) / width];
							dst->alpha_blend(src_pixel);
							++dst;
						}
						dstptr += surface->stride;
					}
				}
				else
				{
					for (int y = 0; y < height; ++y)
					{
						const uint32_t *src_row_ptr = (uint32_t *)(srcptr + (((y * src_height) / height) * src_stride));
						uint32_t *dst = (uint32_t *)dstptr;
						for (int x = 0; x < width; ++x)
						{
							*dst = src_row_ptr[(x * src_width) / width];
							++dst;
						}
						dstptr += surface->stride;
					}
				}
			}
			else
			{
				eWarning("[gPixmap] unimplemented: scale on non-accel surface %d->%d bpp", src.surface->bpp, surface->bpp);
			}
#ifdef GPIXMAP_DEBUG
			s.stop();
			eDebug("[gPixmap] [BLITBENCH] CPU scale blit %dx%d transparent %d (%d bytes) took %u us", pos.width(), pos.height(), src.surface->transparent, srcarea.surface() * src.surface->bypp, s.elapsed_us());
#ifdef GPIXMAP_CHECK_THRESHOLD
			if (accel)
			{
				adjustBlitThreshold(s.elapsed_us(), srcarea.surface() * src.surface->bypp);
			}
#endif
#endif
			continue;
		}

		if ((surface->bpp == 8) && (src.surface->bpp == 8))
		{
			uint8_t *srcptr = (uint8_t *)src.surface->data;
			uint8_t *dstptr = (uint8_t *)surface->data;

			srcptr += srcarea.left() * src.surface->bypp + srcarea.top() * src.surface->stride;
			dstptr += area.left() * surface->bypp + area.top() * surface->stride;
			if (flag & (blitAlphaTest | blitAlphaBlend))
			{
				for (int y = area.height(); y != 0; --y)
				{
					// no real alphatest yet
					int width = area.width();
					unsigned char *s = (unsigned char *)srcptr;
					unsigned char *d = (unsigned char *)dstptr;
					// use duff's device here!
					while (width--)
					{
						if (!*s)
						{
							s++;
							d++;
						}
						else
						{
							*d++ = *s++;
						}
					}
					srcptr += src.surface->stride;
					dstptr += surface->stride;
				}
			}
			else
			{
				int linesize = area.width() * surface->bypp;
				for (int y = area.height(); y != 0; --y)
				{
					memcpy(dstptr, srcptr, linesize);
					srcptr += src.surface->stride;
					dstptr += surface->stride;
				}
			}
		}
		else if ((surface->bpp == 32) && (src.surface->bpp == 32))
		{
			uint32_t *srcptr = (uint32_t *)src.surface->data;
			uint32_t *dstptr = (uint32_t *)surface->data;

			srcptr += srcarea.left() + srcarea.top() * src.surface->stride / 4;
			dstptr += area.left() + area.top() * surface->stride / 4;
			for (int y = area.height(); y != 0; --y)
			{
				if (flag & blitAlphaTest)
				{
					int width = area.width();
					uint32_t *src = srcptr;
					uint32_t *dst = dstptr;

					while (width--)
					{
						if (!((*src) & 0xFF000000))
						{
							src++;
							dst++;
						}
						else
							*dst++ = *src++;
					}
				}
				else if (flag & blitAlphaBlend)
				{
					int width = area.width();
					gRGB *src = (gRGB *)srcptr;
					gRGB *dst = (gRGB *)dstptr;
					while (width--)
					{
						dst->alpha_blend(*src++);
						++dst;
					}
				}
				else
					memcpy(dstptr, srcptr, area.width() * surface->bypp);
				srcptr = (uint32_t *)((uint8_t *)srcptr + src.surface->stride);
				dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
			}
		}
		else if ((surface->bpp == 32) && (src.surface->bpp == 8))
		{
			const uint8_t *srcptr = (uint8_t *)src.surface->data;
			uint8_t *dstptr = (uint8_t *)surface->data; // !!
			uint32_t pal[256];
			convert_palette(pal, src.surface->clut);

			srcptr += srcarea.left() * src.surface->bypp + srcarea.top() * src.surface->stride;
			dstptr += area.left() * surface->bypp + area.top() * surface->stride;
			const int width = area.width();
			for (int y = area.height(); y != 0; --y)
			{
				if (flag & blitAlphaTest)
					blit_8i_to_32_at((uint32_t *)dstptr, srcptr, pal, width);
				else if (flag & blitAlphaBlend)
					blit_8i_to_32_ab((gRGB *)dstptr, srcptr, (const gRGB *)pal, width);
				else
					blit_8i_to_32((uint32_t *)dstptr, srcptr, pal, width);
				srcptr += src.surface->stride;
				dstptr += surface->stride;
			}
		}
		else if ((surface->bpp == 16) && (src.surface->bpp == 8))
		{
			uint8_t *srcptr = (uint8_t *)src.surface->data;
			uint8_t *dstptr = (uint8_t *)surface->data; // !!
			uint32_t pal[256];

			for (int i = 0; i != 256; ++i)
			{
				uint32_t icol;
				if (src.surface->clut.data && (i < src.surface->clut.colors))
					icol = src.surface->clut.data[i].argb();
				else
					icol = 0x010101 * i;
#if BYTE_ORDER == LITTLE_ENDIAN
				pal[i] = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
				pal[i] = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
				pal[i] ^= 0xFF000000;
			}

			srcptr += srcarea.left() * src.surface->bypp + srcarea.top() * src.surface->stride;
			dstptr += area.left() * surface->bypp + area.top() * surface->stride;

			if (flag & blitAlphaBlend)
				eWarning("[gPixmap] ignore unsupported 8bpp -> 16bpp alphablend!");

			for (int y = 0; y < area.height(); y++)
			{
				int width = area.width();
				unsigned char *psrc = (unsigned char *)srcptr;
				uint16_t *dst = (uint16_t *)dstptr;
				if (flag & blitAlphaTest)
					blit_8i_to_16_at(dst, psrc, pal, width);
				else
					blit_8i_to_16(dst, psrc, pal, width);
				srcptr += src.surface->stride;
				dstptr += surface->stride;
			}
		}
		else if ((surface->bpp == 16) && (src.surface->bpp == 32))
		{
			uint8_t *srcptr = (uint8_t *)src.surface->data;
			uint8_t *dstptr = (uint8_t *)surface->data;

			srcptr += srcarea.left() * src.surface->bypp + srcarea.top() * src.surface->stride;
			dstptr += area.left() * surface->bypp + area.top() * surface->stride;

			for (int y = 0; y < area.height(); y++)
			{
				int width = area.width();
				uint32_t *srcp = (uint32_t *)srcptr;
				uint16_t *dstp = (uint16_t *)dstptr;

				if (flag & blitAlphaBlend)
				{
					while (width--)
					{
						if (!((*srcp) & 0xFF000000))
						{
							srcp++;
							dstp++;
						}
						else
						{
							gRGB icol = *srcp++;
#if BYTE_ORDER == LITTLE_ENDIAN
							uint32_t jcol = bswap_16(*dstp);
#else
							uint32_t jcol = *dstp;
#endif
							int bg_b = (jcol >> 8) & 0xF8;
							int bg_g = (jcol >> 3) & 0xFC;
							int bg_r = (jcol << 3) & 0xF8;

							int a = icol.a;
							int r = icol.r;
							int g = icol.g;
							int b = icol.b;

							r = ((r - bg_r) * a) / 255 + bg_r;
							g = ((g - bg_g) * a) / 255 + bg_g;
							b = ((b - bg_b) * a) / 255 + bg_b;

#if BYTE_ORDER == LITTLE_ENDIAN
							*dstp++ = bswap_16((b >> 3) << 11 | (g >> 2) << 5 | r >> 3);
#else
							*dstp++ = (b >> 3) << 11 | (g >> 2) << 5 | r >> 3;
#endif
						}
					}
				}
				else if (flag & blitAlphaTest)
				{
					while (width--)
					{
						if (!((*srcp) & 0xFF000000))
						{
							srcp++;
							dstp++;
						}
						else
						{
							uint32_t icol = *srcp++;
#if BYTE_ORDER == LITTLE_ENDIAN
							*dstp++ = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
							*dstp++ = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
						}
					}
				}
				else
				{
					while (width--)
					{
						uint32_t icol = *srcp++;
#if BYTE_ORDER == LITTLE_ENDIAN
						*dstp++ = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
						*dstp++ = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
					}
				}
				srcptr += src.surface->stride;
				dstptr += surface->stride;
			}
		}
		else
			eWarning("[gPixmap] cannot blit %dbpp from %dbpp", surface->bpp, src.surface->bpp);
#ifdef GPIXMAP_DEBUG
		s.stop();
		eDebug("[gPixmap] [BLITBENCH] cpu blit %dx%d transparent %d (%d bytes) took %u us", pos.width(), pos.height(), src.surface->transparent, srcarea.surface() * src.surface->bypp, s.elapsed_us());
#ifdef GPIXMAP_CHECK_THRESHOLD
		if (accel)
		{
			adjustBlitThreshold(s.elapsed_us(), srcarea.surface() * src.surface->bypp);
		}
#endif
#endif
	}
	if (accumulate)
	{
		gAccel::getInstance()->sync();
	}
}

#undef FIX

void gPixmap::mergePalette(const gPixmap &target)
{
	if ((!surface->clut.colors) || (!target.surface->clut.colors))
		return;

	gColor *lookup = new gColor[surface->clut.colors];

	for (int i = 0; i < surface->clut.colors; i++)
		lookup[i].color = target.surface->clut.findColor(surface->clut.data[i]);

	delete[] surface->clut.data;
	surface->clut.colors = target.surface->clut.colors;
	surface->clut.data = new gRGB[surface->clut.colors];
	memcpy(static_cast<void *>(surface->clut.data), target.surface->clut.data, sizeof(gRGB) * surface->clut.colors);

	uint8_t *dstptr = (uint8_t *)surface->data;

	for (int ay = 0; ay < surface->y; ay++)
	{
		for (int ax = 0; ax < surface->x; ax++)
			dstptr[ax] = lookup[dstptr[ax]];
		dstptr += surface->stride;
	}

	delete[] lookup;
}

static inline int sgn(int a)
{
	if (a < 0)
		return -1;
	else if (!a)
		return 0;
	else
		return 1;
}

void gPixmap::line(const gRegion &clip, ePoint start, ePoint dst, gColor color)
{
	uint32_t col = color;
	if (surface->bpp != 8)
	{
		if (surface->clut.data && color < surface->clut.colors)
			col = surface->clut.data[color].argb();
		else
			col = 0x10101 * color;
		col ^= 0xFF000000;
	}

	if (surface->bpp == 16)
	{
#if BYTE_ORDER == LITTLE_ENDIAN
		col = bswap_16(((col & 0xFF) >> 3) << 11 | ((col & 0xFF00) >> 10) << 5 | (col & 0xFF0000) >> 19);
#else
		col = ((col & 0xFF) >> 3) << 11 | ((col & 0xFF00) >> 10) << 5 | (col & 0xFF0000) >> 19;
#endif
	}
	line(clip, start, dst, col);
}

void gPixmap::line(const gRegion &clip, ePoint start, ePoint dst, gRGB color)
{
	uint32_t col;
	col = color.argb();
	col ^= 0xFF000000;
	line(clip, start, dst, col);
}

void gPixmap::line(const gRegion &clip, ePoint start, ePoint dst, unsigned int color)
{
	if (clip.rects.empty())
		return;

	uint8_t *srf8 = 0;
	uint16_t *srf16 = 0;
	uint32_t *srf32 = 0;
	int stride = surface->stride;

	switch (surface->bpp)
	{
	case 8:
		srf8 = (uint8_t *)surface->data;
		break;
	case 16:
		srf16 = (uint16_t *)surface->data;
		stride /= 2;
		break;
	case 32:
		srf32 = (uint32_t *)surface->data;
		stride /= 4;
		break;
	}

	int xa = start.x(), ya = start.y(), xb = dst.x(), yb = dst.y();
	int dx, dy, x, y, s1, s2, e, temp, swap, i;
	dy = abs(yb - ya);
	dx = abs(xb - xa);
	s1 = sgn(xb - xa);
	s2 = sgn(yb - ya);
	x = xa;
	y = ya;
	if (dy > dx)
	{
		temp = dx;
		dx = dy;
		dy = temp;
		swap = 1;
	}
	else
		swap = 0;
	e = 2 * dy - dx;

	int lasthit = 0;
	for(i=1; i<=dx; i++)
	{
		/* i don't like this clipping loop, but the only */
		/* other choice i see is to calculate the intersections */
		/* before iterating through the pixels. */

		/* one could optimize this because of the ordering */
		/* of the bands. */

		lasthit = 0;
		int a = lasthit;

			/* if last pixel was invisble, first check bounding box */
		if (a == -1)
		{
				/* check if we just got into the bbox again */
			if (clip.extends.contains(x, y))
				lasthit = a = 0;
			else
				goto fail;
		} 
		else if (!clip.rects[a].contains(x, y))
		{
			do
			{
				++a;
				if ((unsigned int)a == clip.rects.size())
					a = 0;
				if (a == lasthit)
				{
					goto fail;
					lasthit = -1;
				}
			} while (!clip.rects[a].contains(x, y));
			lasthit = a;
		}

		if (srf8)
			srf8[y * stride + x] = color;
		else if (srf16)
			srf16[y * stride + x] = color;
		else
			srf32[y * stride + x] = color;
fail:
		while (e>=0)
		{
			if (swap==1)
				x+=s1;
			else
				y+=s2;
			e-=2*dx;
		}

		if (swap==1)
			y+=s2;
		else
			x+=s1;
		e+=2*dy;
	}
}

gColor gPalette::findColor(const gRGB rgb) const
{
	/* grayscale? */
	if (!data)
		return (rgb.r + rgb.g + rgb.b) / 3;

	if (rgb.a == 255) /* Fully transparent, then RGB does not matter */
	{
		for (int t = 0; t < colors; t++)
			if (data[t].a == 255)
				return t;
	}

	int difference = 1 << 30, best_choice = 0;
	for (int t = 0; t < colors; t++)
	{
		int ttd;
		int td = (signed)(rgb.r - data[t].r);
		td *= td;
		td *= (255 - data[t].a);
		ttd = td;
		if (ttd >= difference)
			continue;
		td = (signed)(rgb.g - data[t].g);
		td *= td;
		td *= (255 - data[t].a);
		ttd += td;
		if (ttd >= difference)
			continue;
		td = (signed)(rgb.b - data[t].b);
		td *= td;
		td *= (255 - data[t].a);
		ttd += td;
		if (ttd >= difference)
			continue;
		td = (signed)(rgb.a - data[t].a);
		td *= td;
		td *= 255;
		ttd += td;
		if (ttd >= difference)
			continue;
		if (!ttd)
			return t;
		difference = ttd;
		best_choice = t;
	}
	return best_choice;
}

DEFINE_REF(gPixmap);

gPixmap::~gPixmap()
{
	if (on_dispose)
		on_dispose(this);
	if (surface)
		delete (gSurface *)surface;
}

static void donot_delete_surface(gPixmap *pixmap)
{
	pixmap->surface = NULL;
}

gPixmap::gPixmap(gUnmanagedSurface *surface):
	surface(surface),
	on_dispose(donot_delete_surface)
{
}

gPixmap::gPixmap(eSize size, int bpp, int accel):
	surface(new gSurface(size.width(), size.height(), bpp, accel)),
	on_dispose(NULL)
{
}

gPixmap::gPixmap(int width, int height, int bpp, gPixmapDisposeCallback call_on_dispose, int accel):
	surface(new gSurface(width, height, bpp, accel)),
	on_dispose(call_on_dispose)
{
}
