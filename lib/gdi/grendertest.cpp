#include <lib/gdi/grendertest.h>
#include <lib/gdi/accel.h>
#include <lib/gdi/region.h>
#include <algorithm>
#include <atomic>
#include <cstring>
#include <mutex>
#include <sstream>
#include <time.h>
#include <vector>

namespace {
std::mutex captureMutex;
std::atomic<bool> captureActive{false};
std::vector<gRenderTestFrame> captureFrames;
unsigned int captureLimit = 0;
unsigned int captureDropped = 0;
unsigned long long captureStart = 0;

unsigned long long monotonicUs()
{
	timespec value;
	clock_gettime(CLOCK_MONOTONIC, &value);
	return static_cast<unsigned long long>(value.tv_sec) * 1000000ULL + value.tv_nsec / 1000;
}
}

bool gRenderTest::startCapture(int limit)
{
	std::lock_guard<std::mutex> lock(captureMutex);
	if (captureActive.load())
		return false;
	captureLimit = std::max(1, std::min(4096, limit));
	captureFrames.clear();
	captureFrames.reserve(captureLimit);
	captureDropped = 0;
	captureStart = monotonicUs();
	captureActive.store(true);
	return true;
}

void gRenderTest::recordFrame(const gRenderTestFrame& frame)
{
	if (!captureActive.load())
		return;
	std::lock_guard<std::mutex> lock(captureMutex);
	// Exclude a frame that began before capture; values[1] includes idle time.
	if (!captureActive.load() || frame.values[0] < frame.values[1] || frame.values[0] - frame.values[1] < captureStart)
		return;
	if (captureFrames.size() < captureLimit)
		captureFrames.push_back(frame);
	else
		++captureDropped;
}

std::string gRenderTest::stopCapture()
{
	std::vector<gRenderTestFrame> frames;
	unsigned int dropped;
	unsigned long long start, end;
	{
		std::lock_guard<std::mutex> lock(captureMutex);
		captureActive.store(false);
		frames.swap(captureFrames);
		dropped = captureDropped;
		start = captureStart;
		end = monotonicUs();
	}
	std::ostringstream result;
	result << "{\"schema\":2,\"gpuTimerQuery\":false,\"scanoutConfirmed\":false,\"startUs\":" << start
		<< ",\"endUs\":" << end << ",\"dropped\":" << dropped
		<< ",\"columns\":[\"endUs\",\"intervalUs\",\"drawUs\",\"swapUs\",\"fillUs\",\"rectUs\",\"blitUs\",\"textUs\",\"copyUs\",\"uploadBytes\",\"uploads\",\"ionUploads\",\"ionAvoidedBytes\",\"clutUploads\",\"convertedUploads\",\"fillOps\",\"gradientOps\",\"roundedOps\",\"blitOps\",\"glyphs\",\"frameCopies\",\"copyPixels\",\"rgb565Uploads\"],\"frames\":[";
	bool first = true;
	for (const auto& frame : frames) {
		if (!first) result << ',';
		first = false;
		result << '[';
		for (size_t i = 0; i < frame.values.size(); ++i) {
			if (i) result << ',';
			result << frame.values[i];
		}
		result << ']';
	}
	result << "]}";
	return result.str();
}

int gRenderTest::createPixmap(ePtr<gPixmap>& output, int width, int height, int bpp, bool alpha, int accel)
{
	output = 0;
	if (width < 1 || height < 1 || width > 1024 || height > 1024 || (bpp != 8 && bpp != 16 && bpp != 32) || accel < -1 || accel > 1)
		return -1;
	output = new gPixmap(eSize(width, height), bpp, accel);
	gUnmanagedSurface* surface = output->surface;
	if (!surface || !surface->data) {
		output = 0;
		return -1;
	}
	const gRGB colors[] = {gRGB(255, 0, 0), gRGB(0, 255, 0), gRGB(0, 0, 255), gRGB(255, 255, 255)};
	if (bpp == 8) {
		delete[] surface->clut.data;
		surface->clut.start = 0;
		surface->clut.colors = 256;
		surface->clut.data = new gRGB[256];
		for (int i = 0; i < 256; ++i) {
			surface->clut.data[i] = colors[i / 64];
			surface->clut.data[i].a = alpha ? 255 - (i % 64) * 255 / 63 : 0;
		}
	}
	memset(surface->data, 0, surface->stride * height);
	for (int y = 0; y < height; ++y) {
		unsigned char* row = static_cast<unsigned char*>(surface->data) + y * surface->stride;
		int step = height > 1 ? y * 63 / (height - 1) : 63;
		for (int x = 0; x < width; ++x) {
			int band = std::min(3, x * 4 / width);
			const gRGB& color = colors[band];
			if (bpp == 8)
				row[x] = band * 64 + step;
			else if (bpp == 32)
				reinterpret_cast<uint32_t*>(row)[x] = color.value | (static_cast<uint32_t>(alpha ? step * 255 / 63 : 255) << 24);
			else {
				const uint16_t bgr565 = ((color.b >> 3) << 11) | ((color.g >> 2) << 5) | (color.r >> 3);
				row[x * 2] = bgr565 >> 8;
				row[x * 2 + 1] = bgr565 & 0xff;
			}
		}
	}
	surface->transparent = alpha && bpp != 16;
	return 0;
}

