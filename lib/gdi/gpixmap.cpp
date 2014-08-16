#include <cstdlib>
#include <cstring>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/region.h>
#include <lib/gdi/accel.h>
#include <byteswap.h>

#ifndef BYTE_ORDER
#error "no BYTE_ORDER defined!"
#endif

// #define GPIXMAP_DEBUG

#ifdef GPIXMAP_DEBUG
#	include "../base/benchmark.h"
#endif

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
			return (surface->y * surface->stride) > 12000;
		case 32:
			return (surface->y * surface->stride) > 48000;
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
				eDebug("ERROR: accelAlloc failed");
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
	for (i=0; i<region.rects.size(); ++i)
	{
		const eRect &area = region.rects[i];
		if (area.empty())
			continue;

		if (surface->bpp == 8)
		{
			for (int y=area.top(); y<area.bottom(); y++)
		 		memset(((__u8*)surface->data)+y*surface->stride+area.left(), color.color, area.width());
		} else if (surface->bpp == 16)
		{
			uint32_t icol;

			if (surface->clut.data && color < surface->clut.colors)
				icol=surface->clut.data[color].argb();
			else
				icol=0x10101*color;
#if BYTE_ORDER == LITTLE_ENDIAN
			uint16_t col = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
			uint16_t col = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
			for (int y=area.top(); y<area.bottom(); y++)
			{
				uint16_t *dst=(uint16_t*)(((uint8_t*)surface->data)+y*surface->stride+area.left()*surface->bypp);
				int x=area.width();
				while (x--)
					*dst++=col;
			}
		} else if (surface->bpp == 32)
		{
			uint32_t col;

			if (surface->clut.data && color < surface->clut.colors)
				col = surface->clut.data[color].argb();
			else
				col = 0x10101 * color;

			col^=0xFF000000;

			if (surface->data_phys)
				if (!gAccel::getInstance()->fill(surface,  area, col))
					continue;

			for (int y=area.top(); y<area.bottom(); y++)
			{
				uint32_t *dst=(uint32_t*)(((uint8_t*)surface->data)+y*surface->stride+area.left()*surface->bypp);
				int x=area.width();
				while (x--)
					*dst++=col;
			}
		}	else
			eWarning("couldn't fill %d bpp", surface->bpp);
	}
}

void gPixmap::fill(const gRegion &region, const gRGB &color)
{
	unsigned int i;
	for (i=0; i<region.rects.size(); ++i)
	{
		const eRect &area = region.rects[i];
		if (area.empty())
			continue;

		if (surface->bpp == 32)
		{
			uint32_t col;

			col = color.argb();
			col^=0xFF000000;

#ifdef GPIXMAP_DEBUG
			Stopwatch s;
#endif
			if (surface->data_phys && (area.surface() > 20000))
				if (!gAccel::getInstance()->fill(surface,  area, col)) {
#ifdef GPIXMAP_DEBUG
					s.stop();
					eDebug("[BLITBENCH] accel fill %dx%d took %u us", area.width(), area.height(), s.elapsed_us());
#endif
					continue;
				}

			for (int y=area.top(); y<area.bottom(); y++)
			{
				uint32_t *dst=(uint32_t*)(((uint8_t*)surface->data)+y*surface->stride+area.left()*surface->bypp);
				int x=area.width();
				while (x--)
					*dst++=col;
			}
#ifdef GPIXMAP_DEBUG
			s.stop();
			eDebug("[BLITBENCH] cpu fill %dx%d took %u us", area.width(), area.height(), s.elapsed_us());
#endif
		} else if (surface->bpp == 16)
		{
			uint32_t icol = color.argb();
#if BYTE_ORDER == LITTLE_ENDIAN
			uint16_t col = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
			uint16_t col = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
			for (int y=area.top(); y<area.bottom(); y++)
			{
				uint16_t *dst=(uint16_t*)(((uint8_t*)surface->data)+y*surface->stride+area.left()*surface->bypp);
				int x=area.width();
				while (x--)
					*dst++=col;
			}
		}	else
			eWarning("couldn't rgbfill %d bpp", surface->bpp);
	}
}

static inline void blit_8i_to_32(uint32_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
		*dst++=pal[*src++];
}

