#ifndef __gdi_spinner_h
#define __gdi_spinner_h

#include <cstdint>
#include <vector>

// Small, software-rendered busy indicator. Geometry is cached at OSD resolution.
class gSpinner
{
	struct Pixel
	{
		int x, y;
		float dx, dy, angle, coverage;
	};
	std::vector<Pixel> m_pixels;
	int m_diameter = 0;
	float m_radius = 0, m_halfWidth = 0;

public:
	void resize(int diameter);
	void render(void *data, int stride, uint64_t elapsedMs, uint32_t color) const;
};

#endif