std::string gRenderTest::pixmapInfo(ePtr<gPixmap>& pixmap)
{
	if (!pixmap || !pixmap->surface)
		return "{}";
	const gUnmanagedSurface* surface = pixmap->surface;
	pixmap->ensureCPUContent();
	std::ostringstream result;
	result << "{\"width\":" << surface->x << ",\"height\":" << surface->y << ",\"bpp\":" << surface->bpp
		<< ",\"stride\":" << surface->stride << ",\"cpuBytes\":" << surface->stride * surface->y
		<< ",\"paletteEntries\":" << surface->clut.colors << ",\"physicalBacking\":" << (surface->data_phys ? "true" : "false")
		<< ",\"sharedNative\":" << (surface->gl_native_shared ? "true" : "false");
	if (surface->bpp == 32 && surface->data && surface->x > 0 && surface->y > 0) {
		const volatile uint32_t* first = static_cast<const volatile uint32_t*>(surface->data);
		const volatile uint32_t* last = reinterpret_cast<const volatile uint32_t*>(static_cast<const uint8_t*>(surface->data) + (surface->y - 1) * surface->stride);
		result << ",\"cornerAlpha\":[" << (first[0] >> 24) << ',' << (first[surface->x - 1] >> 24) << ',' << (last[0] >> 24) << ',' << (last[surface->x - 1] >> 24) << ']';
	}
	result << '}';
	return result.str();
}

int gRenderTest::createPaintedPixmap(ePtr<gPixmap>& output, int pattern, int accel)
{
	output = 0;
	if (pattern < 0 || pattern > 2 || (accel != -1 && accel != 1))
		return -1;
	output = new gPixmap(eSize(320, 160), 32, accel);
	if (!output->surface || !output->surface->data) {
		output = 0;
		return -1;
	}
	const eRect bounds(0, 0, 320, 160);
	const gRegion clip(bounds);
	if (pattern == 0) {
		const gRGB colors[] = {gRGB(255, 0, 0), gRGB(0, 255, 0), gRGB(0, 0, 255), gRGB(255, 255, 255)};
		for (int i = 0; i < 4; ++i)
			output->fill(gRegion(eRect(i * 80, 0, 80, 160)), colors[i]);
	} else {
		output->fill(clip, gRGB(0xff000000));
		if (pattern == 1) {
			const std::vector<gRGB> gradient = {gRGB(0x00f03048), gRGB(0x80e9c75a), gRGB(0xff1a9aee)};
			output->drawRectangle(clip, bounds, gRGB(), gRGB(0x00ffffff), 3, gradient, 2, 26, 15, true, 0, true);
		} else {
			ePtr<gPixmap> source;
			if (createPixmap(source, 320, 160, 32, true, -1))
				return -1;
			output->blit(*source, bounds, clip, 26, 15, gPixmap::blitAlphaBlend);
		}
	}
	return 0;
}

int gRenderTest::verifyColorBars(ePtr<gPixmap>& pixmap)
{
	if (!pixmap || !pixmap->surface || pixmap->surface->bpp != 32 || pixmap->surface->x != 320 || pixmap->surface->y != 160)
		return -1;
	if (gAccel::getInstance())
		gAccel::getInstance()->sync();
	const uint32_t colors[] = {0xffff0000, 0xff00ff00, 0xff0000ff, 0xffffffff};
	const gUnmanagedSurface* surface = pixmap->surface;
	int mismatches = 0;
	for (int y = 0; y < surface->y; ++y) {
		const volatile uint32_t* row = reinterpret_cast<const volatile uint32_t*>(static_cast<const uint8_t*>(surface->data) + y * surface->stride);
		for (int x = 0; x < surface->x; ++x)
			mismatches += row[x] != colors[x / 80];
	}
	return mismatches;
}
