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
	while (n*2 <= size) {
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
	int dx = 0.0, dy = 0.0, squared_dst = 0.0;
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
	int dx = 0.0, dy = 0.0, squared_dst = 0.0;
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
	int dx = 0.0, dy = 0.0, squared_dst = 0.0;
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
	int dx = 0.0, dy = 0.0, squared_dst = 0.0;
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
