#include <lib/gdi/spinner.h>

#include <algorithm>
#include <cmath>
#include <cstring>

namespace
{
	constexpr float PI = 3.14159265358979323846f;
	constexpr float CIRCLE = 2 * PI;

	float coverage(float distance)
	{
		return std::max(0.0f, std::min(1.0f, distance + 0.5f));
	}
}

void gSpinner::resize(int diameter)
{
	m_diameter = std::max(8, diameter);
	m_halfWidth = m_diameter * (3.0f / 64);
	m_radius = m_diameter / 2.0f - m_halfWidth - 1.0f;
	m_pixels.clear();
	const float center = (m_diameter - 1) / 2.0f;
	for (int y = 0; y < m_diameter; ++y)
		for (int x = 0; x < m_diameter; ++x)
		{
			const float dx = x - center, dy = y - center;
			const float alpha = coverage(m_halfWidth - std::fabs(std::sqrt(dx * dx + dy * dy) - m_radius));
			if (alpha > 0)
			{
				float angle = std::atan2(dy, dx);
				if (angle < 0)
					angle += CIRCLE;
				m_pixels.push_back({x, y, dx, dy, angle, alpha});
			}
		}
}

void gSpinner::render(void *data, int stride, uint64_t elapsedMs, uint32_t color) const
{
	// Grow the leading end, then let the trailing end catch up. The cycle offset
	// keeps the movement continuous while the whole arc rotates at a steady rate.
	const float cycle = (elapsedMs % 2000) / 2000.0f;
	const float progress = cycle < 0.5f ? cycle * 2 : cycle * 2 - 1;
	const float eased = progress * progress * (3 - 2 * progress);
	const float tail = cycle < 0.5f ? 0 : 240 * eased;
	const float phase = std::fmod(cycle * 360 + ((elapsedMs / 2000) % 3) * 240 + tail, 360.0f) * (PI / 180);
	const float length = (cycle < 0.5f ? 30 + 240 * eased : 270 - 240 * eased) * (PI / 180);
	const float startX = std::cos(phase) * m_radius, startY = std::sin(phase) * m_radius;
	const float endX = std::cos(phase + length) * m_radius, endY = std::sin(phase + length) * m_radius;
	const float capLimit = (m_halfWidth + 0.5f) * (m_halfWidth + 0.5f);
	color &= 0xffffff;
	std::memset(data, 0, stride * m_diameter);
	for (const Pixel &pixel : m_pixels)
	{
		float angle = pixel.angle - phase;
		if (angle < 0)
			angle += CIRCLE;
		float active = pixel.coverage;
		if (angle > length)
		{
			const float sx = pixel.dx - startX, sy = pixel.dy - startY;
			const float ex = pixel.dx - endX, ey = pixel.dy - endY;
			const float distance = std::min(sx * sx + sy * sy, ex * ex + ey * ey);
			active = distance < capLimit ? coverage(m_halfWidth - std::sqrt(distance)) : 0;
		}
		const uint32_t alpha = std::min(active, pixel.coverage) * 255 + 0.5f;
		auto row = reinterpret_cast<uint32_t *>(static_cast<uint8_t *>(data) + pixel.y * stride);
		if (alpha)
			row[pixel.x] = (alpha << 24) | color;
	}
}