static inline void blit_8i_to_32_at(uint32_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
	{
		if (!(pal[*src]&0x80000000))
		{
			src++;
			dst++;
		} else
			*dst++=pal[*src++];
	}
}

static inline void blit_8i_to_16(uint16_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
		*dst++=pal[*src++] & 0xFFFF;
}

static inline void blit_8i_to_16_at(uint16_t *dst, const uint8_t *src, const uint32_t *pal, int width)
{
	while (width--)
	{
		if (!(pal[*src]&0x80000000))
		{
			src++;
			dst++;
		} else
			*dst++=pal[*src++] & 0xFFFF;
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

static void convert_palette(uint32_t* pal, const gPalette& clut)
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
	for(; i != 256; ++i)
	{
		pal[i] = (0x010101*i) | 0xFF000000;
	}
}

#define FIX 0x10000

void gPixmap::blit(const gPixmap &src, const eRect &_pos, const gRegion &clip, int flag)
{
	bool accel = (surface->data_phys && src.surface->data_phys);
//	eDebug("blit: -> %d,%d+%d,%d -> %d,%d+%d,%d, flags=0x%x, accel=%d",
//		_pos.x(), _pos.y(), _pos.width(), _pos.height(),
//		clip.extends.x(), clip.extends.y(), clip.extends.width(), clip.extends.height(),
//		flag, accel);
	eRect pos = _pos;

//	eDebug("source size: %d %d", src.size().width(), src.size().height());

	if (!(flag & blitScale)) /* pos' size is valid only when scaling */
		pos = eRect(pos.topLeft(), src.size());
	else if (pos.size() == src.size()) /* no scaling required */
		flag &= ~blitScale;

	int scale_x = FIX, scale_y = FIX;

	if (flag & blitScale)
	{
		ASSERT(src.size().width());
		ASSERT(src.size().height());
		scale_x = pos.size().width() * FIX / src.size().width();
		scale_y = pos.size().height() * FIX / src.size().height();
		if (flag & blitKeepAspectRatio)
		{
			if (scale_x > scale_y)
			{
				pos = eRect(ePoint(pos.x() + (scale_x - scale_y) * pos.width() / (2 * FIX), pos.y()),
					eSize(src.size().width() * pos.height() / src.size().height(), pos.height()));
				scale_x = scale_y;

			}
			else
			{
				pos = eRect(ePoint(pos.x(), pos.y()  + (scale_y - scale_x) * pos.height() / (2 * FIX)),
					eSize(pos.width(), src.size().height() * pos.width() / src.size().width()));
				scale_y = scale_x;
			}
		}
	}

//	eDebug("SCALE %x %x", scale_x, scale_y);

	for (unsigned int i=0; i<clip.rects.size(); ++i)
	{
//		eDebug("clip rect: %d %d %d %d", clip.rects[i].x(), clip.rects[i].y(), clip.rects[i].width(), clip.rects[i].height());
		eRect area = pos; /* pos is the virtual (pre-clipping) area on the dest, which can be larger/smaller than src if scaling is enabled */
		area&=clip.rects[i];
		area&=eRect(ePoint(0, 0), size());

		if (area.empty())
			continue;

		eRect srcarea = area;
		srcarea.moveBy(-pos.x(), -pos.y());

//		eDebug("srcarea before scale: %d %d %d %d",
//			srcarea.x(), srcarea.y(), srcarea.width(), srcarea.height());

		if (flag & blitScale)
			srcarea = eRect(srcarea.x() * FIX / scale_x, srcarea.y() * FIX / scale_y, srcarea.width() * FIX / scale_x, srcarea.height() * FIX / scale_y);

//		eDebug("srcarea after scale: %d %d %d %d",
//			srcarea.x(), srcarea.y(), srcarea.width(), srcarea.height());

		if (accel)
		{
			/* we have hardware acceleration for this blit operation */
			if (flag & (blitAlphaTest | blitAlphaBlend))
			{
				/* alpha blending is requested */
				if (gAccel::getInstance()->hasAlphaBlendingSupport())
				{
					/* Hardware alpha blending is broken on the few
					 * boxes that support it, so only use it
					 * when scaling */
					if (flag & blitScale)
						accel = true;
					else if (flag & blitAlphaTest) /* Alpha test only on 8-bit */
						accel = (src.surface->bpp == 8);
					else
						accel = false;
				}
				else
				{
					/* our hardware does not support alphablending */
					accel = false;
				}
			}
		}

#ifdef GPIXMAP_DEBUG
		Stopwatch s;
#endif
		if (accel) {
			if (!gAccel::getInstance()->blit(surface, src.surface, area, srcarea, flag)) {
#ifdef GPIXMAP_DEBUG
				s.stop();
				eDebug("[BLITBENCH] accel blit took %u us", s.elapsed_us());
#endif
				continue;
			}
		}

		if (flag & blitScale)
		{
			if ((surface->bpp == 32) && (src.surface->bpp==8))
			{
				const uint8_t *srcptr = (uint8_t*)src.surface->data;
				uint8_t *dstptr=(uint8_t*)surface->data; // !!
				uint32_t pal[256];
				convert_palette(pal, src.surface->clut);

				const int src_stride = src.surface->stride;
				srcptr += srcarea.left()*src.surface->bypp + srcarea.top()*src_stride;
				dstptr += area.left()*surface->bypp + area.top()*surface->stride;
				const int width = area.width();
				const int height = area.height();
				const int src_height = srcarea.height();
				const int src_width = srcarea.width();
				if (flag & blitAlphaTest)
				{
					for (int y = 0; y < height; ++y)
					{
						const uint8_t *src_row_ptr = srcptr + (((y * src_height) / height) * src_stride);
						uint32_t *dst = (uint32_t*)dstptr;
						for (int x = 0; x < width; ++x)
						{
							uint32_t pixel = pal[src_row_ptr[(x *src_width) / width]];
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
						gRGB *dst = (gRGB*)dstptr;
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
						uint32_t *dst = (uint32_t*)dstptr;
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
				const uint8_t* srcptr = (const uint8_t*)src.surface->data + srcarea.left()*src.surface->bypp + srcarea.top()*src_stride;
				uint8_t* dstptr = (uint8_t*)surface->data + area.left()*surface->bypp + area.top()*surface->stride;
				const int width = area.width();
				const int height = area.height();
				const int src_height = srcarea.height();
				const int src_width = srcarea.width();
				if (flag & blitAlphaTest)
				{
					for (int y = 0; y < height; ++y)
					{
						const uint32_t *src_row_ptr = (uint32_t*)(srcptr + (((y * src_height) / height) * src_stride));
						uint32_t *dst = (uint32_t*)dstptr;
						for (int x = 0; x < width; ++x)
						{
							uint32_t pixel = src_row_ptr[(x *src_width) / width];
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
						gRGB *dst = (gRGB*)dstptr;
						for (int x = 0; x < width; ++x)
						{
							dst->alpha_blend(src_row_ptr[(x * src_width) / width]);
							++dst;
						}
						dstptr += surface->stride;
					}
				}
				else
				{
					for (int y = 0; y < height; ++y)
					{
						const uint32_t *src_row_ptr = (uint32_t*)(srcptr + (((y * src_height) / height) * src_stride));
						uint32_t *dst = (uint32_t*)dstptr;
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
				eWarning("unimplemented: scale on non-accel surface %d->%d bpp", src.surface->bpp, surface->bpp);
			}
#ifdef GPIXMAP_DEBUG
			s.stop();
			eDebug("[BLITBENCH] CPU scale blit took %u us", s.elapsed_us());
#endif
			continue;
		}

		if ((surface->bpp == 8) && (src.surface->bpp == 8))
		{
			uint8_t *srcptr=(uint8_t*)src.surface->data;
			uint8_t *dstptr=(uint8_t*)surface->data;

			srcptr+=srcarea.left()*src.surface->bypp+srcarea.top()*src.surface->stride;
			dstptr+=area.left()*surface->bypp+area.top()*surface->stride;
			if (flag & (blitAlphaTest|blitAlphaBlend))
			{
				for (int y = area.height(); y != 0; --y)
				{
					// no real alphatest yet
					int width=area.width();
					unsigned char *s = (unsigned char*)srcptr;
					unsigned char *d = (unsigned char*)dstptr;
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
				int linesize = area.width()*surface->bypp;
				for (int y = area.height(); y != 0; --y)
				{
					memcpy(dstptr, srcptr, linesize);
					srcptr += src.surface->stride;
					dstptr += surface->stride;
				}
			}
		}
		else if ((surface->bpp == 32) && (src.surface->bpp==32))
		{
			uint32_t *srcptr=(uint32_t*)src.surface->data;
			uint32_t *dstptr=(uint32_t*)surface->data;

			srcptr+=srcarea.left()+srcarea.top()*src.surface->stride/4;
			dstptr+=area.left()+area.top()*surface->stride/4;
			for (int y = area.height(); y != 0; --y)
			{
				if (flag & blitAlphaTest)
				{
					int width=area.width();
					unsigned long *src=(unsigned long*)srcptr;
					unsigned long *dst=(unsigned long*)dstptr;
					while (width--)
					{
						if (!((*src)&0xFF000000))
						{
							src++;
							dst++;
						} else
							*dst++=*src++;
					}
				} else if (flag & blitAlphaBlend)
				{
					int width = area.width();
					gRGB *src = (gRGB*)srcptr;
					gRGB *dst = (gRGB*)dstptr;
					while (width--)
					{
						dst->alpha_blend(*src++);
						++dst;
					}
				} else
					memcpy(dstptr, srcptr, area.width()*surface->bypp);
				srcptr = (uint32_t*)((uint8_t*)srcptr + src.surface->stride);
				dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
			}
		}
		else if ((surface->bpp == 32) && (src.surface->bpp==8))
		{
			const uint8_t *srcptr = (uint8_t*)src.surface->data;
			uint8_t *dstptr=(uint8_t*)surface->data; // !!
			uint32_t pal[256];
			convert_palette(pal, src.surface->clut);

			srcptr+=srcarea.left()*src.surface->bypp+srcarea.top()*src.surface->stride;
			dstptr+=area.left()*surface->bypp+area.top()*surface->stride;
			const int width=area.width();
			for (int y = area.height(); y != 0; --y)
			{
				if (flag & blitAlphaTest)
					blit_8i_to_32_at((uint32_t*)dstptr, srcptr, pal, width);
				else if (flag & blitAlphaBlend)
					blit_8i_to_32_ab((gRGB*)dstptr, srcptr, (const gRGB*)pal, width);
				else
					blit_8i_to_32((uint32_t*)dstptr, srcptr, pal, width);
				srcptr += src.surface->stride;
				dstptr += surface->stride;
			}
		}
		else if ((surface->bpp == 16) && (src.surface->bpp==8))
		{
			uint8_t *srcptr=(uint8_t*)src.surface->data;
			uint8_t *dstptr=(uint8_t*)surface->data; // !!
			uint32_t pal[256];

			for (int i=0; i != 256; ++i)
			{
				uint32_t icol;
				if (src.surface->clut.data && (i<src.surface->clut.colors))
					icol = src.surface->clut.data[i].argb();
				else
					icol=0x010101*i;
#if BYTE_ORDER == LITTLE_ENDIAN
				pal[i] = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
				pal[i] = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
				pal[i]^=0xFF000000;
			}

			srcptr+=srcarea.left()*src.surface->bypp+srcarea.top()*src.surface->stride;
			dstptr+=area.left()*surface->bypp+area.top()*surface->stride;

			if (flag & blitAlphaBlend)
				eWarning("ignore unsupported 8bpp -> 16bpp alphablend!");

			for (int y=0; y<area.height(); y++)
			{
				int width=area.width();
				unsigned char *psrc=(unsigned char*)srcptr;
				uint16_t *dst=(uint16_t*)dstptr;
				if (flag & blitAlphaTest)
					blit_8i_to_16_at(dst, psrc, pal, width);
				else
					blit_8i_to_16(dst, psrc, pal, width);
				srcptr+=src.surface->stride;
				dstptr+=surface->stride;
			}
		}
		else if ((surface->bpp == 16) && (src.surface->bpp==32))
		{
			uint8_t *srcptr=(uint8_t*)src.surface->data;
			uint8_t *dstptr=(uint8_t*)surface->data;

			srcptr+=srcarea.left()+srcarea.top()*src.surface->stride;
			dstptr+=area.left()+area.top()*surface->stride;

			if (flag & blitAlphaBlend)
				eWarning("ignore unsupported 32bpp -> 16bpp alphablend!");

			for (int y=0; y<area.height(); y++)
			{
				int width=area.width();
				uint32_t *srcp=(uint32_t*)srcptr;
				uint16_t *dstp=(uint16_t*)dstptr;

				if (flag & blitAlphaTest)
				{
					while (width--)
					{
						if (!((*srcp)&0xFF000000))
						{
							srcp++;
							dstp++;
						} else
						{
							uint32_t icol = *srcp++;
#if BYTE_ORDER == LITTLE_ENDIAN
							*dstp++ = bswap_16(((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19);
#else
							*dstp++ = ((icol & 0xFF) >> 3) << 11 | ((icol & 0xFF00) >> 10) << 5 | (icol & 0xFF0000) >> 19;
#endif
						}
					}
				} else
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
				srcptr+=src.surface->stride;
				dstptr+=surface->stride;
			}
		}
		else
			eWarning("cannot blit %dbpp from %dbpp", surface->bpp, src.surface->bpp);
#ifdef GPIXMAP_DEBUG
		s.stop();
		eDebug("[BLITBENCH] cpu blit took %u us", s.elapsed_us());
#endif
	}
}

#undef FIX

void gPixmap::mergePalette(const gPixmap &target)
{
	if ((!surface->clut.colors) || (!target.surface->clut.colors))
		return;

	gColor *lookup=new gColor[surface->clut.colors];

	for (int i=0; i<surface->clut.colors; i++)
		lookup[i].color=target.surface->clut.findColor(surface->clut.data[i]);

	delete [] surface->clut.data;
	surface->clut.colors=target.surface->clut.colors;
	surface->clut.data=new gRGB[surface->clut.colors];
	memcpy(surface->clut.data, target.surface->clut.data, sizeof(gRGB)*surface->clut.colors);

	uint8_t *dstptr=(uint8_t*)surface->data;

	for (int ay=0; ay<surface->y; ay++)
	{
		for (int ax=0; ax<surface->x; ax++)
			dstptr[ax]=lookup[dstptr[ax]];
		dstptr+=surface->stride;
	}

	delete [] lookup;
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
			col = 0x10101*color;
		col^=0xFF000000;
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
	col^=0xFF000000;
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
			srf8 = (uint8_t*)surface->data;
			break;
		case 16:
			srf16 = (uint16_t*)surface->data;
			stride /= 2;
			break;
		case 32:
			srf32 = (uint32_t*)surface->data;
			stride /= 4;
			break;
	}

	int xa = start.x(), ya = start.y(), xb = dst.x(), yb = dst.y();
	int dx, dy, x, y, s1, s2, e, temp, swap, i;
	dy=abs(yb-ya);
	dx=abs(xb-xa);
	s1=sgn(xb-xa);
	s2=sgn(yb-ya);
	x=xa;
	y=ya;
	if (dy>dx)
	{
		temp=dx;
		dx=dy;
		dy=temp;
		swap=1;
	} else
		swap=0;
	e = 2*dy-dx;

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
		} else if (!clip.rects[a].contains(x, y))
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
		for (int t=0; t<colors; t++)
			if (data[t].a == 255)
				return t;
	}

	int difference=1<<30, best_choice=0;
	for (int t=0; t<colors; t++)
	{
		int ttd;
		int td=(signed)(rgb.r-data[t].r); td*=td; td*=(255-data[t].a);
		ttd=td;
		if (ttd>=difference)
			continue;
		td=(signed)(rgb.g-data[t].g); td*=td; td*=(255-data[t].a);
		ttd+=td;
		if (ttd>=difference)
			continue;
		td=(signed)(rgb.b-data[t].b); td*=td; td*=(255-data[t].a);
		ttd+=td;
		if (ttd>=difference)
			continue;
		td=(signed)(rgb.a-data[t].a); td*=td; td*=255;
		ttd+=td;
		if (ttd>=difference)
			continue;
		if (!ttd)
			return t;
		difference=ttd;
		best_choice=t;
	}
	return best_choice;
}

DEFINE_REF(gPixmap);

gPixmap::~gPixmap()
{
	if (on_dispose)
		on_dispose(this);
	if (surface)
		delete (gSurface*)surface;
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
