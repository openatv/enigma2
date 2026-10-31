#pragma once

#include <lib/gdi/gpixmap.h>
#include <string>
#ifndef SWIG
#include <array>

// Wall-clock renderer counters, not GPU timer-query measurements.
struct gRenderTestFrame {
	std::array<unsigned long long, 23> values;
};
#endif

class gRenderTest {
public:
	static bool startCapture(int limit = 4096);
	static std::string stopCapture();
	static SWIG_VOID(int) createPixmap(ePtr<gPixmap>& SWIG_OUTPUT, int width, int height, int bpp, bool alpha = true, int accel = 0);
	static std::string pixmapInfo(ePtr<gPixmap>& pixmap);
	static SWIG_VOID(int) createPaintedPixmap(ePtr<gPixmap>& SWIG_OUTPUT, int pattern, int accel);
	static int verifyColorBars(ePtr<gPixmap>& pixmap);
#ifndef SWIG
	static void recordFrame(const gRenderTestFrame& frame);
#endif
};
