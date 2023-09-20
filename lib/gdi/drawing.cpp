/*
Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License

Copyright (c) 2023 openATV

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
1. Non-Commercial Use: You may not use the Software or any derivative works
   for commercial purposes without obtaining explicit permission from the
   copyright holder.
2. Share Alike: If you distribute or publicly perform the Software or any
   derivative works, you must do so under the same license terms, and you
   must make the source code of any derivative works available to the
   public.
3. Attribution: You must give appropriate credit to the original author(s)
   of the Software by including a prominent notice in your derivative works.
THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more details about the CC BY-NC-SA 4.0 License, please visit:
https://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#include <lib/gdi/drawing.h>
#include <lib/gdi/region.h>

void duplicate_32fc(uint32_t *out, const uint32_t in, size_t size) {

	size_t n = 1;
	size_t last_n = 0;

	if (n < 1)
		return;

	//Copy the first one
	out[0] = in;

	//Double the size of the copy for each copy
	while (n * 2 <= size)
	{
		memcpy(&out[n], out, n * sizeof(uint32_t));
		last_n = n;
		n = n * 2;
	}

	//Copy the tail
	if (last_n < size) {
		memcpy(&out[last_n], out, (size - last_n) * sizeof(uint32_t));
	}
}

uint32_t* createGradientBuffer(int graSize, const gRGB &startColor, const gRGB &endColor) {
	uint32_t* gradientBuf = (uint32_t*)malloc(graSize * sizeof(uint32_t));

	uint32_t start_col = startColor.argb();
	start_col^=0xFF000000;

	uint32_t end_col = endColor.argb();
	end_col^=0xFF000000;

	uint8_t start_a = (uint8_t)((start_col & 0xFF000000) >> 24);
	uint8_t start_r  = (uint8_t)((start_col & 0x00FF0000) >> 16);
	uint8_t start_g  = (uint8_t)((start_col & 0x0000FF00) >>  8);
	uint8_t start_b  = (uint8_t) (start_col & 0x000000FF);

	uint8_t end_a = (uint8_t)((end_col & 0xFF000000) >> 24);
	uint8_t end_r  = (uint8_t)((end_col & 0x00FF0000) >> 16);
	uint8_t end_g  = (uint8_t)((end_col & 0x0000FF00) >>  8);
	uint8_t end_b  = (uint8_t) (end_col & 0x000000FF);

	float steps = (float)graSize;
	float aStep = (float)(end_a - start_a) / steps;
	float rStep = (float)(end_r - start_r) / steps;
	float gStep = (float)(end_g - start_g) / steps;
	float bStep = (float)(end_b - start_b) / steps;

	if (gradientBuf != nullptr) {
		for (int x = 0; x < graSize; x++) {
			uint8_t a = (uint8_t)(start_a + aStep * x);
			uint8_t r  = (uint8_t)(start_r + rStep * x);
			uint8_t g  = (uint8_t)(start_g + gStep * x);
			uint8_t b  = (uint8_t)(start_b + bStep * x);
			gradientBuf[x] = ((uint32_t)a << 24) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
		}
	}
	return gradientBuf;
}

static void blendPixelRounded(uint32_t *dst, const uint32_t *src, const double alpha)
{
	
	if (!((*src)&0xFF000000))
		return;
	
	uint8_t r = (*src >> 24) & 0xFF;
	uint8_t g = (*src >> 16) & 0xFF;
	uint8_t b = (*src >> 8) & 0xFF;
	uint8_t a = (*src >> 0) & 0xFF;

	// Apply alpha blending
	uint8_t newR = r * alpha;
	uint8_t newG = g * alpha;
	uint8_t newB = b * alpha;
	uint8_t newA = a * alpha;

	// Combine the new color with the existing pixel color using alpha blending
	uint8_t oldR = (*dst >> 24) & 0xFF;
	uint8_t oldG = (*dst >> 16) & 0xFF;
	uint8_t oldB = (*dst >> 8) & 0xFF;
	uint8_t oldA = (*dst >> 0) & 0xFF;

	uint8_t finalR = newR + oldR * (1 - alpha);
	uint8_t finalG = newG + oldG * (1 - alpha);
	uint8_t finalB = newB + oldB * (1 - alpha);
	uint8_t finalA = newA + oldA * (1 - alpha);

	*dst = (finalR << 24) | (finalG << 16) | (finalB << 8) | finalA;
}

void drawAngleTl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *dst=(uint32_t*)(((uint8_t*)surface->data)+y*surface->stride+cornerRect.left()*surface->bypp);

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topLeftCornerDRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.topLeftCornerSRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, s, alpha);
			}
			++dst;
		}
	}
}

void drawAngleTr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *dst=(uint32_t*)(((uint8_t*)surface->data)+y*surface->stride+cornerRect.left()*surface->bypp);

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
			dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topRightCornerDRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.topRightCornerSRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, s, alpha);
			}
			++dst;
		}
	}
}

void drawAngleBl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *dst=(uint32_t*)(((uint8_t*)surface->data)+y*surface->stride+cornerRect.left()*surface->bypp);

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomLeftCornerDRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.bottomLeftCornerSRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, s, alpha);
			}
			++dst;
		}
	}
}

void drawAngleBr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *dst=(uint32_t*)(((uint8_t*)surface->data)+y*surface->stride+cornerRect.left()*surface->bypp);

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
			dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomRightCornerDRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.bottomRightCornerSRadius)
			{
				const uint32_t *s = src + (direction ==  1 ? yInOriginalArea : xInOriginalArea);
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, s, alpha);
			}
			++dst;
		}
	}
}

void drawAngle32Tl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	uint32_t *srcptr=(uint32_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride/4;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!((*src)&0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++=*src++;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{

					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
					src++;
					dst++;
				}
				else
					*dst++=*src++;
				continue;
			}
			else if (squared_dst < cornerData.topLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
			++dst;
			++src;
		}
		srcptr = (uint32_t*)((uint8_t*)srcptr + pixmap.surface->stride);
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle32Tr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	uint32_t *srcptr=(uint32_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride/4;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{

			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
			dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!((*src)&0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++=*src++;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
					src++;
					dst++;
				}
				else
					*dst++=*src++;
				continue;
			}
			else if (squared_dst < cornerData.topRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
			++dst;
			++src;
		}
		srcptr = (uint32_t*)((uint8_t*)srcptr + pixmap.surface->stride);
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle32Bl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	uint32_t *srcptr=(uint32_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride/4;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!((*src)&0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++=*src++;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
					src++;
					dst++;
				}
				else
					*dst++=*src++;
				continue;
			}
			else if (squared_dst < cornerData.bottomLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
			++dst;
			++src;
		}
		srcptr = (uint32_t*)((uint8_t*)srcptr + pixmap.surface->stride);
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle32Br(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	uint32_t *srcptr=(uint32_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride/4;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		uint32_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
			dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!((*src)&0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++=*src++;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
					src++;
					dst++;
				}
				else
					*dst++=*src++;
				continue;
			}
			else if (squared_dst < cornerData.bottomRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
			++dst;
			++src;
		}
		srcptr = (uint32_t*)((uint8_t*)srcptr + pixmap.surface->stride);
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle32ScaledTl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();
	for (int y = cornerRect.top(); y < cornerRect.bottom(); ++y) {
		int yInOriginalArea = y - area.top();
		for (int x = cornerRect.left(); x < cornerRect.right(); ++x) {
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;
			int xInOriginalArea = x - area.left();

			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t *src = (uint32_t*)src_pixel;

			dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if ((*src) & 0x80000000)
						*dst=*src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
				}
				else
					memcpy(dst_pixel, src_pixel, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.topLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
		}
	}
}

void drawAngle32ScaledTr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();

	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;

			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t *src = (uint32_t*)src_pixel;

			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
			dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if ((*src) & 0x80000000)
						*dst=*src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
				}
				else
					memcpy(dst_pixel, src_pixel, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.topRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
		}
	}
}

void drawAngle32ScaledBl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();

	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;

			int xInOriginalArea = x - area.left();

			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t *src = (uint32_t*)src_pixel;

			dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if ((*src) & 0x80000000)
						*dst=*src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
				}
				else
					memcpy(dst_pixel, src_pixel, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.bottomLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
		}
	}
}

void drawAngle32ScaledBr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();

	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;

			int xInOriginalArea = x - area.left();
			
			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t *src = (uint32_t*)src_pixel;

			dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
			dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if ((*src) & 0x80000000)
						*dst=*src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gSrc = (gRGB*)src;
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(*gSrc);
				}
				else
					memcpy(dst_pixel, src_pixel, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.bottomRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, src, alpha);
			}
		}
	}
}

void drawAngle8Tl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		const uint8_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!(pal[*src] & 0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(pal[*src++]);
					dst++;
				}
				else
					*dst++ = pal[*src++];
				continue;
			}
			else if (squared_dst < cornerData.topLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &pal[*src], alpha);
			}
			++dst;
			++src;
		}
		srcptr += pixmap.surface->stride;
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle8Tr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		const uint8_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
			dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!(pal[*src] & 0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(pal[*src++]);
					dst++;
				}
				else
					*dst++ = pal[*src++];
				continue;
			}
			else if (squared_dst < cornerData.topRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &pal[*src], alpha);
			}
			++dst;
			++src;
		}
		srcptr += pixmap.surface->stride;
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle8Bl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		const uint8_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!(pal[*src] & 0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(pal[*src++]);
					dst++;
				}
				else
					*dst++ = pal[*src++];
				continue;
			}
			else if (squared_dst < cornerData.bottomLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &pal[*src], alpha);
			}
			++dst;
			++src;
		}
		srcptr += pixmap.surface->stride;
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle8Br(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t*)pixmap.surface->data;
	uint32_t *dstptr=(uint32_t*)surface->data;

	srcptr+=(cornerRect.left() - area.left())+(cornerRect.top() - area.top())*pixmap.surface->stride;
	dstptr+=cornerRect.left()+cornerRect.top()*surface->stride/4;
	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();
		const uint8_t *src = srcptr;
		uint32_t *dst = dstptr;

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
			dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (!(pal[*src] & 0xFF000000))
					{
						src++;
						dst++;
					} else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(pal[*src++]);
					dst++;
				}
				else
					*dst++ = pal[*src++];
				continue;
			}
			else if (squared_dst < cornerData.bottomRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &pal[*src], alpha);
			}
			++dst;
			++src;
		}
		srcptr += pixmap.surface->stride;
		dstptr = (uint32_t*)((uint8_t*)dstptr + surface->stride);
	}
}

void drawAngle8ScaledTl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();
	for (int y = cornerRect.top(); y < cornerRect.bottom(); ++y) {
		int yInOriginalArea = y - area.top();
		for (int x = cornerRect.left(); x < cornerRect.right(); ++x) {
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;
			int xInOriginalArea = x - area.left();

			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t src = pal[*src_pixel];

			dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (src & 0x80000000)
						*dst=src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(src);
				}
				else
					memcpy(dst_pixel, &src, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.topLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &src, alpha);
			}
		}
	}
}

void drawAngle8ScaledTr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();

	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;

			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t src = pal[*src_pixel];

			int xInOriginalArea = x - area.left();
			dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
			dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (src & 0x80000000)
						*dst=src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(src);
				}
				else
					memcpy(dst_pixel, &src, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.topRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &src, alpha);
			}
		}
	}
}

void drawAngle8ScaledBl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();

	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;

			int xInOriginalArea = x - area.left();

			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t src = pal[*src_pixel];

			dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomLeftCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (src & 0x80000000)
						*dst=src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(src);
				}
				else
					memcpy(dst_pixel, &src, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.bottomLeftCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &src, alpha);
			}
		}
	}
}

void drawAngle8ScaledBr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;

	const int src_width = pixmap.size().width();
	const int src_height = pixmap.size().height();
	const float scaleX = (float)src_width / (float)area.width();
	const float scaleY = (float)src_height / (float)area.height();

	for (int y = cornerRect.top(); y < cornerRect.bottom(); y++)
	{
		int yInOriginalArea = y - area.top();

		for (int x = cornerRect.left(); x < cornerRect.right(); x++)
		{
			int src_x = (x - area.left()) * scaleX;
			int src_y = (y - area.top()) * scaleY;

			int xInOriginalArea = x - area.left();
			
			uint8_t* dst_pixel = (uint8_t*)surface->data + x * dst_bypp + y * dst_stride;
			const uint8_t* src_pixel = (const uint8_t*)pixmap.surface->data + src_x * src_bypp + src_y * src_stride;
			uint32_t *dst = (uint32_t*)dst_pixel;
			uint32_t src = pal[*src_pixel];

			dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
			dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomRightCornerDRadius)
			{
				if (flag & gPixmap::blitAlphaTest)
				{
					if (src & 0x80000000)
						*dst=src;
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB*)dst;
					gDst->alpha_blend(src);
				}
				else
					memcpy(dst_pixel, &src, dst_bypp);
				continue;
			}
			else if (squared_dst < cornerData.bottomRightCornerSRadius)
			{
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, &src, alpha);
			}
		}
	}
}
