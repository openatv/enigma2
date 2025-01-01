/*
Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License

Copyright (c) 2023-2025 zKhadiri, jbleyel, OpenATV

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

uint32_t *createGradientBuffer3(int graSize, const std::vector<gRGB> &colors)
{
	uint32_t *gradientBuf = (uint32_t *)malloc(graSize * sizeof(uint32_t));

	uint32_t start_col = colors.at(0).argb();
	uint32_t mid_col = colors.at(1).argb();
	uint32_t end_col = colors.at(2).argb();

	start_col ^= 0xFF000000;
	mid_col ^= 0xFF000000;
	end_col ^= 0xFF000000;

	uint8_t start_a = (uint8_t)((start_col & 0xFF000000) >> 24);
	uint8_t start_r = (uint8_t)((start_col & 0x00FF0000) >> 16);
	uint8_t start_g = (uint8_t)((start_col & 0x0000FF00) >> 8);
	uint8_t start_b = (uint8_t)(start_col & 0x000000FF);

	uint8_t mid_a = (uint8_t)((mid_col & 0xFF000000) >> 24);
	uint8_t mid_r = (uint8_t)((mid_col & 0x00FF0000) >> 16);
	uint8_t mid_g = (uint8_t)((mid_col & 0x0000FF00) >> 8);
	uint8_t mid_b = (uint8_t)(mid_col & 0x000000FF);

	uint8_t end_a = (uint8_t)((end_col & 0xFF000000) >> 24);
	uint8_t end_r = (uint8_t)((end_col & 0x00FF0000) >> 16);
	uint8_t end_g = (uint8_t)((end_col & 0x0000FF00) >> 8);
	uint8_t end_b = (uint8_t)(end_col & 0x000000FF);

	float steps = (float)graSize;
	float aStep1 = (float)(mid_a - start_a) / (steps / 2);
	float rStep1 = (float)(mid_r - start_r) / (steps / 2);
	float gStep1 = (float)(mid_g - start_g) / (steps / 2);
	float bStep1 = (float)(mid_b - start_b) / (steps / 2);

	float aStep2 = (float)(end_a - mid_a) / (steps / 2);
	float rStep2 = (float)(end_r - mid_r) / (steps / 2);
	float gStep2 = (float)(end_g - mid_g) / (steps / 2);
	float bStep2 = (float)(end_b - mid_b) / (steps / 2);

	if (gradientBuf != NULL)
	{
		for (int x = 0; x < graSize; x++)
		{
			uint8_t a, r, g, b;
			if (x < graSize / 2)
			{
				a = (uint8_t)(start_a + aStep1 * x);
				r = (uint8_t)(start_r + rStep1 * x);
				g = (uint8_t)(start_g + gStep1 * x);
				b = (uint8_t)(start_b + bStep1 * x);
			}
			else
			{
				a = (uint8_t)(mid_a + aStep2 * (x - graSize / 2));
				r = (uint8_t)(mid_r + rStep2 * (x - graSize / 2));
				g = (uint8_t)(mid_g + gStep2 * (x - graSize / 2));
				b = (uint8_t)(mid_b + bStep2 * (x - graSize / 2));
			}
			gradientBuf[x] = (((uint32_t)a << 24) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b);
		}
	}
	return gradientBuf;
}

uint32_t *createGradientBuffer2(int graSize, const gRGB &startColor, const gRGB &endColor)
{
	uint32_t *gradientBuf = (uint32_t *)malloc(graSize * sizeof(uint32_t));

	uint32_t start_col = startColor.argb();
	start_col ^= 0xFF000000;

	uint32_t end_col = endColor.argb();
	end_col ^= 0xFF000000;

	uint8_t start_a = (uint8_t)((start_col & 0xFF000000) >> 24);
	uint8_t start_r = (uint8_t)((start_col & 0x00FF0000) >> 16);
	uint8_t start_g = (uint8_t)((start_col & 0x0000FF00) >> 8);
	uint8_t start_b = (uint8_t)(start_col & 0x000000FF);

	uint8_t end_a = (uint8_t)((end_col & 0xFF000000) >> 24);
	uint8_t end_r = (uint8_t)((end_col & 0x00FF0000) >> 16);
	uint8_t end_g = (uint8_t)((end_col & 0x0000FF00) >> 8);
	uint8_t end_b = (uint8_t)(end_col & 0x000000FF);

	float steps = (float)graSize;
	float aStep = (float)(end_a - start_a) / steps;
	float rStep = (float)(end_r - start_r) / steps;
	float gStep = (float)(end_g - start_g) / steps;
	float bStep = (float)(end_b - start_b) / steps;

	if (gradientBuf != nullptr)
	{
		for (int x = 0; x < graSize; x++)
		{
			uint8_t a = (uint8_t)(start_a + aStep * x);
			uint8_t r = (uint8_t)(start_r + rStep * x);
			uint8_t g = (uint8_t)(start_g + gStep * x);
			uint8_t b = (uint8_t)(start_b + bStep * x);
			gradientBuf[x] = ((uint32_t)a << 24) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)b;
		}
	}
	return gradientBuf;
}

static void blendPixelRounded(uint32_t *dst, const uint32_t *src, const double alpha)
{
	if (!((*src) & 0xFF000000))
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

void drawAngleTl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	for (int y = rTop; y < rBottom; y++)
	{
		int yInOriginalArea = y - aTop;
		uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + rLeft * surface->bypp);

		for (int x = rLeft; x < rRight; x++)
		{
			int xInOriginalArea = x - aLeft;
			dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topLeftCornerDRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.topLeftCornerSRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, s, alpha);
			}
			++dst;
		}
	}
}

void drawAngleTr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	for (int y = rTop; y < rBottom; y++)
	{
		int yInOriginalArea = y - aTop;
		uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + rLeft * surface->bypp);

		for (int x = rLeft; x < rRight; x++)
		{
			int xInOriginalArea = x - aLeft;
			dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
			dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.topRightCornerDRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.topRightCornerSRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, s, alpha);
			}
			++dst;
		}
	}
}

void drawAngleBl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	for (int y = rTop; y < rBottom; y++)
	{
		int yInOriginalArea = y - aTop;
		uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + rLeft * surface->bypp);

		for (int x = rLeft; x < rRight; x++)
		{
			int xInOriginalArea = x - aLeft;
			dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
			dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomLeftCornerDRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.bottomLeftCornerSRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
				alpha = radiusData.at(squared_dst);
				blendPixelRounded(dst, s, alpha);
			}
			++dst;
		}
	}
}

void drawAngleBr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	for (int y = rTop; y < rBottom; y++)
	{
		int yInOriginalArea = y - aTop;
		uint32_t *dst = (uint32_t *)(((uint8_t *)surface->data) + y * surface->stride + rLeft * surface->bypp);

		for (int x = rLeft; x < rRight; x++)
		{
			int xInOriginalArea = x - aLeft;
			dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
			dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
			squared_dst = dx * dx + dy * dy;
			if (squared_dst <= cornerData.bottomRightCornerDRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
				*dst = *s;
				++dst;
				continue;
			}
			else if (squared_dst < cornerData.bottomRightCornerSRadius)
			{
				const uint32_t *s = src + (direction == 1 ? yInOriginalArea : xInOriginalArea);
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
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint32_t *srcptr = (uint32_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (rLeft - aLeft) + (rTop - aTop) * pixmap.surface->stride / 4;
	dstptr += rLeft + rTop * surface->stride / 4;
	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					if (!((*src) & 0xFF000000))
					{
						src++;
						dst++;
					}
					else
						*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					gRGB *gSrc = (gRGB *)src;
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((gSrc->b - gDst->b) * gSrc->a) >> 8);
					gDst->g += (((gSrc->g - gDst->g) * gSrc->a) >> 8);
					gDst->r += (((gSrc->r - gDst->r) * gSrc->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * gSrc->a) >> 8);
					src++;
					dst++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
}

void drawAngle32Tr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint32_t *srcptr = (uint32_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (rLeft - aLeft) + (rTop - aTop) * pixmap.surface->stride / 4;
	dstptr += rLeft + rTop * surface->stride / 4;
	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					if (!((*src) & 0xFF000000))
					{
						src++;
						dst++;
					}
					else
						*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					gRGB *gSrc = (gRGB *)src;
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((gSrc->b - gDst->b) * gSrc->a) >> 8);
					gDst->g += (((gSrc->g - gDst->g) * gSrc->a) >> 8);
					gDst->r += (((gSrc->r - gDst->r) * gSrc->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * gSrc->a) >> 8);
					src++;
					dst++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
}

void drawAngle32Bl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint32_t *srcptr = (uint32_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (rLeft - aLeft) + (rTop - aTop) * pixmap.surface->stride / 4;
	dstptr += rLeft + rTop * surface->stride / 4;
	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					if (!((*src) & 0xFF000000))
					{
						src++;
						dst++;
					}
					else
						*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					gRGB *gSrc = (gRGB *)src;
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((gSrc->b - gDst->b) * gSrc->a) >> 8);
					gDst->g += (((gSrc->g - gDst->g) * gSrc->a) >> 8);
					gDst->r += (((gSrc->r - gDst->r) * gSrc->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * gSrc->a) >> 8);
					src++;
					dst++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
}

void drawAngle32Br(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint32_t *srcptr = (uint32_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (rLeft - aLeft) + (rTop - aTop) * pixmap.surface->stride / 4;
	dstptr += rLeft + rTop * surface->stride / 4;
	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					if (!((*src) & 0xFF000000))
					{
						src++;
						dst++;
					}
					else
						*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					gRGB *gSrc = (gRGB *)src;
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((gSrc->b - gDst->b) * gSrc->a) >> 8);
					gDst->g += (((gSrc->g - gDst->g) * gSrc->a) >> 8);
					gDst->r += (((gSrc->r - gDst->r) * gSrc->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * gSrc->a) >> 8);
					src++;
					dst++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
	else
	{
		for (int y = rTop; y < rBottom; y++)
		{
			int yInOriginalArea = y - aTop;
			uint32_t *src = srcptr;
			uint32_t *dst = dstptr;

			for (int x = rLeft; x < rRight; x++)
			{
				int xInOriginalArea = x - aLeft;
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					*dst++ = *src++;
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
			srcptr = (uint32_t *)((uint8_t *)srcptr + pixmap.surface->stride);
			dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
		}
	}
}

void drawAngle32ScaledTl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					if (*src & 0x80000000)
						*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					const gRGB *src = (gRGB *)(src_row + src_x * src_bypp);
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((src->b - gDst->b) * src->a) >> 8);
					gDst->g += (((src->g - gDst->g) * src->a) >> 8);
					gDst->r += (((src->r - gDst->r) * src->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * src->a) >> 8);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}

void drawAngle32ScaledTr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					if (*src & 0x80000000)
						*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					const gRGB *src = (gRGB *)(src_row + src_x * src_bypp);
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((src->b - gDst->b) * src->a) >> 8);
					gDst->g += (((src->g - gDst->g) * src->a) >> 8);
					gDst->r += (((src->r - gDst->r) * src->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * src->a) >> 8);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}

void drawAngle32ScaledBl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					if (*src & 0x80000000)
						*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					const gRGB *src = (gRGB *)(src_row + src_x * src_bypp);
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((src->b - gDst->b) * src->a) >> 8);
					gDst->g += (((src->g - gDst->g) * src->a) >> 8);
					gDst->r += (((src->r - gDst->r) * src->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * src->a) >> 8);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}

void drawAngle32ScaledBr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					if (*src & 0x80000000)
						*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					const gRGB *src = (gRGB *)(src_row + src_x * src_bypp);
					gRGB *gDst = (gRGB *)dst;
					gDst->b += (((src->b - gDst->b) * src->a) >> 8);
					gDst->g += (((src->g - gDst->g) * src->a) >> 8);
					gDst->r += (((src->r - gDst->r) * src->a) >> 8);
					gDst->a += (((0xFF - gDst->a) * src->a) >> 8);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint32_t *src = (const uint32_t *)(src_row + src_x * src_bypp);
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					*dst = *src;
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, src, alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}

void drawAngle8Tl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (cornerRect.left() - area.left()) + (cornerRect.top() - area.top()) * pixmap.surface->stride;
	dstptr += cornerRect.left() + cornerRect.top() * surface->stride / 4;
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
					}
					else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB *)dst;
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
		dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
	}
}

void drawAngle8Tr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (cornerRect.left() - area.left()) + (cornerRect.top() - area.top()) * pixmap.surface->stride;
	dstptr += cornerRect.left() + cornerRect.top() * surface->stride / 4;
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
					}
					else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB *)dst;
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
		dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
	}
}

void drawAngle8Bl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (cornerRect.left() - area.left()) + (cornerRect.top() - area.top()) * pixmap.surface->stride;
	dstptr += cornerRect.left() + cornerRect.top() * surface->stride / 4;
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
					}
					else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB *)dst;
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
		dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
	}
}

void drawAngle8Br(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const uint8_t *srcptr = (uint8_t *)pixmap.surface->data;
	uint32_t *dstptr = (uint32_t *)surface->data;

	srcptr += (cornerRect.left() - area.left()) + (cornerRect.top() - area.top()) * pixmap.surface->stride;
	dstptr += cornerRect.left() + cornerRect.top() * surface->stride / 4;
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
					}
					else
						*dst++ = pal[*src++];
				}
				else if (flag & gPixmap::blitAlphaBlend)
				{
					gRGB *gDst = (gRGB *)dst;
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
		dstptr = (uint32_t *)((uint8_t *)dstptr + surface->stride);
	}
}

void drawAngle8ScaledTl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					if (pal[*src] & 0x80000000)
						*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					gRGB *gDst = (gRGB *)dst;
					gDst->alpha_blend(pal[*src]);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = cornerData.topLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = cornerData.topLeftCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topLeftCornerDRadius)
				{
					*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}

void drawAngle8ScaledTr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					if (pal[*src] & 0x80000000)
						*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					gRGB *gDst = (gRGB *)dst;
					gDst->alpha_blend(pal[*src]);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = xInOriginalArea - cornerData.w_topRightCornerRadius;
				dy = cornerData.topRightCornerRadius - yInOriginalArea - 1 + cornerData.borderWidth;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.topRightCornerDRadius)
				{
					*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.topRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}

void drawAngle8ScaledBl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					if (pal[*src] & 0x80000000)
						*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					gRGB *gDst = (gRGB *)dst;
					gDst->alpha_blend(pal[*src]);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = cornerData.bottomLeftCornerRadius - xInOriginalArea - 1 + cornerData.borderWidth;
				dy = yInOriginalArea - cornerData.h_bottomLeftCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomLeftCornerDRadius)
				{
					*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomLeftCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}

void drawAngle8ScaledBr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag)
{
	double alpha = 1.0;
	int dx = 0, dy = 0, squared_dst = 0;
	const std::unordered_map<int, double> &radiusData = cornerData.RadiusData;
	const int src_bypp = pixmap.surface->bypp;
	const int dst_bypp = surface->bypp;
	const int src_stride = pixmap.surface->stride;
	const int dst_stride = surface->stride;
	const float scaleX = (float)pixmap.size().width() / (float)area.width();
	const float scaleY = (float)pixmap.size().height() / (float)area.height();
	const int aLeft = area.left();
	const int aTop = area.top();
	const int rLeft = cornerRect.left();
	const int rRight = cornerRect.right();
	const int rTop = cornerRect.top();
	const int rBottom = cornerRect.bottom();
	uint8_t *dst_row = (uint8_t *)surface->data + rLeft * dst_bypp + rTop * dst_stride;

	if (flag & gPixmap::blitAlphaTest)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					if (pal[*src] & 0x80000000)
						*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
	else if (flag & gPixmap::blitAlphaBlend)
	{
		for (int y = rTop; y < rBottom; ++y)
		{
			int src_y = (int)((y - aTop) * scaleY);
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					gRGB *gDst = (gRGB *)dst;
					gDst->alpha_blend(pal[*src]);
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
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
			const uint8_t *src_row = (const uint8_t *)pixmap.surface->data + src_y * src_stride;
			uint32_t *dst = (uint32_t *)dst_row;
			int yInOriginalArea = y - aTop;

			for (int x = rLeft; x < rRight; ++x)
			{
				int xInOriginalArea = x - aLeft;
				int src_x = (int)((x - aLeft) * scaleX);
				const uint8_t *src = src_row + src_x * src_bypp;
				dx = xInOriginalArea - cornerData.w_bottomRightCornerRadius;
				dy = yInOriginalArea - cornerData.h_bottomRightCornerRadius;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= cornerData.bottomRightCornerDRadius)
				{
					*dst = pal[*src];
					dst++;
					continue;
				}
				else if (squared_dst < cornerData.bottomRightCornerSRadius)
				{
					alpha = radiusData.at(squared_dst);
					blendPixelRounded(dst, &pal[*src], alpha);
				}
				dst++;
			}
			dst_row += dst_stride;
		}
	}
}
