#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/modelinformation.h>
#include <lib/gdi/egl/gegldc.h>
#include <lib/gdi/egl/gles_version.h>
#include <lib/gdi/fb.h>
#include <algorithm>
#include <fstream>
#include <iterator>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>
#include <vector>
#ifdef DREAMNEXTGEN
#include <lib/gdi/dreamge2d.h>
#include <lib/gdi/egl/platform/amlogic/amlogic_window_provider.h>
#endif
#ifdef HAVE_VUPLUS_EGL
#include <lib/gdi/egl/platform/vuplus/vuplus_window_provider.h>
#endif
#ifdef HAVE_VUPLUS_MIPSEL_EGL
#include <lib/gdi/egl/platform/vuplus_mips/vuplus_mips_window_provider.h>
#endif
#ifdef HAVE_NXPL_EGL
#include <lib/gdi/egl/platform/nxpl/nxpl_window_provider.h>
#endif
#ifdef HAVE_V3DPLATFORM_EGL
#include <lib/gdi/egl/platform/v3dplatform/v3dplatform_window_provider.h>
#endif
#ifdef HAVE_HISILICON_EGL
#include <lib/gdi/egl/platform/hisilicon/hisilicon_window_provider.h>
#endif
#ifdef HAVE_DREAMBCM_EGL
#include <lib/gdi/egl/platform/dreambcm/dreambcm_window_provider.h>
#endif

#ifndef EGL_OPENGL_ES3_BIT_KHR
#define EGL_OPENGL_ES3_BIT_KHR 0x00000040
#endif
#ifndef EGL_SWAP_BEHAVIOR
#define EGL_SWAP_BEHAVIOR 0x3093
#endif
#ifndef EGL_BUFFER_PRESERVED
#define EGL_BUFFER_PRESERVED 0x3094
#endif
#ifndef EGL_BUFFER_DESTROYED
#define EGL_BUFFER_DESTROYED 0x3095
#endif
#ifndef EGL_SWAP_BEHAVIOR_PRESERVED_BIT
#define EGL_SWAP_BEHAVIOR_PRESERVED_BIT 0x0400
#endif

static bool hasExtension(const char* extensions, const char* name) {
	if (!extensions || !name || !*name)
		return false;

	const char* start = extensions;
	const size_t name_len = strlen(name);
	while ((start = strstr(start, name))) {
		const char before = start == extensions ? ' ' : *(start - 1);
		const char after = *(start + name_len);
		if ((before == ' ' || before == '\0') && (after == ' ' || after == '\0'))
			return true;
		start += name_len;
	}
	return false;
}

static bool e2eglKeepContextBetweenOpcodes() {
	static int keep = -1;
	if (keep < 0) {
		const char* env = getenv("E2EGL_KEEP_CONTEXT");
		if (env && *env)
			keep = atoi(env) != 0;
		else {
#if defined(HAVE_VUPLUS_EGL) || defined(HAVE_VUPLUS_MIPSEL_EGL) || defined(HAVE_NXPL_EGL)
			keep = 1;
#else
			keep = 0;
#endif
		}
	}
	return keep != 0;
}

static bool e2eglForceDestroyedSwap() {
#if defined(HAVE_V3DPLATFORM_EGL) || defined(HAVE_NXPL_EGL) || defined(HAVE_VUPLUS_EGL) || defined(HAVE_VUPLUS_MIPSEL_EGL)
	return true;
#else
	return false;
#endif
}

static std::string e2eglReadTextFile(const char* filename) {
	std::ifstream file(filename);
	std::string value;
	if (file.good())
		std::getline(file, value);
	return value;
}

#if defined(HAVE_NXPL_EGL) && defined(E2EGL_NXPL_SYNC_FB_DST)
static bool e2eglWriteHexProc(const char* filename, int value)
{
	int fd = open(filename, O_WRONLY | O_TRUNC);
	if (fd < 0)
		return false;

	char buf[32];
	const int len = snprintf(buf, sizeof(buf), "%08x\n", value);
	const bool ok = len > 0 && write(fd, buf, len) == len;
	close(fd);
	return ok;
}

static bool e2eglWriteIntProc(const char* filename, int value)
{
	int fd = open(filename, O_WRONLY | O_TRUNC);
	if (fd < 0)
		return false;

	char buf[32];
	const int len = snprintf(buf, sizeof(buf), "%d\n", value);
	const bool ok = len > 0 && write(fd, buf, len) == len;
	close(fd);
	return ok;
}

static void e2eglSyncNxplFramebufferDestination(int left, int top, int width, int height)
{
	if (width < 1 || height < 1)
		return;

	static const char* dst_left = "/proc/stb/fb/dst_left";
	static const char* dst_top = "/proc/stb/fb/dst_top";
	static const char* dst_width = "/proc/stb/fb/dst_width";
	static const char* dst_height = "/proc/stb/fb/dst_height";
	static const char* dst_apply = "/proc/stb/fb/dst_apply";
	if (access(dst_left, W_OK) || access(dst_top, W_OK) || access(dst_width, W_OK) || access(dst_height, W_OK))
		return;

	const bool ok = e2eglWriteHexProc(dst_left, left) &&
	                e2eglWriteHexProc(dst_top, top) &&
	                e2eglWriteHexProc(dst_width, width) &&
	                e2eglWriteHexProc(dst_height, height);
	if (ok && !access(dst_apply, W_OK))
		e2eglWriteIntProc(dst_apply, 1);

	eDebug("[gEGLDC] NXPL framebuffer OSD destination %s logical=%d,%d %dx%d",
		ok ? "synced" : "sync failed", left, top, width, height);
}
#endif

#ifdef HAVE_HISILICON_EGL
static std::string e2eglReadWholeFile(const char* filename) {
	std::ifstream file(filename);
	if (!file.good())
		return std::string();
	return std::string((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
}

static bool e2eglExtractXmlIntAttribute(const std::string& tag, const char* name, int& value) {
	const std::string key(name);
	size_t pos = tag.find(key);
	if (pos != std::string::npos) {
		const size_t after_key = pos + key.size();
		size_t eq = tag.find('=', after_key);
		if (eq == std::string::npos)
			return false;
		size_t quote = tag.find_first_of("\"'", eq + 1);
		if (quote == std::string::npos)
			return false;
		const char quote_char = tag[quote];
		const size_t end = tag.find(quote_char, quote + 1);
		if (end == std::string::npos)
			return false;
		value = atoi(tag.substr(quote + 1, end - quote - 1).c_str());
		return value > 0;
	}
	return false;
}

static bool e2eglReadSkinResolution(const char* skin_file, int& width, int& height, int& bpp) {
	const std::string skin = e2eglReadWholeFile(skin_file);
	if (skin.empty())
		return false;

	const size_t resolution_start = skin.find("<resolution");
	if (resolution_start == std::string::npos)
		return false;
	const size_t resolution_end = skin.find('>', resolution_start);
	if (resolution_end == std::string::npos)
		return false;

	const std::string tag = skin.substr(resolution_start, resolution_end - resolution_start + 1);
	int xres = 0, yres = 0, depth = 32;
	if (!e2eglExtractXmlIntAttribute(tag, "xres", xres) || !e2eglExtractXmlIntAttribute(tag, "yres", yres))
		return false;
	e2eglExtractXmlIntAttribute(tag, "bpp", depth);

	if (!((xres == 720 && yres == 576) || (xres == 1280 && yres == 720) || (xres == 1920 && yres == 1080) || (xres == 2560 && yres == 1440)))
		return false;

	width = xres;
	height = yres;
	bpp = depth > 0 ? depth : 32;
	return true;
}

static bool e2eglReadSkinResolutionFromValue(std::string skin, int& width, int& height, int& bpp) {
	skin.erase(std::remove(skin.begin(), skin.end(), '\r'), skin.end());
	skin.erase(std::remove(skin.begin(), skin.end(), '\n'), skin.end());
	if (skin.empty())
		return false;

	if (skin[0] == '/')
		return e2eglReadSkinResolution(skin.c_str(), width, height, bpp);

	const std::string skin_path = std::string("/usr/share/enigma2/") + skin;
	return e2eglReadSkinResolution(skin_path.c_str(), width, height, bpp);
}

static bool e2eglReadConfiguredSkinResolution(int& width, int& height, int& bpp) {
	std::ifstream settings("/etc/enigma2/settings");
	std::string line;
	while (settings.good() && std::getline(settings, line)) {
		const char* prefix = "config.skin.primary_skin=";
		if (line.find(prefix) != 0)
			continue;

		if (e2eglReadSkinResolutionFromValue(line.substr(strlen(prefix)), width, height, bpp))
			return true;
		break;
	}

	if (e2eglReadSkinResolutionFromValue("MetrixHD/skin.xml", width, height, bpp))
		return true;

	return e2eglReadSkinResolutionFromValue("skin_default/skin.xml", width, height, bpp);
}
#endif

static bool e2eglNeedsLegacyNxplSurface(const std::string& value) {
	return value == "hd2400" || value == "mutant2400" || value == "quadbox2400" ||
	       value == "triplex" ||
	       value == "et10000" ||
	       value == "formuler1" || value == "formuler1tc" || value == "f1";
}

static bool e2eglNxplUseVideoModeSurface() {
#if defined(HAVE_VUPLUS_EGL)
	return true;
#elif defined(HAVE_NXPL_EGL)
	static int use = -1;
	if (use < 0) {
		const std::string machine = eModelInformation::getInstance().getValue("machinebuild");
		const std::string boxtype = e2eglReadTextFile("/proc/stb/info/boxtype");
		use = e2eglNeedsLegacyNxplSurface(machine) || e2eglNeedsLegacyNxplSurface(boxtype);
	}
	return use != 0;
#else
	return false;
#endif
}

static bool e2eglRequiresNativeWindow()
{
#ifdef HAVE_DREAMBCM_EGL
	return false;
#else
	return true;
#endif
}

static bool e2eglVideoModeToSize(std::string mode, int& width, int& height) {
	mode.erase(std::remove(mode.begin(), mode.end(), '\n'), mode.end());
	mode.erase(std::remove(mode.begin(), mode.end(), '\r'), mode.end());
	if (mode.find("smpte") == 0) {
		width = 4096;
		height = 2160;
		return true;
	}
	if (mode.find("2160") != std::string::npos) {
		width = 3840;
		height = 2160;
		return true;
	}
	if (mode.find("1080") != std::string::npos) {
		width = 1920;
		height = 1080;
		return true;
	}
	if (mode.find("720") != std::string::npos) {
		width = 1280;
		height = 720;
		return true;
	}
	if (mode.find("576") != std::string::npos || mode == "pal" || mode == "pal60") {
		width = 720;
		height = 576;
		return true;
	}
	if (mode.find("480") != std::string::npos || mode == "ntsc") {
		width = 720;
		height = 480;
		return true;
	}
	return false;
}

static void e2eglLimitVuplusNativeSurfaceSize(int& width, int& height) {
#ifdef HAVE_VUPLUS_EGL
	// Vu+ 4K renders WQHD skins logically, while its NXPL OSD window stays at 1080p.
	if (width > 1920 || height > 1080) {
		width = 1920;
		height = 1080;
	}
#else
	(void)width;
	(void)height;
#endif
}

static const char E2EGL_CAPTURE_SOCKET[] = "/tmp/e2egl-osd.socket";
static const char E2EGL_CAPTURE_MAGIC[8] = {'E', '2', 'E', 'G', 'L', '0', '1', 0};
static const uint32_t E2EGL_CAPTURE_FORMAT_BGRA = 1;

struct E2EGLCaptureHeader {
	char magic[8];
	uint32_t width;
	uint32_t height;
	uint32_t stride;
	uint32_t format;
};

static bool e2eglWriteAll(int fd, const void* data, size_t len) {
	const uint8_t* ptr = static_cast<const uint8_t*>(data);
	while (len) {
#ifdef MSG_NOSIGNAL
		const ssize_t written = send(fd, ptr, len, MSG_NOSIGNAL);
#else
		const ssize_t written = send(fd, ptr, len, 0);
#endif
		if (written < 0) {
			if (errno == EINTR)
				continue;
			return false;
		}
		if (!written)
			return false;
		ptr += written;
		len -= written;
	}
	return true;
}

static int divFloorSigned(long long numerator, int denominator) {
	if (denominator <= 0)
		return 0;
	if (numerator >= 0)
		return (int)(numerator / denominator);
	return -(int)((-numerator + denominator - 1) / denominator);
}

static int divCeilSigned(long long numerator, int denominator) {
	if (denominator <= 0)
		return 0;
	if (numerator >= 0)
		return (int)((numerator + denominator - 1) / denominator);
	return -(int)((-numerator) / denominator);
}

static float colorComponent(unsigned char value) {
	return value / 255.0f;
}

static float colorAlpha(const gRGB& color) {
	return 1.0f - (color.a / 255.0f);
}

static void appendRectVertices(std::vector<float>& vertices, const eRect& area) {
	const float x = area.x();
	const float y = area.y();
	const float w = area.width();
	const float h = area.height();
	vertices.push_back(x);
	vertices.push_back(y);
	vertices.push_back(x);
	vertices.push_back(y + h);
	vertices.push_back(x + w);
	vertices.push_back(y);
	vertices.push_back(x + w);
	vertices.push_back(y);
	vertices.push_back(x);
	vertices.push_back(y + h);
	vertices.push_back(x + w);
	vertices.push_back(y + h);
}

static void appendColoredRectVertices(std::vector<float>& vertices, const eRect& area, const gRGB& color) {
	const float r = colorComponent(color.r);
	const float g = colorComponent(color.g);
	const float b = colorComponent(color.b);
	const float a = colorAlpha(color);
	const float x = area.x();
	const float y = area.y();
	const float w = area.width();
	const float h = area.height();
	const float rect_vertices[12] = {x, y, x, y + h, x + w, y, x + w, y, x, y + h, x + w, y + h};

	for (unsigned int i = 0; i < 6; ++i) {
		vertices.push_back(rect_vertices[i * 2 + 0]);
		vertices.push_back(rect_vertices[i * 2 + 1]);
		vertices.push_back(r);
		vertices.push_back(g);
		vertices.push_back(b);
		vertices.push_back(a);
	}
}

static int s_egl_animation_current = 0;
static int s_egl_animation_speed = 15;
static bool s_egl_animation_profiles = true;
static int s_egl_animation_dialog = 18;
static int s_egl_animation_popup = 16;
static int s_egl_animation_toast = 17;
static int s_egl_animation_toast_speed = 10;
static bool s_egl_animation_listbox = false;
static const int E2EGL_WINDOW_ANIMATION_MAX = 21;

static int clampInt(int value, int min_value, int max_value) {
	return std::max(min_value, std::min(max_value, value));
}

static float clampFloat(float value, float min_value, float max_value) {
	return std::max(min_value, std::min(max_value, value));
}

static bool isToastLikeWindow(const eRect& source, int screen_width, int screen_height) {
	if (source.empty())
		return false;

	const float screen_w = std::max(1.0f, (float)screen_width);
	const float screen_h = std::max(1.0f, (float)screen_height);
	const float width_ratio = (float)source.width() / screen_w;
	const float height_ratio = (float)source.height() / screen_h;
	return width_ratio > 0.08f && width_ratio < 0.94f && height_ratio < 0.28f
		&& (source.top() < (int)(screen_h * 0.24f) || source.bottom() > (int)(screen_h * 0.72f));
}

static int effectiveWindowAnimationForRect(const eRect& source, int screen_width, int screen_height) {
	const int base_animation = s_egl_animation_current;
	if (!s_egl_animation_profiles || (base_animation != 15 && base_animation != 16) || source.empty())
		return base_animation;

	const float screen_w = std::max(1.0f, (float)screen_width);
	const float screen_h = std::max(1.0f, (float)screen_height);
	const float width_ratio = (float)source.width() / screen_w;
	const float height_ratio = (float)source.height() / screen_h;
	const bool small_dialog = width_ratio < 0.68f && height_ratio < 0.68f;
	const bool toast_like = isToastLikeWindow(source, screen_width, screen_height);
	const bool side_panel = height_ratio > 0.42f && width_ratio < 0.76f
		&& (source.left() < (int)(screen_w * 0.12f) || source.right() > (int)(screen_w * 0.88f));
	const bool popup_panel = !toast_like && !small_dialog && width_ratio < 0.82f && height_ratio < 0.74f;

	if (toast_like)
		return s_egl_animation_toast;
	if (small_dialog && s_egl_animation_dialog > 0)
		return s_egl_animation_dialog;
	if ((side_panel || popup_panel) && s_egl_animation_popup > 0)
		return s_egl_animation_popup;
	return base_animation;
}

static int windowAnimationDurationMs(const eRect& source, int screen_width, int screen_height) {
	const bool toast_like = isToastLikeWindow(source, screen_width, screen_height);
	const int speed = toast_like ? s_egl_animation_toast_speed : s_egl_animation_speed;
#ifdef DREAMNEXTGEN
	const int duration_factor = 12;
#else
	const int duration_factor = 6;
#endif
	return toast_like ? clampInt(speed * duration_factor, 60, 240) : clampInt(speed * duration_factor, 80, 420);
}

static float easeOut(float t) {
	t = clampFloat(t, 0.0f, 1.0f);
	const float inv = 1.0f - t;
	return 1.0f - inv * inv;
}

static float easeInOut(float t) {
	t = clampFloat(t, 0.0f, 1.0f);
	return t * t * (3.0f - 2.0f * t);
}

static bool opcodeDrawsToSurface(gOpcode::Opcode opcode) {
	switch (opcode) {
	case gOpcode::renderText:
	case gOpcode::renderPara:
	case gOpcode::fill:
	case gOpcode::fillRegion:
	case gOpcode::clear:
	case gOpcode::blit:
	case gOpcode::gradient:
	case gOpcode::rectangle:
	case gOpcode::line:
	case gOpcode::enableSpinner:
	case gOpcode::disableSpinner:
	case gOpcode::incrementSpinner:
		return true;
	default:
		return false;
	}
}

static bool opcodeCanKeepPendingText(gOpcode::Opcode opcode) {
	switch (opcode) {
	case gOpcode::renderText:
	case gOpcode::renderPara:
	case gOpcode::setFont:
	case gOpcode::setBackgroundColor:
	case gOpcode::setForegroundColor:
	case gOpcode::setBackgroundColorRGB:
	case gOpcode::setForegroundColorRGB:
	case gOpcode::setGradient:
	case gOpcode::setRadius:
	case gOpcode::setBorder:
	case gOpcode::setOffset:
	case gOpcode::setClip:
	case gOpcode::addClip:
	case gOpcode::popClip:
		return true;
	default:
		return false;
	}
}

static bool opcodeCanRunWithoutEGLContext(gOpcode::Opcode opcode) {
	switch (opcode) {
	case gOpcode::setFont:
	case gOpcode::setBackgroundColor:
	case gOpcode::setForegroundColor:
	case gOpcode::setBackgroundColorRGB:
	case gOpcode::setForegroundColorRGB:
	case gOpcode::setGradient:
	case gOpcode::setRadius:
	case gOpcode::setBorder:
	case gOpcode::setOffset:
	case gOpcode::setClip:
	case gOpcode::addClip:
	case gOpcode::popClip:
		return true;
	default:
		return false;
	}
}

static bool regionCoversRect(const gRegion& region, const eRect& bounds) {
	if (region.extends != bounds)
		return false;

	long long covered = 0;
	for (unsigned int i = 0; i < region.rects.size(); ++i) {
		eRect rect = region.rects[i] & bounds;
		if (!rect.empty())
			covered += (long long)rect.width() * rect.height();
	}
	return covered >= (long long)bounds.width() * bounds.height();
}

static void logEGLConfig(EGLDisplay display, EGLConfig config, int version) {
	EGLint red = 0, green = 0, blue = 0, alpha = 0;
	EGLint depth = 0, stencil = 0, surface = 0, native_visual = 0;
	EGLint sample_buffers = 0, samples = 0;

	eglGetConfigAttrib(display, config, EGL_RED_SIZE, &red);
	eglGetConfigAttrib(display, config, EGL_GREEN_SIZE, &green);
	eglGetConfigAttrib(display, config, EGL_BLUE_SIZE, &blue);
	eglGetConfigAttrib(display, config, EGL_ALPHA_SIZE, &alpha);
	eglGetConfigAttrib(display, config, EGL_DEPTH_SIZE, &depth);
	eglGetConfigAttrib(display, config, EGL_STENCIL_SIZE, &stencil);
	eglGetConfigAttrib(display, config, EGL_SURFACE_TYPE, &surface);
	eglGetConfigAttrib(display, config, EGL_NATIVE_VISUAL_ID, &native_visual);
	eglGetConfigAttrib(display, config, EGL_SAMPLE_BUFFERS, &sample_buffers);
	eglGetConfigAttrib(display, config, EGL_SAMPLES, &samples);

	eDebug("[gEGLDC] EGL config GLES%d rgba=%d/%d/%d/%d depth=%d stencil=%d surface=0x%x native=0x%x samples=%d/%d",
		version, red, green, blue, alpha, depth, stencil, surface, native_visual, sample_buffers, samples);
}

static bool textRectsCanMerge(const eRect& a, const eRect& b) {
	const int overlap_top = std::max(a.top(), b.top());
	const int overlap_bottom = std::min(a.bottom(), b.bottom());
	if (overlap_top >= overlap_bottom)
		return false;

	const int min_height = std::max(1, std::min(a.height(), b.height()));
	if ((overlap_bottom - overlap_top) * 2 < min_height)
		return false;

	int gap = 0;
	if (a.right() < b.left())
		gap = b.left() - a.right();
	else if (b.right() < a.left())
		gap = a.left() - b.right();

	return gap <= 32;
}

static unsigned long long e2eglNowUs() {
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (unsigned long long)ts.tv_sec * 1000000ULL + (unsigned long long)ts.tv_nsec / 1000ULL;
}

class e2eglScopedTimer {
public:
	e2eglScopedTimer(unsigned long long& target) : m_target(target), m_start_us(e2eglNowUs()) {}
	~e2eglScopedTimer() { m_target += e2eglNowUs() - m_start_us; }

private:
	unsigned long long& m_target;
	unsigned long long m_start_us;
};

static bool e2eglTraceGlEnabled() {
	static int enabled = -1;
	if (enabled < 0) {
		const char* env = getenv("E2EGL_TRACE_GL");
		enabled = (env && *env && strcmp(env, "0")) ? 1 : 0;
	}
	return enabled != 0;
}

static unsigned int e2eglTraceGlLimit() {
	static int limit = -1;
	if (limit < 0) {
		const char* env = getenv("E2EGL_TRACE_GL_LIMIT");
		limit = env && *env ? atoi(env) : 240;
	}
	return limit < 0 ? 0 : (unsigned int)limit;
}

static unsigned long long e2eglTraceGlSlowUs() {
	static long long slow_us = -1;
	if (slow_us < 0) {
		const char* env = getenv("E2EGL_TRACE_GL_SLOW_US");
		slow_us = env && *env ? atoll(env) : 0;
	}
	return slow_us < 0 ? 0 : (unsigned long long)slow_us;
}

static bool e2eglTraceOpsEnabled() {
	static int enabled = -1;
	if (enabled < 0) {
		const char* env = getenv("E2EGL_TRACE_OPS");
		enabled = (env && *env && strcmp(env, "0")) ? 1 : 0;
	}
	return enabled != 0;
}

static bool e2eglAnimationDamageEnabled() {
	static int enabled = -1;
	if (enabled < 0) {
		const char* env = getenv("E2EGL_ANIMATION_DAMAGE");
		enabled = (!env || !*env || strcmp(env, "0")) ? 1 : 0;
	}
	return enabled != 0;
}

static unsigned long long rectPixels(const eRect& rect) {
	return rect.empty() ? 0 : (unsigned long long)rect.width() * (unsigned long long)rect.height();
}

static void logColorOp(const char* op, const eRect& area, const gRGB& color, bool blend) {
	if (!e2eglTraceOpsEnabled())
		return;

	eDebug("[e2egl:op] %s area=%d,%d %dx%d color=#%02x%02x%02x inva=%u alpha=%.3f blend=%d",
		op, area.x(), area.y(), area.width(), area.height(), color.r, color.g, color.b, color.a, colorAlpha(color), blend ? 1 : 0);
}

static void logBlitOp(const char* op, const eRect& dest, const eRect& src, gPixmap* pixmap, int flags) {
	if (!e2eglTraceOpsEnabled())
		return;

	gUnmanagedSurface* surface = pixmap ? pixmap->surface : nullptr;
	eDebug("[e2egl:op] %s dst=%d,%d %dx%d src=%d,%d %dx%d pix=%dx%dx%d tex=%u flags=0x%x transparent=%d",
		op, dest.x(), dest.y(), dest.width(), dest.height(), src.x(), src.y(), src.width(), src.height(),
		surface ? surface->x : 0, surface ? surface->y : 0, surface ? surface->bpp : 0, surface ? surface->gl_texture_id : 0,
		flags, surface && surface->transparent ? 1 : 0);
}

void gEGLDCSetAnimationCurrent(int animation) {
	s_egl_animation_current = clampInt(animation, 0, E2EGL_WINDOW_ANIMATION_MAX);
	eDebug("[gEGLDC] window animation set to %d", s_egl_animation_current);
}

void gEGLDCSetAnimationSpeed(int speed) {
	s_egl_animation_speed = clampInt(speed, 1, 100);
	eDebug("[gEGLDC] window animation speed set to %d", s_egl_animation_speed);
}

void gEGLDCSetToastAnimationSpeed(int speed) {
	s_egl_animation_toast_speed = clampInt(speed, 1, 100);
	eDebug("[gEGLDC] toast animation speed set to %d", s_egl_animation_toast_speed);
}

void gEGLDCSetAnimationListbox(int animation) {
	s_egl_animation_listbox = animation != 0;
	eDebug("[gEGLDC] smooth list selection %s", s_egl_animation_listbox ? "enabled" : "disabled");
}

bool gEGLDC::supportsListboxAnimations() const {
	return s_egl_animation_listbox;
}

void gEGLDCSetAnimationProfiles(int enabled, int dialog, int popup, int toast) {
	s_egl_animation_profiles = enabled != 0;
	s_egl_animation_dialog = clampInt(dialog, 0, E2EGL_WINDOW_ANIMATION_MAX);
	s_egl_animation_popup = clampInt(popup, 0, E2EGL_WINDOW_ANIMATION_MAX);
	s_egl_animation_toast = clampInt(toast, 0, E2EGL_WINDOW_ANIMATION_MAX);
	eDebug("[gEGLDC] window animation profiles %s: dialog=%d popup=%d toast=%d",
		s_egl_animation_profiles ? "enabled" : "disabled",
		s_egl_animation_dialog, s_egl_animation_popup, s_egl_animation_toast);
}

static glyph_key_t hashGlyphMask(gPixmap* glyph_mask) {
	const gUnmanagedSurface* surface = glyph_mask ? glyph_mask->surface : nullptr;
	if (!surface || !surface->data)
		return 0;

	const int width = surface->x;
	const int height = surface->y;
	int pitch = surface->stride ? surface->stride : width;

	uint64_t hash = 1469598103934665603ULL;
	auto mix = [&hash](uint64_t value) {
		for (int i = 0; i < 8; ++i) {
			hash ^= (value >> (i * 8)) & 0xff;
			hash *= 1099511628211ULL;
		}
	};

	mix((uint64_t)width);
	mix((uint64_t)height);
	mix((uint64_t)(uint32_t)pitch);

	const uint8_t* data = (const uint8_t*)surface->data;
	for (int row = 0; row < height; ++row) {
		const uint8_t* src_row = pitch > 0 ? data + (row * pitch) : data + ((height - 1 - row) * -pitch);
		for (int x = 0; x < width; ++x) {
			hash ^= src_row[x];
			hash *= 1099511628211ULL;
		}
	}

	return hash;
}

// Initialization is now managed by gEGLDCAutoInit in egl_init.cpp
// to support runtime fallback to FBDC/SDLDC.

// ---------------------------------------------------------------------------
// tryInitEGL – attempts to create an EGL context for a specific GLES version.
// Returns true on success.  On failure the EGL state is left clean so that the
// caller can immediately try again with a different version.
// ---------------------------------------------------------------------------
bool gEGLDC::tryInitEGL(int version) {
	if (!m_window_provider || !m_native_window_ready) {
		eDebug("[gEGLDC] no usable native window provider for GLES%d.", version);
		return false;
	}

	// 1. get the native display from our platform provider
	EGLNativeDisplayType native_display = m_window_provider->getNativeDisplay();

	m_egl_display = eglGetDisplay(native_display);
	if (m_egl_display == EGL_NO_DISPLAY) {
		eDebug("[gEGLDC] error: eglGetDisplay failed.");
		return false;
	}

	// 2. initialize EGL (only on first call; harmless to call again)
	EGLint major, minor;
	if (!eglInitialize(m_egl_display, &major, &minor)) {
		eDebug("[gEGLDC] error: eglInitialize failed.");
		return false;
	}
	m_egl_major = major;
	m_egl_minor = minor;
	eDebug("[gEGLDC] EGL version %d.%d initialised", major, minor);

	// 3. choose EGL config for the requested GLES version
	EGLint renderable_type = (version >= 3) ? EGL_OPENGL_ES3_BIT_KHR : EGL_OPENGL_ES2_BIT;

	const EGLint preserved_config_attribs[] = {
		EGL_SURFACE_TYPE, EGL_WINDOW_BIT | EGL_SWAP_BEHAVIOR_PRESERVED_BIT, EGL_RENDERABLE_TYPE, renderable_type, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
		EGL_DEPTH_SIZE, 0, EGL_STENCIL_SIZE, 0, EGL_NONE};
	const EGLint config_attribs[] = {
		EGL_SURFACE_TYPE, EGL_WINDOW_BIT, EGL_RENDERABLE_TYPE, renderable_type, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_DEPTH_SIZE, 0, EGL_STENCIL_SIZE, 0,
		EGL_NONE};

	EGLint num_configs = 0;
	m_preserved_swap = false;
	if (!e2eglForceDestroyedSwap() && eglChooseConfig(m_egl_display, preserved_config_attribs, &m_egl_config, 1, &num_configs) && num_configs > 0) {
		m_preserved_swap = true;
	} else if (!eglChooseConfig(m_egl_display, config_attribs, &m_egl_config, 1, &num_configs) || num_configs == 0) {
		eDebug("[gEGLDC] no suitable EGL config found for GLES%d.", version);
		return false;
	}
	logEGLConfig(m_egl_display, m_egl_config, version);

	// 4. create the context
	const EGLint context_attribs[] = {EGL_CONTEXT_CLIENT_VERSION, version, EGL_NONE};

	m_egl_context = eglCreateContext(m_egl_display, m_egl_config, EGL_NO_CONTEXT, context_attribs);
	if (m_egl_context == EGL_NO_CONTEXT) {
		eDebug("[gEGLDC] eglCreateContext for GLES%d failed.", version);
		return false;
	}

	// 5. create the window surface
	EGLNativeWindowType native_window = m_window_provider->getNativeWindow();
	if (!native_window && e2eglRequiresNativeWindow()) {
		eDebug("[gEGLDC] native window is not available for GLES%d.", version);
		eglDestroyContext(m_egl_display, m_egl_context);
		m_egl_context = EGL_NO_CONTEXT;
		return false;
	}
	m_egl_surface = eglCreateWindowSurface(m_egl_display, m_egl_config, native_window, nullptr);
	if (m_egl_surface == EGL_NO_SURFACE) {
		eDebug("[gEGLDC] eglCreateWindowSurface failed. EGL error: 0x%x", eglGetError());
		eglDestroyContext(m_egl_display, m_egl_context);
		m_egl_context = EGL_NO_CONTEXT;
		return false;
	}
	applySwapBehavior();

	// 6. make context current
	if (!eglMakeCurrent(m_egl_display, m_egl_surface, m_egl_surface, m_egl_context)) {
		eDebug("[gEGLDC] eglMakeCurrent failed.");
		eglDestroySurface(m_egl_display, m_egl_surface);
		eglDestroyContext(m_egl_display, m_egl_context);
		m_egl_surface = EGL_NO_SURFACE;
		m_egl_context = EGL_NO_CONTEXT;
		return false;
	}

	m_gles_version = version;
	return true;
}

bool gEGLDC::makeCurrent() {
	if (!isInitialized() || m_egl_display == EGL_NO_DISPLAY || m_egl_surface == EGL_NO_SURFACE)
		return false;

	if (eglGetCurrentContext() == m_egl_context)
		return true;

	if (!eglMakeCurrent(m_egl_display, m_egl_surface, m_egl_surface, m_egl_context)) {
		eDebug("[gEGLDC] eglMakeCurrent failed. EGL error: 0x%x", eglGetError());
		return false;
	}

	return true;
}

bool gEGLDC::releaseCurrent(bool force) {
	if (!force && e2eglKeepContextBetweenOpcodes())
		return false;
	if (m_egl_display != EGL_NO_DISPLAY && eglGetCurrentContext() == m_egl_context) {
		eglMakeCurrent(m_egl_display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
		return true;
	}
	return false;
}

void gEGLDC::applySwapBehavior() {
	if (m_egl_display == EGL_NO_DISPLAY || m_egl_surface == EGL_NO_SURFACE)
		return;

	if (e2eglForceDestroyedSwap()) {
		m_preserved_swap = false;
		if (!eglSurfaceAttrib(m_egl_display, m_egl_surface, EGL_SWAP_BEHAVIOR, EGL_BUFFER_DESTROYED))
			eDebug("[gEGLDC] EGL destroyed swap request failed for Broadcom EGL. EGL error: 0x%x", eglGetError());
		eDebug("[gEGLDC] EGL swap behavior: destroyed (Broadcom preserved swap ignored)");
		return;
	}

	if (!eglSurfaceAttrib(m_egl_display, m_egl_surface, EGL_SWAP_BEHAVIOR, EGL_BUFFER_PRESERVED)) {
		m_preserved_swap = false;
		eDebug("[gEGLDC] EGL preserved swap unavailable. EGL error: 0x%x", eglGetError());
		return;
	}

	EGLint behavior = EGL_BUFFER_DESTROYED;
	eglQuerySurface(m_egl_display, m_egl_surface, EGL_SWAP_BEHAVIOR, &behavior);
	m_preserved_swap = behavior == EGL_BUFFER_PRESERVED;
	eDebug("[gEGLDC] EGL swap behavior: %s", m_preserved_swap ? "preserved" : "destroyed");
}

void gEGLDC::primeEGLSurface(bool preserve_scene) {
#ifndef HAVE_DREAMBCM_EGL
	(void)preserve_scene;
#endif
#if defined(HAVE_VUPLUS_EGL) || defined(HAVE_VUPLUS_MIPSEL_EGL) || defined(HAVE_NXPL_EGL) || defined(HAVE_V3DPLATFORM_EGL) || defined(HAVE_HISILICON_EGL) || defined(HAVE_DREAMBCM_EGL) || defined(DREAMNEXTGEN)
	if (m_egl_display == EGL_NO_DISPLAY || m_egl_surface == EGL_NO_SURFACE || m_egl_context == EGL_NO_CONTEXT)
		return;
#ifdef HAVE_DREAMBCM_EGL
	const bool scene_preserved = preserve_scene && sceneFramebufferActive() && m_scene_frame_valid;
#else
	const bool scene_preserved = false;
#endif

	bindWindowFramebuffer();
	glDisable(GL_BLEND);
	glDisable(GL_SCISSOR_TEST);
	glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
	glViewport(0, 0, surfaceWidth(), surfaceHeight());
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);

#if defined(HAVE_V3DPLATFORM_EGL)
	const int swap_count = 3;
#elif defined(HAVE_VUPLUS_EGL)
	const int swap_count = 5;
#elif defined(DREAMNEXTGEN)
	// DreamNextGen uses three framebuffer pages. Clear every page after
	// recreating the EGL surface so no stale OSD content can become visible.
	const int swap_count = 3;
#elif defined(HAVE_NXPL_EGL)
	const int swap_count = e2eglNxplUseVideoModeSurface() ? 5 : (m_preserved_swap ? 1 : 3);
#else
	const int swap_count = m_preserved_swap ? 1 : 3;
#endif
	int cleared_swaps = 0;
	for (int i = 0; i < swap_count; ++i) {
		glClear(GL_COLOR_BUFFER_BIT);
		if (!eglSwapBuffers(m_egl_display, m_egl_surface)) {
			eDebug("[gEGLDC] EGL surface prime swap failed. EGL error: 0x%x", eglGetError());
			break;
		}
		++cleared_swaps;
	}

	glClear(GL_COLOR_BUFFER_BIT);
	glFlush();
	m_last_frame_valid = false;
	m_frame_restore_pending = false;
	invalidateSpinnerBackground(true);
	if (sceneFramebufferWanted() && ensureSceneFramebuffer() && !scene_preserved)
		clearSceneFramebuffer();
	bindWindowFramebuffer();
#ifdef HAVE_DREAMBCM_EGL
	eDebug("[gEGLDC] primed EGL surface %dx%d logical=%dx%d with %d clear swap(s), preserved=%d scene_preserved=%d",
		surfaceWidth(), surfaceHeight(), m_width, m_height, cleared_swaps, m_preserved_swap ? 1 : 0, scene_preserved ? 1 : 0);
#else
	eDebug("[gEGLDC] primed EGL surface %dx%d logical=%dx%d with %d clear swap(s), preserved=%d",
		surfaceWidth(), surfaceHeight(), m_width, m_height, cleared_swaps, m_preserved_swap ? 1 : 0);
#endif
#endif
}

// ---------------------------------------------------------------------------
// initEGL – cascades from GLES3 down to GLES2, then initialises shaders.
// ---------------------------------------------------------------------------
bool gEGLDC::initEGL() {
	if (!m_window_provider || !m_native_window_ready) {
		eDebug("[gEGLDC] native window provider unavailable, falling back.");
		return false;
	}

	auto tryGLESVersions = [this]() {
		if (tryInitEGL(3))
			return true;
		eDebug("[gEGLDC] GLES3 not available, falling back to GLES2.");
		return tryInitEGL(2);
	};

	bool egl_ready = tryGLESVersions();

#ifdef HAVE_VUPLUS_EGL
	if (!egl_ready && m_video_mode_surface_active) {
		const int failed_width = surfaceWidth();
		const int failed_height = surfaceHeight();
		struct SurfaceSize {
			int width;
			int height;
		};
		const SurfaceSize fallback_sizes[] = {
			{1280, 720}
		};

		m_video_mode_surface_active = false;
		for (const SurfaceSize& fallback : fallback_sizes) {
			if (fallback.width > failed_width || fallback.height > failed_height ||
				(fallback.width == failed_width && fallback.height == failed_height))
				continue;

			if (m_egl_display != EGL_NO_DISPLAY) {
				eglTerminate(m_egl_display);
				m_egl_display = EGL_NO_DISPLAY;
			}
			m_surface_width = fallback.width;
			m_surface_height = fallback.height;
			eDebug("[gEGLDC] Vu+ native window rejected %dx%d, retrying driver-safe surface %dx%d logical=%dx%d",
				failed_width, failed_height, fallback.width, fallback.height, m_width, m_height);
			m_native_window_ready = m_window_provider->init(fallback.width, fallback.height);
			if (!m_native_window_ready) {
				eDebug("[gEGLDC] Vu+ native window fallback init failed for %dx%d",
					fallback.width, fallback.height);
				continue;
			}
			if (tryGLESVersions()) {
				egl_ready = true;
				eDebug("[gEGLDC] Vu+ driver-safe EGL surface selected: %dx%d logical=%dx%d",
					fallback.width, fallback.height, m_width, m_height);
				break;
			}
		}
	}
#endif

	if (!egl_ready) {
		eDebug("[gEGLDC] error: neither GLES3 nor GLES2 could be initialised.");
		return false;
	}

	// Publish the detected version so all shaders can query it
	gles::version = m_gles_version;
	eDebug("[gEGLDC] GLES%d context created.", m_gles_version);

	m_texture_manager.setDisplay(m_egl_display);

	// 7. basic GL state
	applyWindowViewport();
	eglSwapInterval(m_egl_display, 1);
	glGetIntegerv(GL_MAX_TEXTURE_SIZE, &m_max_texture_size);
	eDebug("[gEGLDC] GL maximum texture size: %d", m_max_texture_size);

	const char* egl_extensions = eglQueryString(m_egl_display, EGL_EXTENSIONS);
	const char* gl_extensions = (const char*)glGetString(GL_EXTENSIONS);
#if defined(DREAMNEXTGEN) || defined(HAVE_VUPLUS_EGL) || defined(HAVE_VUPLUS_MIPSEL_EGL) || defined(HAVE_NXPL_EGL) || defined(HAVE_V3DPLATFORM_EGL) || defined(HAVE_HISILICON_EGL) || defined(HAVE_DREAMBCM_EGL)
	const bool bgra_upload = false;
#else
	const bool bgra_upload = hasExtension(gl_extensions, "GL_EXT_texture_format_BGRA8888");
#endif
	eDebug("[gEGLDC] dmabuf import: %s, EGL image target: %s, BGRA upload: %s", hasExtension(egl_extensions, "EGL_EXT_image_dma_buf_import") ? "yes" : "no",
		   hasExtension(gl_extensions, "GL_OES_EGL_image") ? "yes" : "no", bgra_upload ? "yes" : "no");

	// 8. initialise shaders and resources
	if (!m_basic_shader.init()) {
		eFatal("[gEGLDC] failed to initialise basic shader!");
		return false;
	}
	if (!m_advanced_shader.init()) {
		eFatal("[gEGLDC] failed to initialise advanced shader!");
		return false;
	}
	if (!m_texture_shader.init()) {
		eFatal("[gEGLDC] failed to initialise texture shader!");
		return false;
	}
	if (!m_text_shader.init()) {
		eFatal("[gEGLDC] failed to initialise text shader!");
		return false;
	}
	if (!m_font_atlas.init()) {
		eFatal("[gEGLDC] failed to initialise font atlas!");
		return false;
	}

	// 9. upload projection matrices
	m_basic_shader.setResolution((float)m_width, (float)m_height);
	m_advanced_shader.setResolution((float)m_width, (float)m_height);
	m_texture_shader.setResolution((float)m_width, (float)m_height);
	m_text_shader.setResolution((float)m_width, (float)m_height);
	primeEGLSurface();

	eDebug("[gEGLDC] GLES%d successfully initialised (%dx%d)", m_gles_version, m_width, m_height);
	eDebug("[gEGLDC] EGL context keep-between-opcodes: %s", e2eglKeepContextBetweenOpcodes() ? "yes" : "no");
	releaseCurrent(true);
	startCaptureServer();
	return true;
}

int gEGLDC::surfaceWidth() const {
	return m_surface_width > 0 ? m_surface_width : m_width;
}

int gEGLDC::surfaceHeight() const {
	return m_surface_height > 0 ? m_surface_height : m_height;
}

bool gEGLDC::updateVideoModeSurfaceSize(const char* reason) {
#if defined(HAVE_VUPLUS_EGL)
	if (!m_video_mode_surface_active)
		return false;
#elif defined(HAVE_NXPL_EGL)
	if (!e2eglNxplUseVideoModeSurface())
		return false;
#else
	return false;
#endif

	const std::string mode = e2eglReadTextFile("/proc/stb/video/videomode");
	int width = 0;
	int height = 0;
	if (!e2eglVideoModeToSize(mode, width, height))
		return false;
	e2eglLimitVuplusNativeSurfaceSize(width, height);

	if (width == m_surface_width && height == m_surface_height)
		return false;

	eDebug("[gEGLDC] Broadcom video surface %s: mode='%s' %dx%d -> %dx%d logical=%dx%d",
		reason ? reason : "update", mode.c_str(), m_surface_width, m_surface_height, width, height, m_width, m_height);
	m_surface_width = width;
	m_surface_height = height;
	return true;
}

int gEGLDC::scaleSurfaceFloorX(int value) const {
	if (surfaceWidth() == m_width || m_width <= 0)
		return value;
	return divFloorSigned((long long)value * surfaceWidth(), m_width);
}

int gEGLDC::scaleSurfaceCeilX(int value) const {
	if (surfaceWidth() == m_width || m_width <= 0)
		return value;
	return divCeilSigned((long long)value * surfaceWidth(), m_width);
}

int gEGLDC::scaleSurfaceFloorY(int value) const {
	if (surfaceHeight() == m_height || m_height <= 0)
		return value;
	return divFloorSigned((long long)value * surfaceHeight(), m_height);
}

int gEGLDC::scaleSurfaceCeilY(int value) const {
	if (surfaceHeight() == m_height || m_height <= 0)
		return value;
	return divCeilSigned((long long)value * surfaceHeight(), m_height);
}

bool gEGLDC::currentFramebufferUsesSurface() const {
	if (currentFramebufferIsScene())
		return sceneFramebufferUsesSurfaceScale();

	const bool osd_fullscreen = m_osd_left == 0 && m_osd_top == 0 && m_osd_width == m_width && m_osd_height == m_height;
	if (surfaceWidth() == m_width && surfaceHeight() == m_height && osd_fullscreen)
		return false;
	if (!sceneFramebufferActive())
		return true;

	GLint framebuffer = 0;
	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &framebuffer);
	return framebuffer == 0;
}

void gEGLDC::setGlScissor(const eRect& rect) {
	if (currentFramebufferIsScene()) {
		const eRect scene_rect = logicalToSceneRect(rect);
		glScissor(scene_rect.x(), m_scene_frame_height - scene_rect.bottom(), scene_rect.width(), scene_rect.height());
		return;
	}

	if (!currentFramebufferUsesSurface()) {
		int sx = rect.x();
		int sy = m_height - (rect.y() + rect.height());
		glScissor(sx, sy, rect.width(), rect.height());
		return;
	}

	const eRect surface_rect = logicalToSurfaceRect(rect);
	glScissor(surface_rect.x(), surfaceHeight() - surface_rect.bottom(), surface_rect.width(), surface_rect.height());
}

void gEGLDC::setTextureFiltering(GLuint texture, bool linear) {
	if (!texture)
		return;

	const GLint filter = linear ? GL_LINEAR : GL_NEAREST;
	glBindTexture(GL_TEXTURE_2D, texture);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
}

void gEGLDC::resetFrameStats(unsigned long long now_us) {
	if (!now_us)
		now_us = e2eglNowUs();
	const unsigned int next_frame = m_frame_stats_index + 1;
	m_frame_stats = FrameStats();
	m_frame_stats_index = next_frame;
	m_frame_stats.frame_start_us = now_us;
}

void gEGLDC::addTextureUploadStats() {
	gTextureUploadStats upload_stats;
	m_texture_manager.takeUploadStats(upload_stats);
	if (!upload_stats.textures && !upload_stats.content_cache_hits && !upload_stats.content_cache_misses)
		return;

	m_frame_stats.texture_uploads += upload_stats.textures;
	m_frame_stats.texture_dmabuf_uploads += upload_stats.dmabuf;
	m_frame_stats.texture_32_direct_uploads += upload_stats.upload32_direct;
	m_frame_stats.texture_32_converted_uploads += upload_stats.upload32_converted;
	m_frame_stats.texture_8_clut_uploads += upload_stats.upload8_clut;
	m_frame_stats.texture_8_luma_uploads += upload_stats.upload8_luma;
	m_frame_stats.texture_content_cache_hits += upload_stats.content_cache_hits;
	m_frame_stats.texture_content_cache_misses += upload_stats.content_cache_misses;
	m_frame_stats.texture_upload_pixels += upload_stats.pixels;
	m_frame_stats.texture_upload_bytes += upload_stats.bytes;
}

void gEGLDC::logAndResetFrameStats() {
	const unsigned long long now_us = e2eglNowUs();
	addTextureUploadStats();

	const unsigned long long frame_us = m_frame_stats.frame_start_us ? now_us - m_frame_stats.frame_start_us : 0;
	const unsigned long long measured_draw_us =
		m_frame_stats.fill_us + m_frame_stats.rect_us + m_frame_stats.clear_us + m_frame_stats.line_us + m_frame_stats.blit_us + m_frame_stats.text_build_us + m_frame_stats.text_us +
		m_frame_stats.state_us + m_frame_stats.overlap_us + m_frame_stats.texture_gc_us + m_frame_stats.capture_us + m_frame_stats.restore_us + m_frame_stats.copy_us;
	const unsigned long long other_us = m_frame_stats.draw_us > measured_draw_us ? m_frame_stats.draw_us - measured_draw_us : 0;
	const unsigned long long slow_us = e2eglTraceGlSlowUs();
	const unsigned int limit = e2eglTraceGlLimit();
	const bool under_limit = !limit || m_frame_stats_index <= limit;
	const bool slow_enough = !slow_us || frame_us >= slow_us;

	if (e2eglTraceGlEnabled() && under_limit && slow_enough) {
		eDebug("[e2egl:frame] #%u frame_us=%llu draw_us=%llu other_us=%llu swap_us=%llu cap_us=%llu restore_us=%llu fill_us=%llu rect_us=%llu clear_us=%llu line_us=%llu blit_us=%llu text_build_us=%llu text_us=%llu state_us=%llu overlap_us=%llu tex_gc_us=%llu copy_us=%llu ctx_make_us=%llu ctx_release_us=%llu ctx=%u/%u preserved=%d scene=%d anim=%d fill=%u/%u/%llupx solid=%u/%u clear=%u/%u/%llupx rect=%u/%u/%llupx grad=%u round=%u line=%u/%u blit=%u/%u/%llupx glyph=%u text_ops=%u text_batches=%u/%u text_flush=%u/%u/%u/%u/%u/%u/%u/%u text_overlap=%u/%u font_up=%u/%llupx tex_up=%u dmabuf=%u bgra=%u rgba_conv=%u clut8=%u lum8=%u tex_cache=%u/%u tex_px=%llu tex_kib=%llu copies=%u/%llupx restores=%u",
			m_frame_stats_index, frame_us, m_frame_stats.draw_us, other_us, m_frame_stats.swap_us, m_frame_stats.capture_us, m_frame_stats.restore_us,
			m_frame_stats.fill_us, m_frame_stats.rect_us, m_frame_stats.clear_us, m_frame_stats.line_us, m_frame_stats.blit_us, m_frame_stats.text_build_us, m_frame_stats.text_us,
			m_frame_stats.state_us, m_frame_stats.overlap_us, m_frame_stats.texture_gc_us, m_frame_stats.copy_us,
			m_frame_stats.context_make_us, m_frame_stats.context_release_us,
			m_frame_stats.context_make_calls, m_frame_stats.context_release_calls,
			m_preserved_swap ? 1 : 0, sceneFramebufferActive() ? 1 : 0, s_egl_animation_current,
			m_frame_stats.fill_ops, m_frame_stats.fill_rects, m_frame_stats.fill_pixels,
			m_frame_stats.solid_batches, m_frame_stats.solid_vertices,
			m_frame_stats.clear_ops, m_frame_stats.clear_rects, m_frame_stats.clear_pixels,
			m_frame_stats.rect_ops, m_frame_stats.rect_rects, m_frame_stats.rect_pixels,
			m_frame_stats.gradient_ops, m_frame_stats.rounded_ops,
			m_frame_stats.line_ops, m_frame_stats.line_rects,
			m_frame_stats.blit_ops, m_frame_stats.blit_rects, m_frame_stats.blit_pixels,
			m_frame_stats.glyphs, m_frame_stats.text_ops, m_frame_stats.text_batches, m_frame_stats.text_draw_rects,
			m_frame_stats.text_flush_fill, m_frame_stats.text_flush_rect, m_frame_stats.text_flush_line, m_frame_stats.text_flush_blit, m_frame_stats.text_flush_clear, m_frame_stats.text_flush_state,
			m_frame_stats.text_flush_atlas, m_frame_stats.text_flush_limit,
			m_frame_stats.text_overlap_checks, m_frame_stats.text_overlap_rect_tests,
			m_frame_stats.font_uploads, m_frame_stats.font_upload_pixels,
			m_frame_stats.texture_uploads, m_frame_stats.texture_dmabuf_uploads, m_frame_stats.texture_32_direct_uploads, m_frame_stats.texture_32_converted_uploads,
			m_frame_stats.texture_8_clut_uploads, m_frame_stats.texture_8_luma_uploads, m_frame_stats.texture_content_cache_hits, m_frame_stats.texture_content_cache_misses,
			m_frame_stats.texture_upload_pixels, m_frame_stats.texture_upload_bytes / 1024ULL,
			m_frame_stats.frame_copy_draws, m_frame_stats.frame_copy_pixels, m_frame_stats.frame_restores);
	}

	resetFrameStats(now_us);
}

void gEGLDC::drawRegion(const gRegion& region, const gRGB& color, bool blend, bool count_stats) {
	if (region.rects.empty())
		return;

	const bool use_blend = blend;
	if (m_fill_batch_valid && m_fill_batch_blend != use_blend)
		flushFillBatch();

	unsigned int drawn_rects = 0;
	unsigned long long drawn_pixels = 0;
	for (unsigned int i = 0; i < region.rects.size(); ++i) {
		eRect area = region.rects[i] & eRect(0, 0, m_width, m_height);
		if (!area.empty()) {
			logColorOp("fill", area, color, use_blend);
			appendColoredRectVertices(m_fill_batch_buffer, area, color);
			if (m_fill_batch_valid)
				m_fill_batch_bounds |= area;
			else {
				m_fill_batch_bounds = area;
				m_fill_batch_color = color;
				m_fill_batch_blend = use_blend;
				m_fill_batch_valid = true;
			}
			++drawn_rects;
			drawn_pixels += rectPixels(area);
		}
	}
	if (drawn_rects && count_stats) {
		++m_frame_stats.fill_ops;
		m_frame_stats.fill_rects += drawn_rects;
		m_frame_stats.fill_pixels += drawn_pixels;
	}
}

void gEGLDC::flushFillBatch() {
	if (!m_fill_batch_valid || m_fill_batch_buffer.empty())
		return;

	e2eglScopedTimer timer(m_frame_stats.fill_us);
	if (m_fill_batch_blend) {
		glEnable(GL_BLEND);
		glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
	} else {
		glDisable(GL_BLEND);
	}

	glDisable(GL_SCISSOR_TEST);
	m_basic_shader.drawColoredRectBatch(m_fill_batch_buffer.data(), m_fill_batch_buffer.size() / 6);
	++m_frame_stats.solid_batches;
	m_frame_stats.solid_vertices += m_fill_batch_buffer.size() / 6;

	if (m_fill_batch_blend)
		glDisable(GL_BLEND);

	m_fill_batch_buffer.clear();
	m_fill_batch_bounds = eRect::emptyRect();
	m_fill_batch_valid = false;
}

bool gEGLDC::fillBatchIntersects(const eRect& area) const {
	if (!m_fill_batch_valid || m_fill_batch_buffer.empty() || area.empty())
		return false;
	return m_fill_batch_bounds.intersects(area);
}

bool gEGLDC::fillBatchIntersects(const gRegion& region) const {
	if (!m_fill_batch_valid || m_fill_batch_buffer.empty() || region.empty())
		return false;
	if (!m_fill_batch_bounds.intersects(region.extends))
		return false;
	for (unsigned int i = 0; i < region.rects.size(); ++i) {
		if (m_fill_batch_bounds.intersects(region.rects[i]))
			return true;
	}
	return false;
}

void gEGLDC::flushFillBatchIfOverlaps(const eRect& area) {
	if (fillBatchIntersects(area))
		flushFillBatch();
}

void gEGLDC::flushFillBatchIfOverlaps(const gRegion& region) {
	if (fillBatchIntersects(region))
		flushFillBatch();
}

void gEGLDC::resetRectangleState() {
	m_border_width = 0;
	m_radius = 0;
	m_radius_edges = 0;
	m_gradient_orientation = 0;
	m_gradient_fullSize = 0;
	m_gradient_alphablend = false;
	m_gradient_colors.clear();
}

void gEGLDC::resetBlitState() {
	m_radius = 0;
	m_radius_edges = 0;
}

bool gEGLDC::textBatchIntersects(const eRect& area) {
	if (m_text_batch_buffer.empty() || !m_text_batch_bounds_valid || area.empty())
		return false;
	if (!m_text_batch_bounds.intersects(area))
		return false;
	e2eglScopedTimer timer(m_frame_stats.overlap_us);
	++m_frame_stats.text_overlap_checks;
	if (m_text_batch_rects.empty())
		return true;
	for (unsigned int i = 0; i < m_text_batch_rects.size(); ++i) {
		++m_frame_stats.text_overlap_rect_tests;
		if (m_text_batch_rects[i].intersects(area))
			return true;
	}
	return false;
}

bool gEGLDC::textBatchIntersects(const gRegion& region) {
	if (m_text_batch_buffer.empty() || !m_text_batch_bounds_valid || region.empty())
		return false;
	if (!m_text_batch_bounds.intersects(region.extends))
		return false;
	e2eglScopedTimer timer(m_frame_stats.overlap_us);
	++m_frame_stats.text_overlap_checks;
	if (m_text_batch_rects.empty()) {
		for (unsigned int i = 0; i < region.rects.size(); ++i) {
			if (m_text_batch_bounds.intersects(region.rects[i]))
				return true;
		}
		return false;
	}
	for (unsigned int i = 0; i < m_text_batch_rects.size(); ++i) {
		const eRect& text_rect = m_text_batch_rects[i];
		if (!text_rect.intersects(region.extends))
			continue;
		for (unsigned int j = 0; j < region.rects.size(); ++j) {
			++m_frame_stats.text_overlap_rect_tests;
			if (text_rect.intersects(region.rects[j]))
				return true;
		}
	}
	return false;
}

void gEGLDC::noteTextFlushReason(TextFlushReason reason) {
	switch (reason) {
		case textFlushFill:
			++m_frame_stats.text_flush_fill;
			break;
		case textFlushRectangle:
			++m_frame_stats.text_flush_rect;
			break;
		case textFlushLine:
			++m_frame_stats.text_flush_line;
			break;
		case textFlushBlit:
			++m_frame_stats.text_flush_blit;
			break;
		case textFlushClear:
			++m_frame_stats.text_flush_clear;
			break;
		case textFlushState:
			++m_frame_stats.text_flush_state;
			break;
		case textFlushAtlas:
			++m_frame_stats.text_flush_atlas;
			break;
		case textFlushLimit:
			++m_frame_stats.text_flush_limit;
			break;
	}
}

void gEGLDC::flushTextBatchForReason(TextFlushReason reason) {
	if (!m_text_batch_buffer.empty())
		noteTextFlushReason(reason);
	flushTextBatch();
}

void gEGLDC::flushTextBatchIfOverlaps(const eRect& area, TextFlushReason reason) {
	if (textBatchIntersects(area))
		flushTextBatchForReason(reason);
}

void gEGLDC::flushTextBatchIfOverlaps(const gRegion& region, TextFlushReason reason) {
	if (textBatchIntersects(region))
		flushTextBatchForReason(reason);
}

void gEGLDC::addTextBatchRect(const eRect& rect) {
	if (rect.empty())
		return;

	const size_t search_count = std::min<size_t>(m_text_batch_rects.size(), 8);
	for (size_t offset = 0; offset < search_count; ++offset) {
		eRect& existing = m_text_batch_rects[m_text_batch_rects.size() - 1 - offset];
		if (textRectsCanMerge(existing, rect)) {
			existing |= rect;
			return;
		}
	}
	m_text_batch_rects.push_back(rect);
}

eRect gEGLDC::lineDrawBounds(const gOpcode::para::pline* op) const {
	if (!op)
		return eRect::emptyRect();
	const int x1 = std::min(op->start.x(), op->end.x()) + m_current_offset.x();
	const int y1 = std::min(op->start.y(), op->end.y()) + m_current_offset.y();
	const int x2 = std::max(op->start.x(), op->end.x()) + m_current_offset.x();
	const int y2 = std::max(op->start.y(), op->end.y()) + m_current_offset.y();
	return eRect(x1, y1, x2 - x1 + 1, y2 - y1 + 1);
}

eRect gEGLDC::blitDrawBounds(const gOpcode::para::pblit* op) const {
	if (!op || !op->pixmap)
		return eRect::emptyRect();

	const eSize src_size = op->pixmap->size();
	if (src_size.isEmpty())
		return eRect::emptyRect();

	int flags = op->flags;
	eRect pos = op->position;
	pos.moveBy(m_current_offset);

	if (!(flags & gPixmap::blitScale)) {
		if (op->position.size().isValid()) {
			if (flags & gPixmap::blitHAlignCenter)
				pos.setLeft(pos.left() + (op->position.width() - src_size.width()) / 2);
			else if (flags & gPixmap::blitHAlignRight)
				pos.setLeft(pos.right() - src_size.width());

			if (flags & gPixmap::blitVAlignCenter)
				pos.setTop(pos.top() + (op->position.height() - src_size.height()) / 2);
			else if (flags & gPixmap::blitVAlignBottom)
				pos.setTop(pos.bottom() - src_size.height());
		}
		pos.setWidth(src_size.width());
		pos.setHeight(src_size.height());
	} else if (pos.size() == src_size) {
		flags &= ~gPixmap::blitScale;
	} else if (!pos.size().isEmpty()) {
		if (flags & gPixmap::blitKeepAspectRatio) {
			const int scaled_width_by_height = src_size.width() * pos.height() / src_size.height();
			const int scaled_height_by_width = src_size.height() * pos.width() / src_size.width();
			if (scaled_width_by_height <= pos.width()) {
				int old_width = pos.width();
				pos.setWidth(scaled_width_by_height);
				if (flags & gPixmap::blitHAlignCenter)
					pos.moveBy((old_width - pos.width()) / 2, 0);
				else if (flags & gPixmap::blitHAlignRight)
					pos.moveBy(old_width - pos.width(), 0);
			} else {
				int old_height = pos.height();
				pos.setHeight(scaled_height_by_width);
				if (flags & gPixmap::blitVAlignCenter)
					pos.moveBy(0, (old_height - pos.height()) / 2);
				else if (flags & gPixmap::blitVAlignBottom)
					pos.moveBy(0, old_height - pos.height());
			}
		}
	}

	if (op->clip.valid()) {
		eRect c = op->clip;
		c.moveBy(m_current_offset);
		return pos & c & m_current_clip.extends;
	}
	return pos & m_current_clip.extends;
}

void gEGLDC::executeFill(const gOpcode* op) {
	eRect area = op->parm.fill->area;
	area.moveBy(m_current_offset);
	gRegion clip = m_current_clip & area;

	drawRegion(clip, m_foreground_color_rgb);
}

void gEGLDC::executeFillRegion(const gOpcode* op) {
	gRegion region = op->parm.fillRegion->region;
	region.moveBy(m_current_offset);
	gRegion clip = m_current_clip & region;

	drawRegion(clip, m_foreground_color_rgb);
}

void gEGLDC::executeRectangle(const gOpcode* op) {
	e2eglScopedTimer timer(m_frame_stats.rect_us);
	eRect area = op->parm.rectangle->area;
	area.moveBy(m_current_offset);
	gRegion clip = m_current_clip & area;
	if (clip.rects.empty())
		return;

	++m_frame_stats.rect_ops;
	m_frame_stats.rect_rects += clip.rects.size();
	if (m_gradient_colors.size() > 0)
		++m_frame_stats.gradient_ops;
	if (m_radius > 0)
		++m_frame_stats.rounded_ops;
	for (unsigned int i = 0; i < clip.rects.size(); ++i)
		m_frame_stats.rect_pixels += rectPixels(clip.rects[i] & area);

	glEnable(GL_SCISSOR_TEST);

	if (m_border_width > 0) {
		const bool blend_border = op->parm.rectangle->useNew || m_radius > 0;
		if (blend_border) {
			glEnable(GL_BLEND);
			glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
		} else {
			glDisable(GL_BLEND);
		}
		const int border_width = std::min(m_border_width, std::min(area.width(), area.height()) / 2);
		for (unsigned int i = 0; i < clip.rects.size(); ++i) {
			setGlScissor(clip.rects[i]);
			logColorOp("rect-border", area, m_border_color, blend_border);
			m_advanced_shader.drawAdvancedRect(area.x(), area.y(), area.width(), area.height(), m_radius, m_radius_edges, std::vector<gRGB>(), 0, false, 0, colorAlpha(m_border_color), m_border_color);
		}
		if (blend_border)
			glDisable(GL_BLEND);

		area = eRect(area.left() + border_width, area.top() + border_width, area.width() - 2 * border_width, area.height() - 2 * border_width);
		if (area.empty()) {
			glDisable(GL_SCISSOR_TEST);
			return;
		}
	}

	if (m_radius > 0 || m_gradient_colors.size() > 0) {
		const bool blend_rect = op->parm.rectangle->useNew || m_radius > 0 || (m_gradient_colors.size() > 0 && m_gradient_alphablend);
		if (blend_rect) {
			glEnable(GL_BLEND);
			glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
		} else {
			glDisable(GL_BLEND);
		}
		int inner_radius = m_radius;
		if (m_border_width > 0)
			inner_radius = std::max(0, m_radius - m_border_width);
		for (unsigned int i = 0; i < clip.rects.size(); ++i) {
			setGlScissor(clip.rects[i]);
			logColorOp(m_gradient_colors.size() > 0 ? "rect-gradient" : "rect-rounded", area, m_background_color_rgb, blend_rect);
			m_advanced_shader.drawAdvancedRect(area.x(), area.y(), area.width(), area.height(), inner_radius, m_radius_edges, m_gradient_colors, m_gradient_orientation, m_gradient_alphablend > 0,
											   m_gradient_fullSize, colorAlpha(m_background_color_rgb), m_background_color_rgb);
		}
		if (blend_rect)
			glDisable(GL_BLEND);
	} else {
		const bool blend_rect = op->parm.rectangle->useNew;
		if (blend_rect) {
			glEnable(GL_BLEND);
			glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
		} else {
			glDisable(GL_BLEND);
		}
		std::vector<float> vertices;
		vertices.reserve(clip.rects.size() * 12);
		for (unsigned int i = 0; i < clip.rects.size(); ++i) {
			eRect draw = clip.rects[i] & area & eRect(0, 0, m_width, m_height);
			if (!draw.empty()) {
				logColorOp("rect", draw, m_background_color_rgb, blend_rect);
				appendRectVertices(vertices, draw);
			}
		}
		if (!vertices.empty()) {
			glDisable(GL_SCISSOR_TEST);
			m_basic_shader.drawRectBatch(vertices.data(), vertices.size() / 2, colorComponent(m_background_color_rgb.r), colorComponent(m_background_color_rgb.g),
										colorComponent(m_background_color_rgb.b), colorAlpha(m_background_color_rgb));
			++m_frame_stats.solid_batches;
			m_frame_stats.solid_vertices += vertices.size() / 2;
		}
		if (blend_rect)
			glDisable(GL_BLEND);
	}

	glDisable(GL_SCISSOR_TEST);
}

void gEGLDC::executeClear(const gOpcode*) {
	e2eglScopedTimer timer(m_frame_stats.clear_us);
	if (m_background_color_rgb.a == 255) {
		const eRect full_frame(0, 0, m_width, m_height);
		++m_frame_stats.clear_ops;
		glDisable(GL_BLEND);
		if (regionCoversRect(m_current_clip, full_frame)) {
			glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
			glDisable(GL_SCISSOR_TEST);
			logColorOp("clear-transparent", full_frame, m_background_color_rgb, false);
			glClear(GL_COLOR_BUFFER_BIT);
			++m_frame_stats.clear_rects;
			m_frame_stats.clear_pixels += rectPixels(full_frame);
			return;
		}

		if (currentFramebufferUsesSurface()) {
			for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
				eRect area = m_current_clip.rects[i] & full_frame;
				if (!area.empty()) {
					logColorOp("clear-transparent-rect", area, m_background_color_rgb, false);
					++m_frame_stats.clear_rects;
					m_frame_stats.clear_pixels += rectPixels(area);
				}
			}
			drawRegion(m_current_clip, m_background_color_rgb, false, false);
			return;
		}

		glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
		{
			glEnable(GL_SCISSOR_TEST);
			for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
				eRect area = m_current_clip.rects[i] & full_frame;
				if (!area.empty()) {
					setGlScissor(area);
					logColorOp("clear-transparent", area, m_background_color_rgb, false);
					glClear(GL_COLOR_BUFFER_BIT);
					++m_frame_stats.clear_rects;
					m_frame_stats.clear_pixels += rectPixels(area);
				}
			}
			glDisable(GL_SCISSOR_TEST);
		}
		return;
	}

	++m_frame_stats.clear_ops;
	drawRegion(m_current_clip, m_background_color_rgb);
}

void gEGLDC::executeLine(const gOpcode* op) {
	e2eglScopedTimer timer(m_frame_stats.line_us);
	if (m_current_clip.rects.empty())
		return;

	++m_frame_stats.line_ops;
	m_frame_stats.line_rects += m_current_clip.rects.size();

	const bool blend_line = colorAlpha(m_foreground_color_rgb) < 1.0f;
	if (blend_line) {
		glEnable(GL_BLEND);
		glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
	} else {
		glDisable(GL_BLEND);
	}
	glEnable(GL_SCISSOR_TEST);
	for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
		setGlScissor(m_current_clip.rects[i]);
		m_basic_shader.drawLine(op->parm.line->start.x() + m_current_offset.x(), op->parm.line->start.y() + m_current_offset.y(), op->parm.line->end.x() + m_current_offset.x(),
								op->parm.line->end.y() + m_current_offset.y(), colorComponent(m_foreground_color_rgb.r), colorComponent(m_foreground_color_rgb.g),
								colorComponent(m_foreground_color_rgb.b), colorAlpha(m_foreground_color_rgb));
	}
	glDisable(GL_SCISSOR_TEST);
	if (blend_line)
		glDisable(GL_BLEND);
}

void gEGLDC::executeBlit(const gOpcode* opcode) {
	e2eglScopedTimer timer(m_frame_stats.blit_us);
	const gOpcode::para::pblit* op = opcode->parm.blit;
	if (!op->pixmap)
		return;

	GLuint tex_id = m_texture_manager.getTexture(op->pixmap);
	if (tex_id == 0)
		return;

	const eSize src_size = op->pixmap->size();
	if (src_size.isEmpty())
		return;

	int flags = op->flags;
	if (!op->pixmap->surface->transparent)
		flags &= ~(gPixmap::blitAlphaTest | gPixmap::blitAlphaBlend);

	eRect pos = op->position;
	pos.moveBy(m_current_offset);

	if (!(flags & gPixmap::blitScale)) {
		if (op->position.size().isValid()) {
			if (flags & gPixmap::blitHAlignCenter)
				pos.setLeft(pos.left() + (op->position.width() - src_size.width()) / 2);
			else if (flags & gPixmap::blitHAlignRight)
				pos.setLeft(pos.right() - src_size.width());

			if (flags & gPixmap::blitVAlignCenter)
				pos.setTop(pos.top() + (op->position.height() - src_size.height()) / 2);
			else if (flags & gPixmap::blitVAlignBottom)
				pos.setTop(pos.bottom() - src_size.height());
		}
		pos.setWidth(src_size.width());
		pos.setHeight(src_size.height());
	} else if (pos.size() == src_size) {
		flags &= ~gPixmap::blitScale;
	} else if (!pos.size().isEmpty()) {
		if (flags & gPixmap::blitKeepAspectRatio) {
			const int scaled_width_by_height = src_size.width() * pos.height() / src_size.height();
			const int scaled_height_by_width = src_size.height() * pos.width() / src_size.width();
			if (scaled_width_by_height <= pos.width()) {
				int old_width = pos.width();
				pos.setWidth(scaled_width_by_height);
				if (flags & gPixmap::blitHAlignCenter)
					pos.moveBy((old_width - pos.width()) / 2, 0);
				else if (flags & gPixmap::blitHAlignRight)
					pos.moveBy(old_width - pos.width(), 0);
			} else {
				int old_height = pos.height();
				pos.setHeight(scaled_height_by_width);
				if (flags & gPixmap::blitVAlignCenter)
					pos.moveBy(0, (old_height - pos.height()) / 2);
				else if (flags & gPixmap::blitVAlignBottom)
					pos.moveBy(0, old_height - pos.height());
			}
		}
	}

	if (pos.empty())
		return;

	gRegion clip;
	if (op->clip.valid()) {
		eRect c = op->clip;
		c.moveBy(m_current_offset);
		clip = gRegion(c) & m_current_clip;
	} else {
		clip = m_current_clip;
	}

	if (clip.rects.empty())
		return;

	++m_frame_stats.blit_ops;

	bool enable_blend = (flags & gPixmap::blitAlphaBlend) || m_radius > 0;
	if (enable_blend) {
		glEnable(GL_BLEND);
		glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
	} else {
		glDisable(GL_BLEND);
	}

	const bool alpha_texture = flags & (gPixmap::blitAlphaTest | gPixmap::blitAlphaBlend);
	setTextureFiltering(tex_id, !alpha_texture);

	glEnable(GL_SCISSOR_TEST);
	for (unsigned int i = 0; i < clip.rects.size(); ++i) {
		eRect area = pos;
		area &= clip.rects[i];
		area &= eRect(ePoint(0, 0), size());
		if (area.empty())
			continue;

		eRect srcarea = area;
		srcarea.moveBy(-pos.x(), -pos.y());

		if (flags & gPixmap::blitScale) {
			srcarea = eRect(srcarea.x() * src_size.width() / pos.width(), srcarea.y() * src_size.height() / pos.height(), std::max(1, srcarea.width() * src_size.width() / pos.width()),
							std::max(1, srcarea.height() * src_size.height() / pos.height()));
		}

		srcarea &= eRect(ePoint(0, 0), src_size);
		if (srcarea.empty())
			continue;

		const float u0 = (float)srcarea.left() / (float)src_size.width();
		const float v0 = (float)srcarea.top() / (float)src_size.height();
		const float u1 = (float)srcarea.right() / (float)src_size.width();
		const float v1 = (float)srcarea.bottom() / (float)src_size.height();
		const bool luma_texture = op->pixmap->surface->bpp == 8 && !op->pixmap->surface->clut.data;

		setGlScissor(area);
		logBlitOp("blit", area, srcarea, op->pixmap, flags);
		m_texture_shader.drawTexture(area.x(), area.y(), area.width(), area.height(), tex_id, 1.0f, m_radius, m_radius_edges, u0, v0, u1, v1, flags & gPixmap::blitAlphaTest,
			luma_texture, pos.x(), pos.y(), pos.width(), pos.height());
		++m_frame_stats.blit_rects;
		m_frame_stats.blit_pixels += rectPixels(area);
	}
	glDisable(GL_SCISSOR_TEST);

	if (enable_blend) {
		glDisable(GL_BLEND);
	}
}

void gEGLDC::fillTextBackground(const gRegion& clip) {
	flushTextBatchIfOverlaps(clip, textFlushFill);
	drawRegion(clip, m_foreground_color_rgb);
}

void gEGLDC::drawPixmap(gPixmap* pixmap, const eRect& pos, int flags) {
	e2eglScopedTimer timer(m_frame_stats.blit_us);
	if (!pixmap || !pixmap->surface || pos.empty())
		return;

	eSize src_size = pixmap->size();
	if (src_size.isEmpty())
		return;

	eRect dest = pos;
	if (!(flags & gPixmap::blitScale)) {
		dest.setWidth(src_size.width());
		dest.setHeight(src_size.height());
	} else if (dest.size().isEmpty()) {
		dest.setWidth(src_size.width());
		dest.setHeight(src_size.height());
		flags &= ~gPixmap::blitScale;
	}

	GLuint tex_id = m_texture_manager.getTexture(pixmap);
	if (!tex_id)
		return;

	eRect screen(ePoint(0, 0), size());
	eRect area = dest & screen;
	if (!(flags & gPixmap::blitScale) && pos.size().isValid())
		area &= pos;
	if (area.empty())
		return;

	flushFillBatchIfOverlaps(area);

	eRect srcarea = area;
	srcarea.moveBy(-dest.x(), -dest.y());
	if (flags & gPixmap::blitScale) {
		srcarea = eRect(srcarea.x() * src_size.width() / dest.width(), srcarea.y() * src_size.height() / dest.height(), std::max(1, srcarea.width() * src_size.width() / dest.width()),
						std::max(1, srcarea.height() * src_size.height() / dest.height()));
	}
	srcarea &= eRect(ePoint(0, 0), src_size);
	if (srcarea.empty())
		return;

	const float u0 = (float)srcarea.left() / (float)src_size.width();
	const float v0 = (float)srcarea.top() / (float)src_size.height();
	const float u1 = (float)srcarea.right() / (float)src_size.width();
	const float v1 = (float)srcarea.bottom() / (float)src_size.height();
	const bool luma_texture = pixmap->surface->bpp == 8 && !pixmap->surface->clut.data;

	const bool blend = flags & gPixmap::blitAlphaBlend;
	if (blend) {
		glEnable(GL_BLEND);
		glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
	} else {
		glDisable(GL_BLEND);
	}

	const bool alpha_texture = flags & (gPixmap::blitAlphaTest | gPixmap::blitAlphaBlend);
	setTextureFiltering(tex_id, !alpha_texture);

	glEnable(GL_SCISSOR_TEST);
	setGlScissor(area);
	logBlitOp("drawPixmap", area, srcarea, pixmap, flags);
	m_texture_shader.drawTexture(area.x(), area.y(), area.width(), area.height(), tex_id, 1.0f, 0.0f, 0, u0, v0, u1, v1, flags & gPixmap::blitAlphaTest, luma_texture);
	glDisable(GL_SCISSOR_TEST);
	++m_frame_stats.blit_ops;
	++m_frame_stats.blit_rects;
	m_frame_stats.blit_pixels += rectPixels(area);

	if (blend)
		glDisable(GL_BLEND);
}

bool gEGLDC::readFramebufferRegion(const eRect& pos, gPixmap* pixmap) {
	if (!pixmap || !pixmap->surface || pixmap->surface->bpp != 32 || pos.empty())
		return false;

	flushFillBatchIfOverlaps(pos);

	const int width = std::min(pos.width(), pixmap->size().width());
	const int height = std::min(pos.height(), pixmap->size().height());
	if (width <= 0 || height <= 0)
		return false;

	gUnmanagedSurface* surface = pixmap->surface;
	m_texture_manager.prepareSurface(surface);
	if (surface->gl_texture_id) {
		m_texture_manager.queueForDeletion(surface->gl_texture_id);
		surface->gl_texture_id = 0;
	}

	const bool scene_framebuffer = sceneFramebufferActive();
	const bool scaled_scene_framebuffer = scene_framebuffer && sceneFramebufferUsesSurfaceScale();
	const bool window_framebuffer = !scene_framebuffer && currentFramebufferUsesSurface();
	const eRect logical_read(pos.x(), pos.y(), width, height);
	const eRect framebuffer_read = scaled_scene_framebuffer ? logicalToSceneRect(logical_read) :
		(window_framebuffer ? logicalToSurfaceRect(logical_read) : logical_read);
	const int read_x0 = framebuffer_read.x();
	const int read_y0 = framebuffer_read.y();
	const int read_width = framebuffer_read.width();
	const int read_height = framebuffer_read.height();
	const int read_y1 = read_y0 + read_height;
	const int framebuffer_height = scene_framebuffer ? m_scene_frame_height : (window_framebuffer ? surfaceHeight() : m_height);
	if (read_width <= 0 || read_height <= 0 || framebuffer_height <= 0)
		return false;

	std::vector<uint8_t> rgba(read_width * read_height * 4);
	GLint previous_framebuffer = 0;
	if (scene_framebuffer) {
		glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
		glBindFramebuffer(GL_FRAMEBUFFER, m_scene_framebuffer);
	}
	glReadPixels(read_x0, framebuffer_height - read_y1, read_width, read_height, GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
	if (scene_framebuffer)
		glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);

	const bool scale_readback = scaled_scene_framebuffer || window_framebuffer;
	for (int y = 0; y < height; ++y) {
		uint8_t* dst = (uint8_t*)surface->data + y * surface->stride;
		const int src_y_top = scale_readback ? std::min(read_height - 1, (int)(((long long)y * read_height) / height)) : y;
		const uint8_t* src_row = rgba.data() + (read_height - 1 - src_y_top) * read_width * 4;
		for (int x = 0; x < width; ++x) {
			const int src_x = scale_readback ? std::min(read_width - 1, (int)(((long long)x * read_width) / width)) : x;
			const uint8_t* src = src_row + src_x * 4;
			dst[x * 4 + 0] = src[2];
			dst[x * 4 + 1] = src[1];
			dst[x * 4 + 2] = src[0];
			dst[x * 4 + 3] = src[3];
		}
	}

	return true;
}

bool gEGLDC::readOSDToBGRA(std::vector<unsigned char>& pixels, int& width, int& height) {
	pixels.clear();
	width = 0;
	height = 0;

	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);
	if (!isInitialized() || m_egl_display == EGL_NO_DISPLAY || m_egl_surface == EGL_NO_SURFACE || m_egl_context == EGL_NO_CONTEXT)
		return false;

	const bool already_current = eglGetCurrentContext() == m_egl_context;
	if (!already_current && !makeCurrent())
		return false;

	flushFillBatch();
	flushTextBatch();

	GLint previous_framebuffer = 0;
	GLint previous_pack_alignment = 0;
	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glGetIntegerv(GL_PACK_ALIGNMENT, &previous_pack_alignment);

	const bool read_scene_framebuffer = sceneFramebufferActive();
	int read_width = 0;
	int read_height = 0;
	if (read_scene_framebuffer) {
		glBindFramebuffer(GL_FRAMEBUFFER, m_scene_framebuffer);
		width = m_width;
		height = m_height;
		read_width = m_scene_frame_width;
		read_height = m_scene_frame_height;
	} else {
		glBindFramebuffer(GL_FRAMEBUFFER, 0);
		width = surfaceWidth();
		height = surfaceHeight();
		read_width = width;
		read_height = height;
	}

	if (width <= 0 || height <= 0 || read_width <= 0 || read_height <= 0) {
		glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
		glPixelStorei(GL_PACK_ALIGNMENT, previous_pack_alignment);
		if (!already_current)
			releaseCurrent(true);
		return false;
	}

	std::vector<uint8_t> rgba((size_t)read_width * (size_t)read_height * 4U);
	while (glGetError() != GL_NO_ERROR) {
	}
	glPixelStorei(GL_PACK_ALIGNMENT, 1);
	glFinish();
	glReadPixels(0, 0, read_width, read_height, GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
	const GLenum error = glGetError();

	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
	glPixelStorei(GL_PACK_ALIGNMENT, previous_pack_alignment);
	if (!already_current)
		releaseCurrent(true);

	if (error != GL_NO_ERROR) {
		eDebug("[gEGLDC] e2egl capture glReadPixels failed: 0x%x", error);
		width = 0;
		height = 0;
		return false;
	}

	pixels.resize((size_t)width * (size_t)height * 4U);
	for (int y = 0; y < height; ++y) {
		const int src_y = std::min(read_height - 1, (int)(((long long)y * read_height) / height));
		const uint8_t* src_row = rgba.data() + (size_t)(read_height - 1 - src_y) * (size_t)read_width * 4U;
		uint8_t* dst_row = pixels.data() + (size_t)y * (size_t)width * 4U;
		for (int x = 0; x < width; ++x) {
			const int src_x = std::min(read_width - 1, (int)(((long long)x * read_width) / width));
			const uint8_t* src = src_row + (size_t)src_x * 4U;
			uint8_t* dst = dst_row + (size_t)x * 4U;
			const unsigned int alpha = src[3];
			unsigned int red = src[0];
			unsigned int green = src[1];
			unsigned int blue = src[2];
			if (alpha == 0) {
				red = green = blue = 0;
			} else if (alpha < 255) {
				red = std::min(255U, (red * 255U + alpha / 2U) / alpha);
				green = std::min(255U, (green * 255U + alpha / 2U) / alpha);
				blue = std::min(255U, (blue * 255U + alpha / 2U) / alpha);
			}
			dst[0] = (uint8_t)blue;
			dst[1] = (uint8_t)green;
			dst[2] = (uint8_t)red;
			dst[3] = (uint8_t)alpha;
		}
	}

	return true;
}

bool gEGLDC::writeCaptureFrame(int client_fd) {
	std::vector<unsigned char> pixels;
	int width = 0;
	int height = 0;
	if (!readOSDToBGRA(pixels, width, height))
		return false;

	E2EGLCaptureHeader header;
	memset(&header, 0, sizeof(header));
	memcpy(header.magic, E2EGL_CAPTURE_MAGIC, sizeof(header.magic));
	header.width = (uint32_t)width;
	header.height = (uint32_t)height;
	header.stride = (uint32_t)width * 4U;
	header.format = E2EGL_CAPTURE_FORMAT_BGRA;

	return e2eglWriteAll(client_fd, &header, sizeof(header)) && e2eglWriteAll(client_fd, pixels.data(), pixels.size());
}

void gEGLDC::startCaptureServer() {
	if (m_capture_thread_started || m_capture_socket_fd >= 0)
		return;

	int fd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (fd < 0) {
		eDebug("[gEGLDC] failed to create e2egl capture socket: %m");
		return;
	}

	const int flags = fcntl(fd, F_GETFD);
	if (flags >= 0)
		fcntl(fd, F_SETFD, flags | FD_CLOEXEC);

	unlink(E2EGL_CAPTURE_SOCKET);

	struct sockaddr_un addr;
	memset(&addr, 0, sizeof(addr));
	addr.sun_family = AF_UNIX;
	strncpy(addr.sun_path, E2EGL_CAPTURE_SOCKET, sizeof(addr.sun_path) - 1);

	if (bind(fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
		eDebug("[gEGLDC] failed to bind e2egl capture socket %s: %m", E2EGL_CAPTURE_SOCKET);
		close(fd);
		return;
	}

	if (listen(fd, 2) < 0) {
		eDebug("[gEGLDC] failed to listen on e2egl capture socket %s: %m", E2EGL_CAPTURE_SOCKET);
		close(fd);
		unlink(E2EGL_CAPTURE_SOCKET);
		return;
	}

	m_capture_socket_fd = fd;
	m_capture_thread_stop = false;
	if (pthread_create(&m_capture_thread, nullptr, &gEGLDC::captureServerThreadEntry, this) != 0) {
		eDebug("[gEGLDC] failed to start e2egl capture thread");
		close(fd);
		unlink(E2EGL_CAPTURE_SOCKET);
		m_capture_socket_fd = -1;
		return;
	}

	m_capture_thread_started = true;
	eDebug("[gEGLDC] e2egl OSD capture socket active: %s", E2EGL_CAPTURE_SOCKET);
}

void gEGLDC::stopCaptureServer() {
	m_capture_thread_stop = true;
	if (m_capture_thread_started) {
		pthread_join(m_capture_thread, nullptr);
		m_capture_thread_started = false;
	}
	if (m_capture_socket_fd >= 0) {
		close(m_capture_socket_fd);
		m_capture_socket_fd = -1;
	}
	unlink(E2EGL_CAPTURE_SOCKET);
}

void* gEGLDC::captureServerThreadEntry(void* arg) {
	static_cast<gEGLDC*>(arg)->captureServerThread();
	return nullptr;
}

void gEGLDC::captureServerThread() {
	while (!m_capture_thread_stop) {
		const int fd = m_capture_socket_fd;
		if (fd < 0)
			break;

		struct pollfd pfd;
		pfd.fd = fd;
		pfd.events = POLLIN;
		pfd.revents = 0;
		const int poll_result = poll(&pfd, 1, 100);
		if (poll_result < 0) {
			if (errno == EINTR)
				continue;
			break;
		}
		if (poll_result == 0 || !(pfd.revents & POLLIN))
			continue;
		if (m_capture_thread_stop)
			break;

		const int client_fd = accept(fd, nullptr, nullptr);
		if (client_fd < 0) {
			if (errno == EINTR)
				continue;
			if (!m_capture_thread_stop)
				eDebug("[gEGLDC] e2egl capture accept failed: %m");
			continue;
		}

		struct timeval timeout;
		timeout.tv_sec = 2;
		timeout.tv_usec = 0;
		setsockopt(client_fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
		if (!writeCaptureFrame(client_fd))
			eDebug("[gEGLDC] e2egl capture request failed");
		close(client_fd);
	}
}

eRect gEGLDC::clampToScreen(const eRect& rect) const {
	return rect & eRect(0, 0, m_width, m_height);
}

void gEGLDC::deleteFrameTextures() {
	if (!isInitialized()) {
		m_last_frame_texture = 0;
		m_animation_frame_texture = 0;
		m_last_frame_valid = false;
		m_frame_restore_pending = false;
		m_frame_texture_surface = false;
		m_frame_texture_scene_scaled = false;
		m_frame_texture_width = m_width;
		m_frame_texture_height = m_height;
		return;
	}

	GLuint textures[2];
	GLsizei count = 0;
	if (m_last_frame_texture)
		textures[count++] = m_last_frame_texture;
	if (m_animation_frame_texture)
		textures[count++] = m_animation_frame_texture;
	if (count)
		glDeleteTextures(count, textures);

	m_last_frame_texture = 0;
	m_animation_frame_texture = 0;
	m_last_frame_valid = false;
	m_frame_restore_pending = false;
	m_frame_texture_surface = false;
	m_frame_texture_scene_scaled = false;
	m_frame_texture_width = m_width;
	m_frame_texture_height = m_height;
}

bool gEGLDC::sceneFramebufferWanted() const {
#if (defined(HAVE_VUPLUS_EGL) || defined(HAVE_VUPLUS_MIPSEL_EGL) || defined(HAVE_NXPL_EGL) || defined(HAVE_V3DPLATFORM_EGL) || defined(HAVE_HISILICON_EGL) || defined(HAVE_DREAMBCM_EGL)) && !defined(DREAMNEXTGEN)
	if (e2eglForceDestroyedSwap())
		return true;
	return !m_preserved_swap;
#else
	return false;
#endif
}

bool gEGLDC::sceneFramebufferActive() const {
	return sceneFramebufferWanted() && m_scene_framebuffer && m_scene_frame_texture &&
		m_scene_frame_width == sceneFramebufferWidth() && m_scene_frame_height == sceneFramebufferHeight();
}

bool gEGLDC::sceneFramebufferUsesSurfaceScale() const {
	return m_max_texture_size > 0 &&
		(m_width > m_max_texture_size || m_height > m_max_texture_size) &&
		surfaceWidth() > 0 && surfaceHeight() > 0 &&
		surfaceWidth() <= m_max_texture_size && surfaceHeight() <= m_max_texture_size;
}

int gEGLDC::sceneFramebufferWidth() const {
	return sceneFramebufferUsesSurfaceScale() ? surfaceWidth() : m_width;
}

int gEGLDC::sceneFramebufferHeight() const {
	return sceneFramebufferUsesSurfaceScale() ? surfaceHeight() : m_height;
}

eRect gEGLDC::logicalToSceneRect(const eRect& rect) const {
	if (m_width <= 0 || m_height <= 0 || rect.empty())
		return eRect();

	const int scene_width = m_scene_frame_width > 0 ? m_scene_frame_width : sceneFramebufferWidth();
	const int scene_height = m_scene_frame_height > 0 ? m_scene_frame_height : sceneFramebufferHeight();
	const int sx0 = divFloorSigned((long long)rect.x() * scene_width, m_width);
	const int sy0 = divFloorSigned((long long)rect.y() * scene_height, m_height);
	const int sx1 = divCeilSigned((long long)(rect.x() + rect.width()) * scene_width, m_width);
	const int sy1 = divCeilSigned((long long)(rect.y() + rect.height()) * scene_height, m_height);
	return eRect(sx0, sy0, std::max(0, sx1 - sx0), std::max(0, sy1 - sy0));
}

bool gEGLDC::currentFramebufferIsScene() const {
	if (!sceneFramebufferActive())
		return false;

	GLint framebuffer = 0;
	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &framebuffer);
	return framebuffer == (GLint)m_scene_framebuffer || framebuffer == (GLint)m_scene_spare_framebuffer;
}

void gEGLDC::bindWindowFramebuffer() {
	glBindFramebuffer(GL_FRAMEBUFFER, 0);
	applyWindowViewport();
}

eRect gEGLDC::osdDestinationLogical() const {
	const int width = m_osd_width > 0 ? m_osd_width : m_width;
	const int height = m_osd_height > 0 ? m_osd_height : m_height;
	return eRect(m_osd_left, m_osd_top, std::max(1, width), std::max(1, height));
}

eRect gEGLDC::osdDestinationSurface() const {
	const eRect dst = osdDestinationLogical();
	const int sx0 = scaleSurfaceFloorX(dst.x());
	const int sy0 = scaleSurfaceFloorY(dst.y());
	const int sx1 = scaleSurfaceCeilX(dst.x() + dst.width());
	const int sy1 = scaleSurfaceCeilY(dst.y() + dst.height());
	return eRect(sx0, sy0, std::max(1, sx1 - sx0), std::max(1, sy1 - sy0));
}

eRect gEGLDC::logicalToSurfaceRect(const eRect& rect) const {
	if (m_width <= 0 || m_height <= 0 || rect.empty())
		return eRect();

	const eRect dst = osdDestinationSurface();
	const int sx0 = dst.x() + divFloorSigned((long long)rect.x() * dst.width(), m_width);
	const int sy0 = dst.y() + divFloorSigned((long long)rect.y() * dst.height(), m_height);
	const int sx1 = dst.x() + divCeilSigned((long long)(rect.x() + rect.width()) * dst.width(), m_width);
	const int sy1 = dst.y() + divCeilSigned((long long)(rect.y() + rect.height()) * dst.height(), m_height);
	return eRect(sx0, sy0, std::max(0, sx1 - sx0), std::max(0, sy1 - sy0));
}

void gEGLDC::applyWindowViewport() {
	const eRect dst = osdDestinationSurface();
	glViewport(dst.x(), surfaceHeight() - (dst.y() + dst.height()), dst.width(), dst.height());
}

bool gEGLDC::ensureSceneFramebufferObject(GLuint& texture, GLuint& framebuffer, bool& valid, int width, int height, const char* label) {
	if (width <= 0 || height <= 0)
		return false;

	GLint previous_framebuffer = 0;
	GLint previous_texture = 0;
	GLint previous_viewport[4] = {0, 0, 0, 0};
	GLboolean scissor_enabled = glIsEnabled(GL_SCISSOR_TEST);
	GLboolean blend_enabled = glIsEnabled(GL_BLEND);
	GLfloat previous_clear_color[4] = {0.0f, 0.0f, 0.0f, 0.0f};

	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glGetIntegerv(GL_TEXTURE_BINDING_2D, &previous_texture);
	glGetIntegerv(GL_VIEWPORT, previous_viewport);
	glGetFloatv(GL_COLOR_CLEAR_VALUE, previous_clear_color);

	while (glGetError() != GL_NO_ERROR) {
	}

	if ((texture && !framebuffer) || (!texture && framebuffer)) {
		if (framebuffer)
			glDeleteFramebuffers(1, &framebuffer);
		if (texture)
			glDeleteTextures(1, &texture);
		texture = 0;
		framebuffer = 0;
		valid = false;
	}

	if (texture && framebuffer)
		return true;

	GLuint new_texture = 0;
	GLuint new_framebuffer = 0;
	glGenTextures(1, &new_texture);
	glBindTexture(GL_TEXTURE_2D, new_texture);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);

	glGenFramebuffers(1, &new_framebuffer);
	glBindFramebuffer(GL_FRAMEBUFFER, new_framebuffer);
	glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, new_texture, 0);
	const GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
	const GLenum error = glGetError();

	if (status != GL_FRAMEBUFFER_COMPLETE || error != GL_NO_ERROR) {
		eDebug("[gEGLDC] %s framebuffer unavailable status=0x%x error=0x%x", label, status, error);
		glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
		glBindTexture(GL_TEXTURE_2D, previous_texture);
		if (new_framebuffer)
			glDeleteFramebuffers(1, &new_framebuffer);
		if (new_texture)
			glDeleteTextures(1, &new_texture);
		texture = 0;
		framebuffer = 0;
		valid = false;
		return false;
	}

	texture = new_texture;
	framebuffer = new_framebuffer;

	glViewport(0, 0, width, height);
	glDisable(GL_SCISSOR_TEST);
	glDisable(GL_BLEND);
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	valid = true;

	if (blend_enabled)
		glEnable(GL_BLEND);
	else
		glDisable(GL_BLEND);
	if (scissor_enabled)
		glEnable(GL_SCISSOR_TEST);
	else
		glDisable(GL_SCISSOR_TEST);
	glClearColor(previous_clear_color[0], previous_clear_color[1], previous_clear_color[2], previous_clear_color[3]);
	glViewport(previous_viewport[0], previous_viewport[1], previous_viewport[2], previous_viewport[3]);
	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
	glBindTexture(GL_TEXTURE_2D, previous_texture);

	static int scene_log_count = 0;
	if (scene_log_count < 4) {
		++scene_log_count;
		eDebug("[gEGLDC] %s framebuffer active %dx%d logical=%dx%d texture=%u framebuffer=%u",
			label, width, height, m_width, m_height, texture, framebuffer);
	}
	return true;
}

bool gEGLDC::ensureSceneFramebuffer() {
	if (!sceneFramebufferWanted() || m_width <= 0 || m_height <= 0) {
		deleteSceneFramebuffer();
		return false;
	}
	if (m_scene_framebuffer_unavailable)
		return false;

	const int target_width = sceneFramebufferWidth();
	const int target_height = sceneFramebufferHeight();
	if (target_width <= 0 || target_height <= 0)
		return false;

	if ((m_scene_frame_width && m_scene_frame_width != target_width) || (m_scene_frame_height && m_scene_frame_height != target_height))
		deleteSceneFramebuffer();

	if (!ensureSceneFramebufferObject(m_scene_frame_texture, m_scene_framebuffer, m_scene_frame_valid, target_width, target_height, "scene")) {
		m_scene_framebuffer_unavailable = true;
		return false;
	}

	m_scene_frame_width = target_width;
	m_scene_frame_height = target_height;
	return true;
}

bool gEGLDC::ensureSpareSceneFramebuffer() {
	if (!ensureSceneFramebuffer())
		return false;
	return ensureSceneFramebufferObject(m_scene_spare_frame_texture, m_scene_spare_framebuffer, m_scene_spare_frame_valid,
		m_scene_frame_width, m_scene_frame_height, "scene-spare");
}

void gEGLDC::deleteSceneFramebuffer() {
	if (!m_scene_framebuffer && !m_scene_frame_texture && !m_scene_spare_framebuffer && !m_scene_spare_frame_texture) {
		m_scene_frame_width = 0;
		m_scene_frame_height = 0;
		m_scene_frame_valid = false;
		m_scene_spare_frame_valid = false;
		m_scene_animation_old_texture = 0;
		m_scene_animation_old_valid = false;
		return;
	}

	if (isInitialized()) {
		GLint previous_framebuffer = 0;
		glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
		if (previous_framebuffer == (GLint)m_scene_framebuffer || previous_framebuffer == (GLint)m_scene_spare_framebuffer)
			glBindFramebuffer(GL_FRAMEBUFFER, 0);
		if (m_scene_framebuffer)
			glDeleteFramebuffers(1, &m_scene_framebuffer);
		if (m_scene_frame_texture)
			glDeleteTextures(1, &m_scene_frame_texture);
		if (m_scene_spare_framebuffer)
			glDeleteFramebuffers(1, &m_scene_spare_framebuffer);
		if (m_scene_spare_frame_texture)
			glDeleteTextures(1, &m_scene_spare_frame_texture);
	} else {
		m_scene_framebuffer = 0;
		m_scene_frame_texture = 0;
		m_scene_spare_framebuffer = 0;
		m_scene_spare_frame_texture = 0;
	}

	m_scene_framebuffer = 0;
	m_scene_frame_texture = 0;
	m_scene_spare_framebuffer = 0;
	m_scene_spare_frame_texture = 0;
	m_scene_frame_width = 0;
	m_scene_frame_height = 0;
	m_scene_frame_valid = false;
	m_scene_spare_frame_valid = false;
	m_scene_animation_old_texture = 0;
	m_scene_animation_old_valid = false;
}

bool gEGLDC::bindSceneFramebuffer() {
	if (!ensureSceneFramebuffer())
		return false;

	glBindFramebuffer(GL_FRAMEBUFFER, m_scene_framebuffer);
	glViewport(0, 0, m_scene_frame_width, m_scene_frame_height);
	return true;
}

void gEGLDC::clearSceneFramebuffer() {
	if (!bindSceneFramebuffer())
		return;

	glDisable(GL_BLEND);
	glDisable(GL_SCISSOR_TEST);
	glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
	glViewport(0, 0, m_scene_frame_width, m_scene_frame_height);
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	m_scene_frame_valid = true;
}

bool gEGLDC::presentSceneFramebuffer() {
	if (!sceneFramebufferActive())
		return false;

	bindWindowFramebuffer();
	glDisable(GL_SCISSOR_TEST);
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	if (m_scene_frame_valid) {
		const eRect full_frame(0, 0, m_width, m_height);
		drawCopiedFrameTexture(m_scene_frame_texture, full_frame, full_frame, 1.0f, false);
	}
	glDisable(GL_BLEND);
#ifdef HAVE_DREAMBCM_EGL
	// The old Broadcom driver can expose an unfinished render-to-texture frame.
	glFinish();
#endif
	return true;
}

bool gEGLDC::beginSceneFramebufferAnimation() {
	if (!sceneFramebufferActive() || m_scene_animation_old_valid || !m_scene_frame_valid)
		return false;

	flushTextBatch();
	if (!ensureSpareSceneFramebuffer())
		return false;

	const GLuint old_texture = m_scene_frame_texture;
	const eRect full_frame(0, 0, m_width, m_height);

	glBindFramebuffer(GL_FRAMEBUFFER, m_scene_spare_framebuffer);
	glViewport(0, 0, m_scene_frame_width, m_scene_frame_height);
	glDisable(GL_SCISSOR_TEST);
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	drawCopiedFrameTexture(old_texture, full_frame, full_frame, 1.0f, false);
	glDisable(GL_BLEND);
	m_scene_spare_frame_valid = true;

	std::swap(m_scene_frame_texture, m_scene_spare_frame_texture);
	std::swap(m_scene_framebuffer, m_scene_spare_framebuffer);
	std::swap(m_scene_frame_valid, m_scene_spare_frame_valid);

	m_scene_animation_old_texture = m_scene_spare_frame_texture;
	m_scene_animation_old_valid = m_scene_animation_old_texture != 0 && m_scene_spare_frame_valid;
	if (!m_scene_animation_old_valid)
		return false;

	static int scene_animation_log_count = 0;
	if (scene_animation_log_count < 4) {
		++scene_animation_log_count;
		eDebug("[gEGLDC] scene animation zero-copy old=%u new=%u", m_scene_animation_old_texture, m_scene_frame_texture);
	}
	bindSceneFramebuffer();
	return true;
}

void gEGLDC::finishSceneFramebufferAnimation() {
	m_scene_animation_old_texture = 0;
	m_scene_animation_old_valid = false;
	if (sceneFramebufferActive())
		bindSceneFramebuffer();
}

bool gEGLDC::swapWindowFramebuffer() {
	const unsigned long long swap_start_us = e2eglNowUs();
	if (!eglSwapBuffers(m_egl_display, m_egl_surface)) {
		eDebug("[gEGLDC] eglSwapBuffers failed. EGL error: 0x%x", eglGetError());
		return false;
	}

	m_frame_stats.swap_us += e2eglNowUs() - swap_start_us;
	if (m_flip_count < 8) {
		++m_flip_count;
		eDebug("[gEGLDC] swap #%d at %dx%d logical=%dx%d", m_flip_count, surfaceWidth(), surfaceHeight(), m_width, m_height);
	}
	return true;
}

bool gEGLDC::ensureFrameTexture(GLuint& texture) {
	const bool capture_surface = !sceneFramebufferActive() && currentFramebufferUsesSurface();
	const bool capture_scaled_scene = sceneFramebufferActive() && sceneFramebufferUsesSurfaceScale();
	const int capture_width = sceneFramebufferActive() ? m_scene_frame_width : (capture_surface ? surfaceWidth() : m_width);
	const int capture_height = sceneFramebufferActive() ? m_scene_frame_height : (capture_surface ? surfaceHeight() : m_height);
	if (capture_width <= 0 || capture_height <= 0)
		return false;

	if (m_frame_texture_width != capture_width || m_frame_texture_height != capture_height ||
		m_frame_texture_surface != capture_surface || m_frame_texture_scene_scaled != capture_scaled_scene)
		deleteFrameTextures();

	if (!texture) {
		glGenTextures(1, &texture);
		glBindTexture(GL_TEXTURE_2D, texture);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, capture_width, capture_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
		glBindTexture(GL_TEXTURE_2D, 0);
	}

	m_frame_texture_width = capture_width;
	m_frame_texture_height = capture_height;
	m_frame_texture_surface = capture_surface;
	m_frame_texture_scene_scaled = capture_scaled_scene;
	return texture != 0;
}

bool gEGLDC::copyCurrentFrameToTexture(GLuint& texture) {
	if (!ensureFrameTexture(texture))
		return false;

	GLint previous_framebuffer = 0;
	if (sceneFramebufferActive()) {
		glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
		glBindFramebuffer(GL_FRAMEBUFFER, m_scene_framebuffer);
	}

	while (glGetError() != GL_NO_ERROR) {
	}
	glBindTexture(GL_TEXTURE_2D, texture);
	glCopyTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 0, 0, m_frame_texture_width, m_frame_texture_height);
	glBindTexture(GL_TEXTURE_2D, 0);
	if (sceneFramebufferActive())
		glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
	static int frame_capture_log_count = 0;
	if (frame_capture_log_count < 4) {
		++frame_capture_log_count;
		eDebug("[gEGLDC] captured frame texture %dx%d logical=%dx%d", m_frame_texture_width, m_frame_texture_height, m_width, m_height);
	}
	return glGetError() == GL_NO_ERROR;
}

void gEGLDC::captureCurrentFrameAsLast() {
	flushTextBatch();
	const unsigned long long start_us = e2eglNowUs();
	m_last_frame_valid = copyCurrentFrameToTexture(m_last_frame_texture);
	m_frame_stats.capture_us += e2eglNowUs() - start_us;
	if (m_last_frame_valid)
		++m_frame_stats.frame_captures;
}

void gEGLDC::restoreFrameIfNeeded() {
	if (!m_frame_restore_pending)
		return;

	const unsigned long long start_us = e2eglNowUs();
	m_frame_restore_pending = false;
	if (sceneFramebufferActive())
		return;
	if (m_preserved_swap || !m_last_frame_valid || !m_last_frame_texture)
		return;

	const eRect full_frame(0, 0, m_width, m_height);
	static int restore_log_count = 0;
	if (restore_log_count < 4) {
		++restore_log_count;
		eDebug("[gEGLDC] restoring previous frame after non-preserved swap");
	}
	glDisable(GL_SCISSOR_TEST);
	drawCopiedFrameTexture(m_last_frame_texture, full_frame, full_frame, 1.0f, false);
	glDisable(GL_BLEND);
	m_frame_stats.restore_us += e2eglNowUs() - start_us;
	++m_frame_stats.frame_restores;
}

void gEGLDC::copiedTextureSize(GLuint texture, int& width, int& height) const {
	width = m_width;
	height = m_height;
	if (texture == m_last_frame_texture || texture == m_animation_frame_texture) {
		width = m_frame_texture_width;
		height = m_frame_texture_height;
		return;
	}
	if (texture == m_scene_frame_texture || texture == m_scene_spare_frame_texture || texture == m_scene_animation_old_texture) {
		width = m_scene_frame_width ? m_scene_frame_width : m_width;
		height = m_scene_frame_height ? m_scene_frame_height : m_height;
	}
}

void gEGLDC::drawCopiedFrameTexture(GLuint texture, const eRect& dest, const eRect& source, float alpha, bool blend) {
	e2eglScopedTimer timer(m_frame_stats.copy_us);
	if (!texture || dest.empty() || source.empty())
		return;

	int texture_width = m_width;
	int texture_height = m_height;
	copiedTextureSize(texture, texture_width, texture_height);
	if (texture_width <= 0 || texture_height <= 0)
		return;

	const bool texture_is_frame_capture = texture == m_last_frame_texture || texture == m_animation_frame_texture;
	const bool texture_is_surface = texture_is_frame_capture && m_frame_texture_surface;
	const bool texture_is_scene = texture == m_scene_frame_texture || texture == m_scene_spare_frame_texture ||
		texture == m_scene_animation_old_texture || (texture_is_frame_capture && m_frame_texture_scene_scaled);
	const eRect texture_source = texture_is_scene ? logicalToSceneRect(source) : (texture_is_surface ? logicalToSurfaceRect(source) : source);
	const int source_left = texture_source.left();
	const int source_right = texture_source.right();
	const int source_top = texture_source.top();
	const int source_bottom = texture_source.bottom();

	const float u0 = (float)source_left / (float)texture_width;
	const float u1 = (float)source_right / (float)texture_width;
	const float v0 = 1.0f - ((float)source_top / (float)texture_height);
	const float v1 = 1.0f - ((float)source_bottom / (float)texture_height);

	if (blend) {
		glEnable(GL_BLEND);
		glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
	} else {
		glDisable(GL_BLEND);
	}

	m_texture_shader.drawTexture(dest.x(), dest.y(), dest.width(), dest.height(), texture, clampFloat(alpha, 0.0f, 1.0f), 0.0f, 0, u0, v0, u1, v1, false);
	++m_frame_stats.frame_copy_draws;
	m_frame_stats.frame_copy_pixels += rectPixels(dest);
}

void gEGLDC::drawStripedWindowTexture(GLuint texture, const eRect& source, float visible_progress) {
	const int strips = 8;
	const int strip_width = std::max(1, source.width() / strips);

	for (int i = 0; i < strips; ++i) {
		const int left = source.left() + i * strip_width;
		const int right = (i == strips - 1) ? source.right() : std::min(source.right(), left + strip_width);
		if (left >= right)
			continue;

		const float local = clampFloat((visible_progress * (strips + 2) - i) / 2.0f, 0.0f, 1.0f);
		if (local <= 0.0f)
			continue;

		eRect strip_source(left, source.top(), right - left, source.height());
		eRect strip_dest = strip_source;
		const int offset = (int)((1.0f - local) * source.height() * 0.18f);
		strip_dest.moveBy(0, (i & 1) ? offset : -offset);
		drawCopiedFrameTexture(texture, strip_dest, strip_source, local, true);
	}
}

eRect gEGLDC::stripedWindowDamageRect(const eRect& source) const {
	const int overscan = std::max(1, (int)((float)source.height() * 0.18f) + 2);
	return clampToScreen(eRect(source.left(), source.top() - overscan, source.width(), source.height() + overscan * 2));
}

eRect gEGLDC::animatedWindowDestRect(const eRect& source, float visible_progress, bool show, float* alpha_out) const {
	(void)show;

	float x = (float)source.x();
	float y = (float)source.y();
	float w = (float)source.width();
	float h = (float)source.height();
	float alpha = visible_progress;
	float scale_x = 1.0f;
	float scale_y = 1.0f;
	float anchor_x = 0.5f;
	float anchor_y = 0.5f;
	const float hidden = 1.0f - visible_progress;
	const float screen_w = std::max(1.0f, (float)m_width);
	const float screen_h = std::max(1.0f, (float)m_height);
	const float width_ratio = w / screen_w;
	const float height_ratio = h / screen_h;
	const bool small_dialog = width_ratio < 0.68f && height_ratio < 0.68f;
	const bool large_window = width_ratio > 0.82f && height_ratio > 0.72f;
	const bool bottom_panel = source.bottom() > (int)(screen_h * 0.78f) && height_ratio < 0.42f;
	const bool top_panel = source.top() < (int)(screen_h * 0.18f) && height_ratio < 0.34f;
	const bool left_panel = source.left() < (int)(screen_w * 0.12f) && width_ratio < 0.76f && height_ratio > 0.42f;
	const bool right_panel = source.right() > (int)(screen_w * 0.88f) && width_ratio < 0.76f && height_ratio > 0.42f;
	const int animation = effectiveWindowAnimationForRect(source, m_width, m_height);

	switch (animation) {
	case 2: // simple zoom
		scale_x = scale_y = 0.86f + 0.14f * visible_progress;
		break;
	case 3: // grow drop
		y -= hidden * h * 0.30f;
		scale_y = 0.68f + 0.32f * visible_progress;
		anchor_y = 0.0f;
		break;
	case 4: // grow from left
		x -= hidden * w * 0.20f;
		scale_x = 0.68f + 0.32f * visible_progress;
		anchor_x = 0.0f;
		break;
	case 5: // extrude from left
		scale_x = 0.08f + 0.92f * visible_progress;
		anchor_x = 0.0f;
		alpha = 1.0f;
		break;
	case 6: // popup
		scale_x = scale_y = 0.72f + 0.28f * visible_progress;
		break;
	case 7: // slide drop
		y -= hidden * h;
		alpha = 1.0f;
		break;
	case 8: // slide from left
		x -= hidden * w;
		alpha = 1.0f;
		break;
	case 9: // slide left to right
		x = -w + visible_progress * ((float)source.x() + w);
		alpha = 1.0f;
		break;
	case 10: // slide right to left
		x = (float)m_width - visible_progress * ((float)m_width - (float)source.x());
		alpha = 1.0f;
		break;
	case 11: // slide top to bottom
		y = -h + visible_progress * ((float)source.y() + h);
		alpha = 1.0f;
		break;
	case 12: // zoom from left
		scale_x = scale_y = 0.74f + 0.26f * visible_progress;
		anchor_x = 0.0f;
		break;
	case 13: // zoom from right
		scale_x = scale_y = 0.74f + 0.26f * visible_progress;
		anchor_x = 1.0f;
		break;
	case 15: // basis animation
	{
		if (bottom_panel) {
			y += hidden * std::min(h, screen_h * 0.16f);
		} else if (top_panel) {
			y -= hidden * std::min(h, screen_h * 0.12f);
		} else if (left_panel && !large_window) {
			x -= hidden * std::min(w, screen_w * 0.14f);
		} else if (right_panel && !large_window) {
			x += hidden * std::min(w, screen_w * 0.14f);
		} else if (small_dialog) {
			scale_x = scale_y = 0.88f + 0.12f * visible_progress;
			y += hidden * screen_h * 0.015f;
		} else {
			scale_x = scale_y = 0.98f + 0.02f * visible_progress;
		}
		break;
	}
	case 16: // modern adaptive
		if (bottom_panel) {
			y += hidden * std::min(h, screen_h * 0.24f);
			alpha = 0.18f + 0.82f * visible_progress;
		} else if (top_panel) {
			y -= hidden * std::min(h, screen_h * 0.18f);
			alpha = 0.18f + 0.82f * visible_progress;
		} else if (left_panel && !large_window) {
			x -= hidden * std::min(w, screen_w * 0.22f);
			alpha = 0.20f + 0.80f * visible_progress;
		} else if (right_panel && !large_window) {
			x += hidden * std::min(w, screen_w * 0.22f);
			alpha = 0.20f + 0.80f * visible_progress;
		} else if (small_dialog) {
			scale_x = scale_y = 0.82f + 0.18f * visible_progress;
			y += hidden * screen_h * 0.025f;
			alpha = 0.18f + 0.82f * visible_progress;
		} else if (large_window) {
			scale_x = scale_y = 0.985f + 0.015f * visible_progress;
			alpha = 0.35f + 0.65f * visible_progress;
		} else {
			scale_x = scale_y = 0.94f + 0.06f * visible_progress;
			alpha = 0.28f + 0.72f * visible_progress;
		}
		break;
	case 17: // fade in / fade out
		alpha = clampFloat(visible_progress * 1.35f, 0.0f, 1.0f);
		break;
	case 18: // dialog pop
		scale_x = scale_y = 0.78f + 0.22f * visible_progress;
		y += hidden * std::min(h * 0.12f, screen_h * 0.035f);
		alpha = 0.16f + 0.84f * visible_progress;
		break;
	case 19: // toast slide
		if (source.top() < (int)(screen_h * 0.5f))
			y -= hidden * std::min(h, screen_h * 0.20f);
		else
			y += hidden * std::min(h, screen_h * 0.20f);
		alpha = 0.12f + 0.88f * visible_progress;
		break;
	case 20: // side sheet
		if (source.x() + source.width() / 2 < (int)(screen_w * 0.5f)) {
			x -= hidden * std::min(w, screen_w * 0.28f);
			anchor_x = 0.0f;
		} else {
			x += hidden * std::min(w, screen_w * 0.28f);
			anchor_x = 1.0f;
		}
		alpha = 0.18f + 0.82f * visible_progress;
		break;
	case 21: // zoom and fade
		scale_x = scale_y = 0.72f + 0.28f * visible_progress;
		alpha = 0.12f + 0.88f * visible_progress;
		break;
	case 1: // simple fade
	default:
		break;
	}

	if (scale_x != 1.0f) {
		const float new_w = w * scale_x;
		x += (w - new_w) * anchor_x;
		w = new_w;
	}
	if (scale_y != 1.0f) {
		const float new_h = h * scale_y;
		y += (h - new_h) * anchor_y;
		h = new_h;
	}

	if (alpha_out)
		*alpha_out = alpha;
	return eRect((int)x, (int)y, std::max(1, (int)w), std::max(1, (int)h));
}

void gEGLDC::drawAnimatedWindowTexture(GLuint texture, const eRect& source, float visible_progress, bool show) {
	if (effectiveWindowAnimationForRect(source, m_width, m_height) == 14) {
		drawStripedWindowTexture(texture, source, visible_progress);
		return;
	}

	float alpha = visible_progress;
	eRect dest = animatedWindowDestRect(source, visible_progress, show, &alpha);
	drawCopiedFrameTexture(texture, dest, source, alpha, true);
}

void gEGLDC::executeWindowAnimationOpcode(const gOpcode* op, bool show) {
	if (op->parm.setShowHideInfo) {
		eRect rect(op->parm.setShowHideInfo->point, op->parm.setShowHideInfo->size);
		rect = clampToScreen(rect);
		if (s_egl_animation_current > 0 && effectiveWindowAnimationForRect(rect, m_width, m_height) > 0 && !rect.empty()) {
			const bool scene_animation_ready = beginSceneFramebufferAnimation();
			if (!scene_animation_ready)
				captureCurrentFrameAsLast();
			if (scene_animation_ready || m_last_frame_valid) {
				m_pending_listbox_animation.active = false;
				m_pending_listbox_animation.selection_pixmap = nullptr;
				m_pending_window_animation.active = true;
				m_pending_window_animation.show = show;
				m_pending_window_animation.rect = rect;
			}
		}
		delete op->parm.setShowHideInfo;
	}
}

bool gEGLDC::runPendingWindowAnimation() {
	if (!m_pending_window_animation.active)
		return false;

	m_pending_window_animation.active = false;

	const bool use_scene_frames = m_scene_animation_old_valid && sceneFramebufferActive();
	if (s_egl_animation_current <= 0 || (!m_last_frame_valid && !use_scene_frames)) {
		if (use_scene_frames)
			finishSceneFramebufferAnimation();
		return false;
	}

	const eRect source = clampToScreen(m_pending_window_animation.rect);
	if (source.empty()) {
		if (use_scene_frames)
			finishSceneFramebufferAnimation();
		return false;
	}
	const int animation = effectiveWindowAnimationForRect(source, m_width, m_height);
	if (animation <= 0) {
		if (use_scene_frames)
			finishSceneFramebufferAnimation();
		return false;
	}

	GLuint old_frame = 0;
	GLuint new_frame = 0;
	if (use_scene_frames) {
		old_frame = m_scene_animation_old_texture;
		new_frame = m_scene_frame_texture;
	} else {
		const unsigned long long animation_capture_start_us = e2eglNowUs();
		if (!copyCurrentFrameToTexture(m_animation_frame_texture)) {
			const unsigned long long animation_capture_us = e2eglNowUs() - animation_capture_start_us;
			m_frame_stats.capture_us += animation_capture_us;
			m_frame_stats.draw_us += animation_capture_us;
			return false;
		}
		const unsigned long long animation_capture_us = e2eglNowUs() - animation_capture_start_us;
		m_frame_stats.capture_us += animation_capture_us;
		m_frame_stats.draw_us += animation_capture_us;
		old_frame = m_last_frame_texture;
		new_frame = m_animation_frame_texture;
	}

	if (!old_frame || !new_frame) {
		if (use_scene_frames)
			finishSceneFramebufferAnimation();
		return false;
	}

	const unsigned long long animation_start_us = e2eglNowUs();
	unsigned long long source_sync_us = 0;
#ifdef HAVE_DREAMBCM_EGL
	if (use_scene_frames) {
		const unsigned long long sync_start_us = e2eglNowUs();
		// DreamBCM must finish both render-to-texture scenes before they are sampled by the animation.
		glFinish();
		source_sync_us = e2eglNowUs() - sync_start_us;
	}
#endif

	const bool show = m_pending_window_animation.show;
	const eRect full_frame(0, 0, m_width, m_height);
	const int duration_ms = windowAnimationDurationMs(source, m_width, m_height);
	const int frames = clampInt(duration_ms / 16, 4, 30);
	const bool damage_only = !use_scene_frames && m_preserved_swap && e2eglAnimationDamageEnabled();
	eRect previous_damage = source;
	if (e2eglTraceGlEnabled())
		eDebug("[e2egl:animation] start type=%d show=%d rect=%d,%d %dx%d duration_ms=%d frames=%d scene=%d source_sync_us=%llu",
			animation, show ? 1 : 0, source.x(), source.y(), source.width(), source.height(), duration_ms, frames, use_scene_frames ? 1 : 0, source_sync_us);

	for (int frame = 0; frame < frames; ++frame) {
		const unsigned long long animation_draw_start_us = e2eglNowUs();
		const float t = frames <= 1 ? 1.0f : (float)frame / (float)(frames - 1);
		const float progress = easeOut(t);
		const float visible_progress = show ? progress : (1.0f - progress);

		if (use_scene_frames)
			bindWindowFramebuffer();
		glDisable(GL_SCISSOR_TEST);
		if (damage_only) {
			eRect damage = effectiveWindowAnimationForRect(source, m_width, m_height) == 14 ? stripedWindowDamageRect(source) : animatedWindowDestRect(source, visible_progress, show);
			damage = clampToScreen((damage | source) | previous_damage);
			if (!damage.empty()) {
				drawCopiedFrameTexture(show ? old_frame : new_frame, damage, damage, 1.0f, false);
				drawAnimatedWindowTexture(show ? new_frame : old_frame, source, visible_progress, show);
			}
			previous_damage = damage;
		} else {
			{
				e2eglScopedTimer timer(m_frame_stats.clear_us);
				glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
				glClear(GL_COLOR_BUFFER_BIT);
			}
			++m_frame_stats.clear_ops;
			++m_frame_stats.clear_rects;
			m_frame_stats.clear_pixels += rectPixels(full_frame);
			if (show) {
				drawCopiedFrameTexture(old_frame, full_frame, full_frame, 1.0f, false);
				drawAnimatedWindowTexture(new_frame, source, visible_progress, true);
			} else {
				drawCopiedFrameTexture(new_frame, full_frame, full_frame, 1.0f, false);
				drawAnimatedWindowTexture(old_frame, source, visible_progress, false);
			}
		}

		glDisable(GL_BLEND);
		m_frame_stats.draw_us += e2eglNowUs() - animation_draw_start_us;
		if (use_scene_frames) {
			if (swapWindowFramebuffer())
				logAndResetFrameStats();
		} else {
			flip();
		}
		if (frame + 1 < frames)
			usleep(1000 * std::max(1, duration_ms / frames));
	}

	const unsigned long long animation_final_draw_start_us = e2eglNowUs();
	if (use_scene_frames) {
		finishSceneFramebufferAnimation();
		m_frame_stats.draw_us += e2eglNowUs() - animation_final_draw_start_us;
		flip();
		if (e2eglTraceGlEnabled())
			eDebug("[e2egl:animation] end type=%d show=%d elapsed_us=%llu", animation, show ? 1 : 0, e2eglNowUs() - animation_start_us);
		return true;
	}

	glDisable(GL_SCISSOR_TEST);
	if (damage_only) {
		eRect final_damage = clampToScreen(previous_damage | source);
		drawCopiedFrameTexture(new_frame, final_damage, final_damage, 1.0f, false);
	} else {
		{
			e2eglScopedTimer timer(m_frame_stats.clear_us);
			glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
			glClear(GL_COLOR_BUFFER_BIT);
		}
		++m_frame_stats.clear_ops;
		++m_frame_stats.clear_rects;
		m_frame_stats.clear_pixels += rectPixels(full_frame);
		drawCopiedFrameTexture(new_frame, full_frame, full_frame, 1.0f, false);
	}
	glDisable(GL_BLEND);

	std::swap(m_last_frame_texture, m_animation_frame_texture);
	m_last_frame_valid = true;
	m_frame_stats.draw_us += e2eglNowUs() - animation_final_draw_start_us;
	flip();
	if (e2eglTraceGlEnabled())
		eDebug("[e2egl:animation] end type=%d show=%d elapsed_us=%llu", animation, show ? 1 : 0, e2eglNowUs() - animation_start_us);
	return true;
}

void gEGLDC::executeListboxAnimationOpcode(const gOpcode* op) {
	const gOpcode::para::plistboxAnimation* info = op->parm.listboxAnimation;
	if (!info)
		return;

	if (s_egl_animation_listbox && !m_pending_window_animation.active && !m_scene_animation_old_valid) {
		const eRect from = clampToScreen(info->from);
		const eRect to = clampToScreen(info->to);
		if (!from.empty() && !to.empty() && from.size() == to.size() && from.topLeft() != to.topLeft()) {
			const bool scene_animation_ready = beginSceneFramebufferAnimation();
			if (!scene_animation_ready)
				captureCurrentFrameAsLast();
			if (scene_animation_ready || m_last_frame_valid) {
				m_pending_listbox_animation.active = true;
				m_pending_listbox_animation.from = from;
				m_pending_listbox_animation.to = to;
				m_pending_listbox_animation.background_color = info->backgroundColor;
				m_pending_listbox_animation.gradient_colors = info->gradientColors;
				m_pending_listbox_animation.gradient_orientation = info->gradientOrientation;
				m_pending_listbox_animation.gradient_alpha_blend = info->gradientAlphaBlend;
				m_pending_listbox_animation.radius = info->radius;
				m_pending_listbox_animation.radius_edges = info->radiusEdges;
				m_pending_listbox_animation.selection_pixmap = info->selectionPixmap;
			}
		}
	}

	if (info->selectionPixmap)
		info->selectionPixmap->Release();
	delete info;
}

void gEGLDC::drawListboxSelection(const eRect& area, const PendingListboxAnimation& animation) {
	if (area.empty())
		return;

	// Keep the moving focus slightly translucent so the fixed row text remains
	// readable while the bar passes underneath it.
	constexpr float animation_alpha = 0.82f;
	glEnable(GL_BLEND);
	glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);

	if (animation.selection_pixmap) {
		GLuint texture = m_texture_manager.getTexture(animation.selection_pixmap);
		if (texture) {
			const eSize pixmap_size = animation.selection_pixmap->size();
			const int width = std::min(area.width(), pixmap_size.width());
			const int height = std::min(area.height(), pixmap_size.height());
			const eRect dest(area.x() + (area.width() - width) / 2, area.y() + (area.height() - height) / 2, width, height);
			setTextureFiltering(texture, false);
			m_texture_shader.drawTexture(dest.x(), dest.y(), dest.width(), dest.height(), texture, animation_alpha,
				0.0f, 0, 0.0f, 0.0f, (float)width / (float)pixmap_size.width(), (float)height / (float)pixmap_size.height(), false);
		}
	} else {
		gRGB background = animation.background_color;
		std::vector<gRGB> gradient = animation.gradient_colors;
		const unsigned char min_transparency = (unsigned char)((1.0f - animation_alpha) * 255.0f);
		background.a = std::max(background.a, min_transparency);
		for (gRGB& color : gradient)
			color.a = std::max(color.a, min_transparency);
		m_advanced_shader.drawAdvancedRect(area.x(), area.y(), area.width(), area.height(), animation.radius,
			animation.radius_edges, gradient, animation.gradient_orientation, true, 0,
			colorAlpha(background), background);
	}

	glDisable(GL_BLEND);
}

bool gEGLDC::runPendingListboxAnimation() {
	if (!m_pending_listbox_animation.active)
		return false;

	const PendingListboxAnimation animation = m_pending_listbox_animation;
	m_pending_listbox_animation.active = false;
	m_pending_listbox_animation.selection_pixmap = nullptr;
	const bool use_scene_frames = m_scene_animation_old_valid && sceneFramebufferActive();
	if (!s_egl_animation_listbox || (!m_last_frame_valid && !use_scene_frames)) {
		if (use_scene_frames)
			finishSceneFramebufferAnimation();
		return false;
	}

	const eRect from = clampToScreen(animation.from);
	const eRect to = clampToScreen(animation.to);
	if (from.empty() || to.empty() || from.size() != to.size() || from.topLeft() == to.topLeft()) {
		if (use_scene_frames)
			finishSceneFramebufferAnimation();
		return false;
	}

	GLuint old_frame = 0;
	GLuint new_frame = 0;
	if (use_scene_frames) {
		old_frame = m_scene_animation_old_texture;
		new_frame = m_scene_frame_texture;
	} else {
		const unsigned long long capture_start_us = e2eglNowUs();
		if (!copyCurrentFrameToTexture(m_animation_frame_texture)) {
			m_frame_stats.capture_us += e2eglNowUs() - capture_start_us;
			return false;
		}
		m_frame_stats.capture_us += e2eglNowUs() - capture_start_us;
		++m_frame_stats.frame_captures;
		old_frame = m_last_frame_texture;
		new_frame = m_animation_frame_texture;
	}
	if (!old_frame || !new_frame) {
		if (use_scene_frames)
			finishSceneFramebufferAnimation();
		return false;
	}

#ifdef HAVE_DREAMBCM_EGL
	if (use_scene_frames)
		glFinish();
#endif

	const unsigned long long animation_start_us = e2eglNowUs();
	const eRect full_frame(0, 0, m_width, m_height);
	const int duration_ms = clampInt(s_egl_animation_speed * 7, 90, 210);
	const int frames = clampInt((duration_ms + 15) / 16 + 1, 7, 15);
	if (e2eglTraceGlEnabled())
		eDebug("[e2egl:listbox] start from=%d,%d %dx%d to=%d,%d duration_ms=%d frames=%d scene=%d",
			from.x(), from.y(), from.width(), from.height(), to.x(), to.y(), duration_ms, frames, use_scene_frames ? 1 : 0);

	for (int frame = 0; frame < frames; ++frame) {
		const unsigned long long draw_start_us = e2eglNowUs();
		const float t = frames <= 1 ? 1.0f : (float)frame / (float)(frames - 1);
		const float progress = easeInOut(t);
		const int x = from.x() + (int)((to.x() - from.x()) * progress);
		const int y = from.y() + (int)((to.y() - from.y()) * progress);
		const eRect moving(x, y, from.width(), from.height());

		if (use_scene_frames)
			bindWindowFramebuffer();
		glDisable(GL_SCISSOR_TEST);
		glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
		glClear(GL_COLOR_BUFFER_BIT);
		++m_frame_stats.clear_ops;
		++m_frame_stats.clear_rects;
		m_frame_stats.clear_pixels += rectPixels(full_frame);
		drawCopiedFrameTexture(new_frame, full_frame, full_frame, 1.0f, false);
		// The new frame already contains the old row unselected. Restore the
		// destination from the old frame as well, then animate only the focus bar.
		drawCopiedFrameTexture(old_frame, to, to, 1.0f, false);
		drawListboxSelection(moving, animation);
		glDisable(GL_BLEND);
		m_frame_stats.draw_us += e2eglNowUs() - draw_start_us;

		if (use_scene_frames) {
			if (swapWindowFramebuffer())
				logAndResetFrameStats();
		} else
			flip();
		if (frame + 1 < frames) {
			const unsigned long long target_us = animation_start_us +
				(unsigned long long)(frame + 1) * (unsigned long long)duration_ms * 1000ULL / (unsigned long long)(frames - 1);
			const unsigned long long now_us = e2eglNowUs();
			if (target_us > now_us)
				usleep((useconds_t)(target_us - now_us));
		}
	}

	const unsigned long long final_draw_start_us = e2eglNowUs();
	if (use_scene_frames) {
		finishSceneFramebufferAnimation();
		m_frame_stats.draw_us += e2eglNowUs() - final_draw_start_us;
		flip();
	} else {
		glDisable(GL_SCISSOR_TEST);
		glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
		glClear(GL_COLOR_BUFFER_BIT);
		drawCopiedFrameTexture(new_frame, full_frame, full_frame, 1.0f, false);
		glDisable(GL_BLEND);
		std::swap(m_last_frame_texture, m_animation_frame_texture);
		m_last_frame_valid = true;
		m_frame_stats.draw_us += e2eglNowUs() - final_draw_start_us;
		flip();
	}

	if (e2eglTraceGlEnabled())
		eDebug("[e2egl:listbox] end elapsed_us=%llu", e2eglNowUs() - animation_start_us);
	return true;
}

eRect gEGLDC::currentSpinnerRect() const {
	return m_width >= 1920 ? m_spinner_pos_FHD : m_spinner_pos_HD;
}

gPixmap* gEGLDC::currentSpinnerBackground() const {
	return m_width >= 1920 ? m_spinner_saved_FHD : m_spinner_saved_HD;
}

void gEGLDC::invalidateSpinnerBackground(bool clear_pending) {
	m_spinner_background_valid = false;
	m_spinner_background_width = 0;
	m_spinner_background_height = 0;
	m_spinner_background_clear = false;
	if (clear_pending)
		m_spinner_clear_pending = true;
}

void gEGLDC::clearSpinnerRect(const eRect& rect) {
	const eRect area = clampToScreen(rect);
	if (area.empty())
		return;

	flushFillBatchIfOverlaps(area);
	glDisable(GL_BLEND);
	glEnable(GL_SCISSOR_TEST);
	setGlScissor(area);
	glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	glClear(GL_COLOR_BUFFER_BIT);
	glDisable(GL_SCISSOR_TEST);
}

bool gEGLDC::clearSpinnerBackgroundPixmap(gPixmap* background) {
	if (!background || !background->surface || !background->surface->data || background->surface->bpp != 32)
		return false;

	gUnmanagedSurface* surface = background->surface;
	m_texture_manager.prepareSurface(surface);
	const int width = std::min(std::max(0, surface->x), background->size().width());
	const int height = std::min(std::max(0, surface->y), background->size().height());
	if (width <= 0 || height <= 0 || surface->stride < width * 4)
		return false;

	if (surface->gl_texture_id) {
		m_texture_manager.queueForDeletion(surface->gl_texture_id);
		surface->gl_texture_id = 0;
	}
	if (surface->gl_framebuffer_id) {
		m_texture_manager.queueFramebufferForDeletion(surface->gl_framebuffer_id);
		surface->gl_framebuffer_id = 0;
	}

	for (int y = 0; y < height; ++y)
		memset((uint8_t*)surface->data + y * surface->stride, 0, width * 4);
	surface->cpu_content_valid = true;
	surface->gl_content_valid = false;
	return true;
}

bool gEGLDC::captureSpinnerBackground() {
	gPixmap* background = currentSpinnerBackground();
	const eRect rect = clampToScreen(currentSpinnerRect());
	if (!background || !background->surface || rect.empty())
		return false;

	bool ok = false;
	const bool clear_background = m_spinner_clear_pending;
	bool cleared_background = false;
	if (clear_background) {
		ok = clearSpinnerBackgroundPixmap(background);
		cleared_background = ok;
	}
	if (!ok) {
		ok = readFramebufferRegion(rect, background);
		cleared_background = false;
	}
	m_spinner_clear_pending = false;
	m_spinner_background_valid = ok;
	m_spinner_background_width = ok ? m_width : 0;
	m_spinner_background_height = ok ? m_height : 0;
	m_spinner_background_clear = ok && cleared_background;
	return ok;
}

void gEGLDC::enableSpinner() {
	flushTextBatch();
	captureSpinnerBackground();
	incrementSpinner();
}

void gEGLDC::disableSpinner() {
	flushTextBatch();
	const eRect rect = currentSpinnerRect();
	if (m_spinner_clear_pending) {
		clearSpinnerRect(rect);
		m_spinner_clear_pending = false;
	} else if (m_spinner_background_valid && m_spinner_background_width == m_width && m_spinner_background_height == m_height) {
		if (m_spinner_background_clear)
			clearSpinnerRect(rect);
		else
			drawPixmap(currentSpinnerBackground(), rect, 0);
	}
	invalidateSpinnerBackground();
}

void gEGLDC::incrementSpinner() {
	flushTextBatch();
	if (!m_spinner_pic || !m_spinner_num)
		return;

	if (!m_spinner_background_valid || m_spinner_background_width != m_width || m_spinner_background_height != m_height)
		captureSpinnerBackground();

	const eRect rect = currentSpinnerRect();
	if (m_spinner_background_valid) {
		if (m_spinner_background_clear)
			clearSpinnerRect(rect);
		else
			drawPixmap(currentSpinnerBackground(), rect, 0);
	}
	if (m_spinner_pic[m_spinner_i])
		drawPixmap(m_spinner_pic[m_spinner_i], rect, gPixmap::blitAlphaBlend);

	m_spinner_i++;
	m_spinner_i %= m_spinner_num;
}

void gEGLDC::renderGlyph(const ePoint& pos, gPixmap* glyph_mask, const gRGB& color) {
	if (!glyph_mask || !glyph_mask->surface || glyph_mask->surface->bpp != 8)
		return;

	const eRect glyph_bounds(pos.x(), pos.y(), glyph_mask->size().width(), glyph_mask->size().height());
	const eRect screen_bounds(0, 0, m_width, m_height);
	if (m_current_clip.empty() || !glyph_bounds.intersects(m_current_clip.extends) || !glyph_bounds.intersects(screen_bounds))
		return;

	glyph_uv uv;
	glyph_key_t key = hashGlyphMask(glyph_mask);

	if (!m_font_atlas.getGlyph(key, uv)) {
		int w = glyph_mask->size().width();
		int h = glyph_mask->size().height();
		int pitch = glyph_mask->surface->stride;
		uint8_t* data = (uint8_t*)glyph_mask->surface->data;
		if (!m_font_atlas.addGlyph(key, w, h, pitch, data, uv, false)) {
			flushTextBatchForReason(textFlushAtlas);
			if (!m_font_atlas.addGlyph(key, w, h, pitch, data, uv, true))
				return;
		}
	}

	float r = colorComponent(color.r);
	float g = colorComponent(color.g);
	float b = colorComponent(color.b);
	float a = colorAlpha(color);

	const float u_span = uv.u1 - uv.u0;
	const float v_span = uv.v1 - uv.v0;
	unsigned int clipped_quads = 0;

	for (unsigned int i = 0; i < m_current_clip.rects.size(); ++i) {
		eRect clipped = glyph_bounds & m_current_clip.rects[i] & screen_bounds;
		if (clipped.empty())
			continue;

		const float x0 = clipped.left();
		const float y0 = clipped.top();
		const float x1 = clipped.right();
		const float y1 = clipped.bottom();
		const float u0 = uv.u0 + ((float)(clipped.left() - glyph_bounds.left()) / (float)uv.width) * u_span;
		const float v0 = uv.v0 + ((float)(clipped.top() - glyph_bounds.top()) / (float)uv.height) * v_span;
		const float u1 = uv.u0 + ((float)(clipped.right() - glyph_bounds.left()) / (float)uv.width) * u_span;
		const float v1 = uv.v0 + ((float)(clipped.bottom() - glyph_bounds.top()) / (float)uv.height) * v_span;

		float vertices[48] = {x0, y0, u0, v0, r, g, b, a, x0, y1, u0, v1, r, g, b, a, x1, y0, u1, v0, r, g, b, a,
							  x1, y0, u1, v0, r, g, b, a, x0, y1, u0, v1, r, g, b, a, x1, y1, u1, v1, r, g, b, a};

		m_text_batch_buffer.insert(m_text_batch_buffer.end(), vertices, vertices + 48);
		addTextBatchRect(clipped);
		if (m_text_batch_bounds_valid)
			m_text_batch_bounds |= clipped;
		else {
			m_text_batch_bounds = clipped;
			m_text_batch_bounds_valid = true;
		}
		++clipped_quads;
		if (m_text_batch_buffer.size() >= MAX_BATCH_GLYPHS * 48)
			flushTextBatchForReason(textFlushLimit);
	}

	if (clipped_quads) {
		++m_frame_stats.glyphs;
		m_frame_stats.text_draw_rects += clipped_quads;
	}
}

void gEGLDC::flushTextBatch() {
	flushFillBatch();
	if (m_text_batch_buffer.empty())
		return;
	e2eglScopedTimer timer(m_frame_stats.text_us);
	++m_frame_stats.text_batches;

	glEnable(GL_BLEND);
	glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);

	m_text_shader.bind();

	// Bind the atlas pixmap
	gPixmap* atlas_pix = m_font_atlas.getPixmap();
	const bool atlas_texture_valid = atlas_pix && atlas_pix->surface && atlas_pix->surface->gl_texture_id && atlas_pix->surface->gl_content_valid;
	GLuint tex_id = m_texture_manager.getTexture(atlas_pix);
	if (!tex_id) {
		eDebug("[gEGLDC] failed to upload font atlas texture");
		m_text_batch_buffer.clear();
		m_text_batch_rects.clear();
		m_text_batch_bounds_valid = false;
		glDisable(GL_BLEND);
		return;
	}
	glActiveTexture(GL_TEXTURE0);
	glBindTexture(GL_TEXTURE_2D, tex_id);

	if (m_font_atlas.isDirty()) {
		if (!atlas_texture_valid) {
			m_font_atlas.clearDirty();
		} else {
			const std::vector<eRect>& dirty_rects = m_font_atlas.getDirtyRects();
			const eRect fallback_dirty = m_font_atlas.getDirtyRect();
			const int dirty_count = dirty_rects.empty() ? 1 : (int)dirty_rects.size();
			const int stride = atlas_pix->size().width();

			glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
			GLenum src_fmt = GL_LUMINANCE;
#ifdef HAVE_GLES3
			if (gles::isGLES3())
				src_fmt = GL_RED;
#endif
			for (int i = 0; i < dirty_count; ++i) {
				eRect dirty = dirty_rects.empty() ? fallback_dirty : dirty_rects[i];
				dirty &= eRect(ePoint(0, 0), atlas_pix->size());
				if (dirty.empty())
					continue;

				// GLES 2.0 cannot address sub-rect rows in client memory. GLES3 can upload
				// only the dirty atlas rectangle via GL_UNPACK_ROW_LENGTH.
				int start_x = 0;
				const int start_y = dirty.top();
				int upload_width = atlas_pix->size().width();
				const int height = dirty.height();
				const uint8_t* data = (const uint8_t*)atlas_pix->surface->data + start_y * stride;

#ifdef HAVE_GLES3
				if (gles::isGLES3()) {
					start_x = dirty.left();
					upload_width = dirty.width();
					data += start_x;
					glPixelStorei(GL_UNPACK_ROW_LENGTH, stride);
				}
#endif
				glTexSubImage2D(GL_TEXTURE_2D, 0, start_x, start_y, upload_width, height, src_fmt, GL_UNSIGNED_BYTE, data);
				++m_frame_stats.font_uploads;
				m_frame_stats.font_upload_pixels += rectPixels(eRect(start_x, start_y, upload_width, height));
			}

#ifdef HAVE_GLES3
			if (gles::isGLES3())
				glPixelStorei(GL_UNPACK_ROW_LENGTH, 0);
#endif
			glPixelStorei(GL_UNPACK_ALIGNMENT, 4);
			m_font_atlas.clearDirty();
		}
	}

	glDisable(GL_SCISSOR_TEST);
	m_text_shader.drawBatch(m_text_batch_buffer.data(), m_text_batch_buffer.size());

	glDisable(GL_BLEND);

	m_text_batch_buffer.clear();
	m_text_batch_rects.clear();
	m_text_batch_bounds_valid = false;
}

void gEGLDC::exec(const gOpcode* opcode) {
	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);

	/*
	 * fbClass::lock() prevents new paint commands while an external GLES
	 * client is active. Commands which were already queued still have to be
	 * consumed so their parameter objects and references are released.
	 * Discard them without drawing while retaining correct ownership cleanup.
	 */
	if (m_graphics_suspended) {
		discardOpcode(opcode);
		return;
	}

	if (!isInitialized())
		return;

	if (opcodeCanRunWithoutEGLContext(opcode->opcode)) {
		const unsigned long long draw_start_us = e2eglNowUs();
		{
			e2eglScopedTimer timer(m_frame_stats.state_us);
			gDC::exec(opcode);
		}
		m_frame_stats.draw_us += e2eglNowUs() - draw_start_us;
		return;
	}

	const bool already_current = eglGetCurrentContext() == m_egl_context;
	if (!already_current) {
		const unsigned long long context_make_start_us = e2eglNowUs();
		if (!makeCurrent())
			return;
		m_frame_stats.context_make_us += e2eglNowUs() - context_make_start_us;
		++m_frame_stats.context_make_calls;
	}

	const unsigned long long draw_start_us = e2eglNowUs();
	bool draw_time_recorded = false;
	{
		e2eglScopedTimer timer(m_frame_stats.texture_gc_us);
		m_texture_manager.processDeletions();
	}
	const bool draws_to_surface = opcodeDrawsToSurface(opcode->opcode);
	const bool may_flush_to_surface = opcode->opcode == gOpcode::flush || opcode->opcode == gOpcode::flip || opcode->opcode == gOpcode::sendShow || opcode->opcode == gOpcode::sendHide || opcode->opcode == gOpcode::sendListboxAnimation;
	bool using_scene_framebuffer = false;
	if (sceneFramebufferWanted() && (draws_to_surface || may_flush_to_surface))
		using_scene_framebuffer = bindSceneFramebuffer();
	if (draws_to_surface) {
		if (!using_scene_framebuffer)
			restoreFrameIfNeeded();
		else
			m_frame_restore_pending = false;
	}

	switch (opcode->opcode) {
		case gOpcode::fill:
			{
				eRect area = opcode->parm.fill->area;
				area.moveBy(m_current_offset);
				flushTextBatchIfOverlaps(m_current_clip & area, textFlushFill);
			}
			executeFill(opcode);
			delete opcode->parm.fill;
			break;

		case gOpcode::fillRegion:
			{
				gRegion region = opcode->parm.fillRegion->region;
				region.moveBy(m_current_offset);
				flushTextBatchIfOverlaps(m_current_clip & region, textFlushFill);
			}
			executeFillRegion(opcode);
			delete opcode->parm.fillRegion;
			break;

		case gOpcode::rectangle:
			{
				eRect area = opcode->parm.rectangle->area;
				area.moveBy(m_current_offset);
				gRegion draw_region = m_current_clip & area;
				flushTextBatchIfOverlaps(draw_region, textFlushRectangle);
				flushFillBatchIfOverlaps(draw_region);
			}
			executeRectangle(opcode);
			resetRectangleState();
			delete opcode->parm.rectangle;
			break;

		case gOpcode::line:
			{
				gRegion draw_region = m_current_clip & lineDrawBounds(opcode->parm.line);
				flushTextBatchIfOverlaps(draw_region, textFlushLine);
				flushFillBatchIfOverlaps(draw_region);
			}
			executeLine(opcode);
			delete opcode->parm.line;
			break;

		case gOpcode::blit:
			{
				eRect area = blitDrawBounds(opcode->parm.blit);
				if (!area.empty()) {
					gRegion draw_region = m_current_clip & area;
					flushTextBatchIfOverlaps(draw_region, textFlushBlit);
					flushFillBatchIfOverlaps(draw_region);
				}
			}
			executeBlit(opcode);
			resetBlitState();
			if (opcode->parm.blit->pixmap)
				opcode->parm.blit->pixmap->Release();
			delete opcode->parm.blit;
			break;

		case gOpcode::clear:
			flushTextBatchIfOverlaps(m_current_clip, textFlushClear);
			flushFillBatchIfOverlaps(m_current_clip);
			executeClear(opcode);
			delete opcode->parm.fill;
			break;

		case gOpcode::flush:
		case gOpcode::flip:
			flushTextBatch();
			m_frame_stats.draw_us += e2eglNowUs() - draw_start_us;
			draw_time_recorded = true;
			if (!runPendingWindowAnimation() && !runPendingListboxAnimation()) {
				if (!m_preserved_swap && !sceneFramebufferActive())
					captureCurrentFrameAsLast();
				flip();
			}
			gDC::exec(opcode);
			break;

		case gOpcode::sendShow:
			flushTextBatch();
			executeWindowAnimationOpcode(opcode, true);
			break;

		case gOpcode::sendHide:
			flushTextBatch();
			executeWindowAnimationOpcode(opcode, false);
			break;

		case gOpcode::sendListboxAnimation:
			flushTextBatch();
			executeListboxAnimationOpcode(opcode);
			break;

		default:
			if (!opcodeCanKeepPendingText(opcode->opcode))
				flushTextBatchForReason(textFlushState);
			if (opcode->opcode == gOpcode::renderText || opcode->opcode == gOpcode::renderPara) {
				e2eglScopedTimer timer(m_frame_stats.text_build_us);
				++m_frame_stats.text_ops;
				gDC::exec(opcode);
			} else {
				e2eglScopedTimer timer(m_frame_stats.state_us);
				gDC::exec(opcode);
			}
			break;
	}

	if (!draw_time_recorded)
		m_frame_stats.draw_us += e2eglNowUs() - draw_start_us;

	const bool present_opcode = opcode->opcode == gOpcode::flush || opcode->opcode == gOpcode::flip;
	const unsigned long long context_release_start_us = e2eglNowUs();
	if (releaseCurrent(present_opcode)) {
		m_frame_stats.context_release_us += e2eglNowUs() - context_release_start_us;
		++m_frame_stats.context_release_calls;
	}
}

std::string gEGLDC::getGraphicsWindowProvider() const
{
#ifdef DREAMNEXTGEN
	return "Amlogic";
#elif defined(HAVE_VUPLUS_EGL)
	return "Vuplus";
#elif defined(HAVE_VUPLUS_MIPSEL_EGL)
	return "Vuplus MIPS";
#elif defined(HAVE_NXPL_EGL)
	return "NXPL";
#elif defined(HAVE_V3DPLATFORM_EGL)
	return "V3DPlatform";
#elif defined(HAVE_HISILICON_EGL)
	return "HiSilicon";
#elif defined(HAVE_DREAMBCM_EGL)
	return "Dreambox BCM";
#else
	return "";
#endif
}

std::string gEGLDC::getGraphicsAccelerator() const
{
	std::string info = "GLES/EGL";
#ifdef DREAMNEXTGEN
	info += ", e2ge / Dream GE2D";
	if (dreamGE2DIsActive())
		info += " active";
#endif
	return info;
}

std::string gEGLDC::getGraphicsBuffering() const
{
	const int pages = getGraphicsBufferPages();
	if (pages >= 3)
		return "triple";
	if (pages == 2)
		return "double";
	if (pages == 1)
		return "single";
	return "";
}

int gEGLDC::getGraphicsBufferPages() const
{
	return m_fb && m_fb->Available() ? m_fb->getNumPages() : 0;
}

int gEGLDC::islocked() const
{
	if (m_graphics_suspended)
		return 1;
	fbClass *fb = m_fb ? m_fb : fbClass::getInstance();
	return fb ? fb->islocked() : 0;
}

bool gEGLDC::getGraphicsPreservedSwap() const
{
	return !e2eglForceDestroyedSwap() && m_preserved_swap;
}

bool gEGLDC::suspendGraphics()
{
	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);

	if (m_graphics_suspended)
		return true;

	if (!isInitialized() || m_egl_display == EGL_NO_DISPLAY || m_egl_context == EGL_NO_CONTEXT)
		return false;

	if (!islocked())
		eDebug("[gEGLDC] suspending graphics without fbClass lock; callers should lock painting first");

	if (m_egl_surface != EGL_NO_SURFACE) {
		if (!makeCurrent()) {
			eDebug("[gEGLDC] graphics suspend failed; EGL context could not be made current");
			return false;
		}
		flushFillBatch();
		flushTextBatch();
		m_texture_manager.releaseGLResources();
		deleteSceneFramebuffer();
		deleteFrameTextures();
		m_font_atlas.release();
#ifdef HAVE_DREAMBCM_EGL
		/*
		 * libvc5dream permits only one active EGL client. Release every GL
		 * object before terminating Enigma2's Dream EGL client below.
		 */
		m_basic_shader.release();
		m_advanced_shader.release();
		m_texture_shader.release();
		m_text_shader.release();
#endif
		m_texture_manager.processDeletions();
		glFinish();
		releaseCurrent(true);
	}

	if (m_egl_surface != EGL_NO_SURFACE) {
		if (!eglDestroySurface(m_egl_display, m_egl_surface)) {
			eDebug("[gEGLDC] eglDestroySurface failed while suspending graphics. EGL error: 0x%x", eglGetError());
			m_font_atlas.init();
			return false;
		}
		m_egl_surface = EGL_NO_SURFACE;
	}

#ifdef HAVE_DREAMBCM_EGL
	/*
	 * Surface-only suspension works on the other EGL providers. Dream BCM
	 * keeps an inter-process device lock while EGLDisplay/EGLContext remain
	 * alive; a second EGL application then blocks before reaching main().
	 */
	if (m_egl_context != EGL_NO_CONTEXT) {
		eglDestroyContext(m_egl_display, m_egl_context);
		m_egl_context = EGL_NO_CONTEXT;
	}
	if (m_egl_display != EGL_NO_DISPLAY) {
		eglTerminate(m_egl_display);
		m_egl_display = EGL_NO_DISPLAY;
	}
	eglReleaseThread();
	m_egl_major = 0;
	m_egl_minor = 0;
	m_gles_version = 0;
	m_max_texture_size = 0;
	m_preserved_swap = false;
	gles::version = 0;
	m_texture_manager.setDisplay(EGL_NO_DISPLAY);
	m_texture_manager.resetContextGeneration();
	eDebug("[gEGLDC] Dream BCM EGL display and context released for external client");
#endif

#ifdef HAVE_VUPLUS_EGL
	/*
	 * The Vuplus compositor retains the last submitted OSD buffer after the
	 * EGL surface is destroyed. Remove only the native window while external
	 * framebuffer clients such as TuxText own the display.
	 */
	if (m_window_provider && m_native_window_ready) {
		if (auto *vuplus_provider = dynamic_cast<VuplusWindowProvider*>(m_window_provider)) {
			if (!vuplus_provider->suspend()) {
				eDebug("[gEGLDC] graphics suspend failed; Vuplus native window is still visible");
				return false;
			}
			m_native_window_ready = false;
		}
	}
#endif

#ifdef HAVE_NXPL_EGL
	/*
	 * Destroying the EGL surface alone leaves the last submitted NXPL buffer
	 * visible in the Broadcom compositor.  A transparent Chromium VideoHole
	 * would then reveal stale Enigma2 OSD below it.  Drop only the native OSD
	 * window while suspended; keep the display registration and Nexus client
	 * joined so refresh() can recreate the window cheaply on resume.
	 */
	if (m_window_provider && m_native_window_ready) {
		if (auto *nxpl_provider = dynamic_cast<NxplWindowProvider*>(m_window_provider)) {
			if (!nxpl_provider->suspend()) {
				eDebug("[gEGLDC] graphics suspend failed; NXPL native window is still visible");
				return false;
			}
			m_native_window_ready = false;
		}
	}
#endif

	m_preserved_swap = false;
	m_pending_window_animation.active = false;
	m_pending_listbox_animation.active = false;
	m_pending_listbox_animation.selection_pixmap = nullptr;
	m_frame_restore_pending = false;
	invalidateSpinnerBackground(true);
	std::vector<float>().swap(m_text_batch_buffer);
	std::vector<eRect>().swap(m_text_batch_rects);
	m_text_batch_bounds_valid = false;
	std::vector<float>().swap(m_fill_batch_buffer);
	m_fill_batch_bounds = eRect::emptyRect();
	m_fill_batch_valid = false;

	/*
	 * Keep the logical resolution. Replacing the CPU backing pixmap releases
	 * its full-screen allocation while queued commands can still be disposed
	 * safely. Non-Dream providers also retain EGLDisplay and EGLContext.
	 */
	m_pixmap = new gPixmap(eSize(1, 1), 32, gPixmap::accelNever);
	m_graphics_suspended = true;
	eDebug("[gEGLDC] graphics suspended; EGL surface, frame buffers and transient texture caches released");
	return true;
}

bool gEGLDC::resumeGraphics()
{
	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);

	if (!m_graphics_suspended)
		return true;

#ifdef HAVE_DREAMBCM_EGL
	m_pixmap = new gPixmap(eSize(std::max(1, m_width), std::max(1, m_height)), 32, gPixmap::accelNever);
	m_text_batch_buffer.reserve(MAX_BATCH_GLYPHS * 48);
	m_text_batch_rects.reserve(MAX_BATCH_GLYPHS);
	m_fill_batch_buffer.reserve(1024 * 36);
	m_native_window_ready = m_window_provider && m_window_provider->init(surfaceWidth(), surfaceHeight());
	if (!m_native_window_ready || !initEGL()) {
		cleanupEGL();
		m_graphics_suspended = true;
		m_pixmap = new gPixmap(eSize(1, 1), 32, gPixmap::accelNever);
		std::vector<float>().swap(m_text_batch_buffer);
		std::vector<eRect>().swap(m_text_batch_rects);
		std::vector<float>().swap(m_fill_batch_buffer);
		eDebug("[gEGLDC] Dream BCM graphics resume failed; EGL client could not be recreated");
		return false;
	}
	m_graphics_suspended = false;
	eDebug("[gEGLDC] Dream BCM graphics resumed with a new EGL display and context at %dx%d logical=%dx%d",
		surfaceWidth(), surfaceHeight(), m_width, m_height);
	return true;
#else
	if (!isInitialized() || m_egl_display == EGL_NO_DISPLAY || m_egl_context == EGL_NO_CONTEXT)
		return false;

	m_pixmap = new gPixmap(eSize(std::max(1, m_width), std::max(1, m_height)), 32, gPixmap::accelNever);
	m_text_batch_buffer.reserve(MAX_BATCH_GLYPHS * 48);
	m_text_batch_rects.reserve(MAX_BATCH_GLYPHS);
	m_fill_batch_buffer.reserve(1024 * 36);
	if (!m_font_atlas.init()) {
		m_pixmap = new gPixmap(eSize(1, 1), 32, gPixmap::accelNever);
		eDebug("[gEGLDC] graphics resume failed; font atlas is unavailable");
		return false;
	}
	m_graphics_suspended = false;
	refresh();

	if (m_egl_surface == EGL_NO_SURFACE) {
		m_graphics_suspended = true;
		m_font_atlas.release();
		m_pixmap = new gPixmap(eSize(1, 1), 32, gPixmap::accelNever);
		std::vector<float>().swap(m_text_batch_buffer);
		std::vector<eRect>().swap(m_text_batch_rects);
		std::vector<float>().swap(m_fill_batch_buffer);
		eDebug("[gEGLDC] graphics resume failed; EGL surface is unavailable");
		return false;
	}

	eDebug("[gEGLDC] graphics resumed at %dx%d logical=%dx%d", surfaceWidth(), surfaceHeight(), m_width, m_height);
	return true;
#endif
}

std::string gEGLDC::getOSDAxis() const
{
	return "0 0 " + std::to_string(std::max(1, m_width)) + " " + std::to_string(std::max(1, m_height));
}

bool gEGLDC::setOSDPosition(int left, int top, int width, int height)
{
	if (width < 1 || height < 1)
		return false;

	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);
	const bool old_osd_fullscreen = m_osd_left == 0 && m_osd_top == 0 && m_osd_width == m_width && m_osd_height == m_height;
	const bool egl_ready = isInitialized() && m_egl_display != EGL_NO_DISPLAY && m_egl_surface != EGL_NO_SURFACE && m_egl_context != EGL_NO_CONTEXT;
	bool egl_current = false;

	if (egl_ready) {
		egl_current = makeCurrent();
		if (egl_current) {
			flushTextBatch();
			if (!sceneFramebufferActive() && old_osd_fullscreen)
				captureCurrentFrameAsLast();
		}
	}

	m_osd_left = left;
	m_osd_top = top;
	m_osd_width = width;
	m_osd_height = height;
#if defined(HAVE_NXPL_EGL) && defined(E2EGL_NXPL_SYNC_FB_DST)
	e2eglSyncNxplFramebufferDestination(m_osd_left, m_osd_top, m_osd_width, m_osd_height);
#endif

	if (egl_current) {
		m_pending_window_animation.active = false;
		m_pending_listbox_animation.active = false;
		m_pending_listbox_animation.selection_pixmap = nullptr;
		invalidateSpinnerBackground();
		m_frame_restore_pending = false;

		bool frame_presented = false;
		if (sceneFramebufferActive() && m_scene_frame_valid) {
			frame_presented = presentSceneFramebuffer();
		} else {
			bindWindowFramebuffer();
			glDisable(GL_SCISSOR_TEST);
			glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
			glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
			glClear(GL_COLOR_BUFFER_BIT);
			if (m_last_frame_valid && m_last_frame_texture) {
				const eRect full_frame(0, 0, m_width, m_height);
				glDisable(GL_BLEND);
				m_texture_shader.drawTexture(full_frame.x(), full_frame.y(), full_frame.width(), full_frame.height(),
					m_last_frame_texture, 1.0f, 0.0f, 0, 0.0f, 1.0f, 1.0f, 0.0f, false);
				++m_frame_stats.frame_copy_draws;
				m_frame_stats.frame_copy_pixels += rectPixels(full_frame);
				frame_presented = true;
			}
		}

		const bool swapped = swapWindowFramebuffer();
		if (swapped && frame_presented && sceneFramebufferActive())
			bindSceneFramebuffer();
		releaseCurrent(true);
	}

	const eRect surface_rect = osdDestinationSurface();
	eDebug("[gEGLDC] OSD position set logical=%d,%d %dx%d surface=%d,%d %dx%d",
		m_osd_left, m_osd_top, m_osd_width, m_osd_height,
		surface_rect.x(), surface_rect.y(), surface_rect.width(), surface_rect.height());
	return true;
}

gEGLDC::gEGLDC(INativeWindowProvider* window_provider, int width, int height) : gMainDC(), m_fb(nullptr) {
	int xres = width, yres = height, bpp = 32;

#ifdef DREAMNEXTGEN
	setenv("DREAM_GE2D_SURFACE_ACCEL", "1", 0);
	setenv("DREAM_GE2D_ACCEL_FILL", "1", 0);
	setenv("DREAM_GE2D_ACCEL_BLIT", "1", 0);
#endif

	if (!window_provider) {
#if defined(DREAMNEXTGEN) || defined(HAVE_VUPLUS_MIPSEL_EGL) || defined(HAVE_HISILICON_EGL) || defined(HAVE_DREAMBCM_EGL) || defined(HAVE_NXPL_EGL) || defined(HAVE_V3DPLATFORM_EGL)
		m_fb = new fbClass;
		if (m_fb->Available())
			m_fb->getMode(xres, yres, bpp);
#ifdef HAVE_HISILICON_EGL
		int skin_xres = 0, skin_yres = 0, skin_bpp = 32;
		if (e2eglReadConfiguredSkinResolution(skin_xres, skin_yres, skin_bpp)) {
			xres = skin_xres;
			yres = skin_yres;
			bpp = skin_bpp;
			eDebug("[gEGLDC] Hisi early skin framebuffer mode requested %dx%dx%d", xres, yres, bpp);
		} else {
			xres = 1280;
			yres = 720;
			bpp = 32;
			eDebug("[gEGLDC] Hisi early skin framebuffer mode fallback %dx%dx%d", xres, yres, bpp);
		}
#endif
#else
		if (fbClass::getInstance())
			fbClass::getInstance()->getMode(xres, yres, bpp);
#endif
		if (!((xres == 720 && yres == 576) || (xres == 1280 && yres == 720) || (xres == 1920 && yres == 1080) || (xres == 2560 && yres == 1440))) {
			xres = 1280;
			yres = 720;
			bpp = 32;
		}
#if defined(DREAMNEXTGEN) || defined(HAVE_VUPLUS_MIPSEL_EGL) || defined(HAVE_HISILICON_EGL) || defined(HAVE_DREAMBCM_EGL) || defined(HAVE_NXPL_EGL) || defined(HAVE_V3DPLATFORM_EGL)
		if (m_fb && m_fb->Available()) {
			m_fb->SetMode(xres, yres, bpp);
			m_fb->getMode(xres, yres, bpp);
		}
#endif
		width = xres;
		height = yres;
#ifdef DREAMNEXTGEN
		window_provider = new AmlogicWindowProvider(width, height);
#elif defined(HAVE_VUPLUS_EGL)
		window_provider = new VuplusWindowProvider();
#elif defined(HAVE_VUPLUS_MIPSEL_EGL)
		window_provider = new VuplusMipsWindowProvider();
#elif defined(HAVE_NXPL_EGL)
		window_provider = new NxplWindowProvider();
#elif defined(HAVE_V3DPLATFORM_EGL)
		window_provider = new V3DPlatformWindowProvider();
#elif defined(HAVE_HISILICON_EGL)
		window_provider = new HisiliconWindowProvider(width, height);
#elif defined(HAVE_DREAMBCM_EGL)
		window_provider = new DreamBcmWindowProvider(width, height);
#endif
	}

	m_window_provider = window_provider;
	m_width = width;
	m_height = height;
	m_surface_width = width;
	m_surface_height = height;
#ifdef HAVE_VUPLUS_EGL
	m_video_mode_surface_active = true;
#else
	m_video_mode_surface_active = false;
#endif
	updateVideoModeSurfaceSize("constructor");
#if defined(HAVE_NXPL_EGL)
	if (e2eglNxplUseVideoModeSurface() && m_fb && m_fb->Available()) {
		int fb_xres = surfaceWidth(), fb_yres = surfaceHeight(), fb_bpp = bpp;
		m_fb->SetMode(surfaceWidth(), surfaceHeight(), bpp);
		m_fb->getMode(fb_xres, fb_yres, fb_bpp);
		m_surface_width = fb_xres;
		m_surface_height = fb_yres;
		eDebug("[gEGLDC] NXPL framebuffer mode initialised to %dx%dx%d logical=%dx%d", fb_xres, fb_yres, fb_bpp, m_width, m_height);
	}
#endif
	m_osd_left = 0;
	m_osd_top = 0;
	m_osd_width = width;
	m_osd_height = height;
#if defined(HAVE_NXPL_EGL) && defined(E2EGL_NXPL_SYNC_FB_DST)
	e2eglSyncNxplFramebufferDestination(m_osd_left, m_osd_top, m_osd_width, m_osd_height);
#endif
	m_egl_major = 0;
	m_egl_minor = 0;
	m_gles_version = 0;
	m_max_texture_size = 0;
	m_flip_count = 0;
	m_preserved_swap = false;
	m_native_window_ready = false;
	m_graphics_suspended = false;
	m_egl_display = EGL_NO_DISPLAY;
	m_egl_surface = EGL_NO_SURFACE;
	m_egl_context = EGL_NO_CONTEXT;
	m_last_frame_texture = 0;
	m_animation_frame_texture = 0;
	m_scene_frame_texture = 0;
	m_scene_framebuffer = 0;
	m_scene_spare_frame_texture = 0;
	m_scene_spare_framebuffer = 0;
	m_scene_animation_old_texture = 0;
	m_last_frame_valid = false;
	m_frame_restore_pending = false;
	m_frame_texture_surface = false;
	m_frame_texture_scene_scaled = false;
	m_frame_texture_width = 0;
	m_frame_texture_height = 0;
	m_scene_frame_width = 0;
	m_scene_frame_height = 0;
	m_scene_frame_valid = false;
	m_scene_spare_frame_valid = false;
	m_scene_animation_old_valid = false;
	m_scene_framebuffer_unavailable = false;
	m_spinner_background_valid = false;
	m_spinner_background_width = 0;
	m_spinner_background_height = 0;
	m_spinner_background_clear = false;
	m_spinner_clear_pending = false;
	m_capture_socket_fd = -1;
	m_capture_thread_started = false;
	m_capture_thread_stop = false;
	m_frame_stats_index = 0;
	m_text_batch_bounds = eRect();
	m_text_batch_bounds_valid = false;
	m_text_batch_buffer.reserve(MAX_BATCH_GLYPHS * 48);
	m_text_batch_rects.reserve(MAX_BATCH_GLYPHS);
	m_fill_batch_bounds = eRect::emptyRect();
	m_fill_batch_color = gRGB();
	m_fill_batch_blend = false;
	m_fill_batch_valid = false;
	m_fill_batch_buffer.reserve(1024 * 36);
	resetFrameStats();

	m_pixmap = new gPixmap(eSize(width, height), 32, gPixmap::accelNever);
	if (m_window_provider) {
		m_native_window_ready = m_window_provider->init(surfaceWidth(), surfaceHeight());
		if (!m_native_window_ready)
			eDebug("[gEGLDC] native window provider init failed");
	}
}

gEGLDC::~gEGLDC() {
	stopCaptureServer();
	cleanupEGL();
	if (m_window_provider) {
		m_window_provider->cleanup();
		delete m_window_provider;
		m_window_provider = nullptr;
	}
	delete m_fb;
	m_fb = nullptr;
}

void gEGLDC::cleanupEGL() {
	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);

	if (m_egl_display != EGL_NO_DISPLAY) {
		if (makeCurrent()) {
			m_texture_manager.releaseGLResources();
			deleteSceneFramebuffer();
			deleteFrameTextures();
#ifdef HAVE_DREAMBCM_EGL
			m_basic_shader.release();
			m_advanced_shader.release();
			m_texture_shader.release();
			m_text_shader.release();
#endif
			releaseCurrent(true);
		}
		if (m_egl_context != EGL_NO_CONTEXT) {
			eglDestroyContext(m_egl_display, m_egl_context);
		}
		if (m_egl_surface != EGL_NO_SURFACE) {
			eglDestroySurface(m_egl_display, m_egl_surface);
		}
		eglTerminate(m_egl_display);
	}
	m_egl_display = EGL_NO_DISPLAY;
	m_egl_surface = EGL_NO_SURFACE;
	m_egl_context = EGL_NO_CONTEXT;
	m_egl_major = 0;
	m_egl_minor = 0;
	m_gles_version = 0;
	m_max_texture_size = 0;
	m_scene_frame_texture = 0;
	m_scene_framebuffer = 0;
	m_scene_spare_frame_texture = 0;
	m_scene_spare_framebuffer = 0;
	m_scene_animation_old_texture = 0;
	m_scene_frame_width = 0;
	m_scene_frame_height = 0;
	m_scene_frame_valid = false;
	m_scene_spare_frame_valid = false;
	m_scene_animation_old_valid = false;
	m_scene_framebuffer_unavailable = false;
	m_last_frame_texture = 0;
	m_animation_frame_texture = 0;
	m_last_frame_valid = false;
	m_frame_restore_pending = false;
	m_frame_texture_surface = false;
	m_frame_texture_scene_scaled = false;
	m_graphics_suspended = false;
#ifdef HAVE_DREAMBCM_EGL
	m_texture_manager.setDisplay(EGL_NO_DISPLAY);
#endif
	gles::version = 0;
}

void gEGLDC::setResolution(int xres, int yres, int bpp) {
	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);

	int surface_xres = xres;
	int surface_yres = yres;
#if defined(HAVE_DREAMBCM_EGL)
	if (m_surface_width > 0 && m_surface_height > 0) {
		surface_xres = m_surface_width;
		surface_yres = m_surface_height;
		if (xres > surface_xres || yres > surface_yres) {
			surface_xres = xres;
			surface_yres = yres;
		}
	}
#endif
#if defined(HAVE_VUPLUS_EGL)
	if (m_video_mode_surface_active) {
		int mode_xres = 0, mode_yres = 0;
		const std::string mode = e2eglReadTextFile("/proc/stb/video/videomode");
		if (e2eglVideoModeToSize(mode, mode_xres, mode_yres)) {
			e2eglLimitVuplusNativeSurfaceSize(mode_xres, mode_yres);
			surface_xres = mode_xres;
			surface_yres = mode_yres;
		}
	} else if (m_surface_width > 0 && m_surface_height > 0) {
		surface_xres = m_surface_width;
		surface_yres = m_surface_height;
	}
#elif defined(HAVE_NXPL_EGL)
	if (e2eglNxplUseVideoModeSurface()) {
		int mode_xres = 0, mode_yres = 0;
		const std::string mode = e2eglReadTextFile("/proc/stb/video/videomode");
		if (e2eglVideoModeToSize(mode, mode_xres, mode_yres)) {
			surface_xres = mode_xres;
			surface_yres = mode_yres;
		}
	}
#endif

	const bool surface_size_changed = m_surface_width != surface_xres || m_surface_height != surface_yres;
	const bool native_window_must_recreate = false;
	if (m_width == xres && m_height == yres && !surface_size_changed)
		return;

	const bool osd_was_fullscreen = m_osd_left == 0 && m_osd_top == 0 && m_osd_width == m_width && m_osd_height == m_height;
	const bool egl_ready = isInitialized() && m_egl_display != EGL_NO_DISPLAY && m_egl_context != EGL_NO_CONTEXT;
	if (egl_ready && eglGetCurrentContext() == m_egl_context)
		releaseCurrent(true);
	if (egl_ready && (surface_size_changed || native_window_must_recreate) && m_egl_surface != EGL_NO_SURFACE) {
		eglDestroySurface(m_egl_display, m_egl_surface);
		m_egl_surface = EGL_NO_SURFACE;
	}

	m_width = xres;
	m_height = yres;
	m_surface_width = surface_xres;
	m_surface_height = surface_yres;
	m_scene_framebuffer_unavailable = false;
	if (osd_was_fullscreen) {
		m_osd_left = 0;
		m_osd_top = 0;
		m_osd_width = xres;
		m_osd_height = yres;
	}
#if defined(HAVE_NXPL_EGL) && defined(E2EGL_NXPL_SYNC_FB_DST)
	e2eglSyncNxplFramebufferDestination(m_osd_left, m_osd_top, m_osd_width, m_osd_height);
#endif
	m_pixmap = new gPixmap(eSize(xres, yres), bpp, gPixmap::accelNever);
	invalidateSpinnerBackground();
#ifdef DREAMNEXTGEN
	if (m_fb && m_fb->Available()) {
		m_fb->SetMode(xres, yres, bpp);
		m_fb->getMode(xres, yres, bpp);
		eDebug("[gEGLDC] framebuffer mode set to %dx%dx%d", xres, yres, bpp);
	}
#elif defined(HAVE_HISILICON_EGL)
	if (m_fb && m_fb->Available()) {
		int fb_xres = surface_xres, fb_yres = surface_yres, fb_bpp = bpp;
		m_fb->SetMode(surface_xres, surface_yres, bpp);
		m_fb->getMode(fb_xres, fb_yres, fb_bpp);
		m_surface_width = fb_xres;
		m_surface_height = fb_yres;
		eDebug("[gEGLDC] Hisi framebuffer mode set to %dx%dx%d logical=%dx%d", fb_xres, fb_yres, fb_bpp, m_width, m_height);
	}
#elif defined(HAVE_DREAMBCM_EGL)
	if (m_fb && m_fb->Available()) {
		int fb_xres = surface_xres, fb_yres = surface_yres, fb_bpp = bpp;
		m_fb->SetMode(surface_xres, surface_yres, bpp);
		m_fb->getMode(fb_xres, fb_yres, fb_bpp);
		m_surface_width = fb_xres;
		m_surface_height = fb_yres;
		eDebug("[gEGLDC] framebuffer mode set to %dx%dx%d logical=%dx%d", fb_xres, fb_yres, fb_bpp, m_width, m_height);
	}
#elif defined(HAVE_NXPL_EGL)
	if (e2eglNxplUseVideoModeSurface() && m_fb && m_fb->Available()) {
		int fb_xres = surface_xres, fb_yres = surface_yres, fb_bpp = bpp;
		m_fb->SetMode(surface_xres, surface_yres, bpp);
		m_fb->getMode(fb_xres, fb_yres, fb_bpp);
		m_surface_width = fb_xres;
		m_surface_height = fb_yres;
		eDebug("[gEGLDC] NXPL framebuffer mode set to %dx%dx%d logical=%dx%d", fb_xres, fb_yres, fb_bpp, m_width, m_height);
	}
#endif
	if (m_graphics_suspended) {
		m_pixmap = new gPixmap(eSize(1, 1), 32, gPixmap::accelNever);
		eDebug("[gEGLDC] suspended graphics resolution changed to %dx%d surface=%dx%d",
			m_width, m_height, surfaceWidth(), surfaceHeight());
		return;
	}
	if (m_window_provider) {
		m_native_window_ready = m_window_provider->init(surfaceWidth(), surfaceHeight());
		if (!m_native_window_ready) {
			eDebug("[gEGLDC] native window provider resize init failed for %dx%d logical=%dx%d",
				surfaceWidth(), surfaceHeight(), m_width, m_height);
			return;
		}
	}

	if (egl_ready) {
		if (m_egl_surface == EGL_NO_SURFACE) {
			EGLNativeWindowType native_window = m_window_provider ? m_window_provider->getNativeWindow() : (EGLNativeWindowType)0;
			if (!native_window && e2eglRequiresNativeWindow()) {
				eDebug("[gEGLDC] native window is not available while resizing to %dx%d logical=%dx%d",
					surfaceWidth(), surfaceHeight(), m_width, m_height);
				return;
			}
			m_egl_surface = eglCreateWindowSurface(m_egl_display, m_egl_config, native_window, nullptr);
			if (m_egl_surface == EGL_NO_SURFACE) {
				eDebug("[gEGLDC] eglCreateWindowSurface failed while resizing to %dx%d logical=%dx%d. EGL error: 0x%x",
					surfaceWidth(), surfaceHeight(), m_width, m_height, eglGetError());
				return;
			}
			applySwapBehavior();
		}
		if (makeCurrent()) {
			deleteSceneFramebuffer();
			deleteFrameTextures();
			m_pending_window_animation.active = false;
			m_pending_listbox_animation.active = false;
			m_pending_listbox_animation.selection_pixmap = nullptr;
			invalidateSpinnerBackground();
			m_flip_count = 0;
			applyWindowViewport();
			eglSwapInterval(m_egl_display, 1);
			m_basic_shader.setResolution((float)m_width, (float)m_height);
			m_advanced_shader.setResolution((float)m_width, (float)m_height);
			m_texture_shader.setResolution((float)m_width, (float)m_height);
			m_text_shader.setResolution((float)m_width, (float)m_height);
			primeEGLSurface();
			eDebug("[gEGLDC] resized EGL surface to %dx%d logical=%dx%d", surfaceWidth(), surfaceHeight(), m_width, m_height);
			releaseCurrent(true);
		}
	}
}

void gEGLDC::refresh() {
	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);

	if (!isInitialized() || m_egl_display == EGL_NO_DISPLAY || m_egl_context == EGL_NO_CONTEXT)
		return;

	bool preserve_scene = false;
#ifdef HAVE_DREAMBCM_EGL
	if (m_egl_surface != EGL_NO_SURFACE && makeCurrent()) {
		if (sceneFramebufferActive()) {
			bindSceneFramebuffer();
			flushTextBatch();
			glFlush();
			preserve_scene = m_scene_frame_valid;
		}
		releaseCurrent(true);
	}
#endif

#ifdef HAVE_VUPLUS_MIPSEL_EGL
	if (m_egl_surface != EGL_NO_SURFACE) {
		if (makeCurrent()) {
			applyWindowViewport();
			eglSwapInterval(m_egl_display, 1);
			releaseCurrent(true);
		}
		eDebug("[gEGLDC] Vuplus MIPS refresh keeps existing EGL surface at %dx%d logical=%dx%d",
			surfaceWidth(), surfaceHeight(), m_width, m_height);
		return;
	}
	eDebug("[gEGLDC] Vuplus MIPS refresh recreates missing EGL surface at %dx%d logical=%dx%d",
		surfaceWidth(), surfaceHeight(), m_width, m_height);
#endif

#ifdef DREAMNEXTGEN
	if (m_fb && m_fb->Available()) {
		m_fb->SetMode(m_width, m_height, 32);
		eDebug("[gEGLDC] framebuffer mode refreshed to %dx%d", m_width, m_height);
	}
#elif defined(HAVE_HISILICON_EGL)
	if (m_fb && m_fb->Available()) {
		int fb_xres = surfaceWidth(), fb_yres = surfaceHeight(), fb_bpp = 32;
		m_fb->SetMode(surfaceWidth(), surfaceHeight(), 32);
		m_fb->getMode(fb_xres, fb_yres, fb_bpp);
		m_surface_width = fb_xres;
		m_surface_height = fb_yres;
		eDebug("[gEGLDC] Hisi framebuffer mode refreshed to %dx%dx%d logical=%dx%d", fb_xres, fb_yres, fb_bpp, m_width, m_height);
	}
#elif defined(HAVE_DREAMBCM_EGL)
	if (m_fb && m_fb->Available()) {
		int fb_xres = surfaceWidth(), fb_yres = surfaceHeight(), fb_bpp = 32;
		m_fb->SetMode(surfaceWidth(), surfaceHeight(), 32);
		m_fb->getMode(fb_xres, fb_yres, fb_bpp);
		m_surface_width = fb_xres;
		m_surface_height = fb_yres;
		eDebug("[gEGLDC] framebuffer mode refreshed to %dx%d logical=%dx%d", surfaceWidth(), surfaceHeight(), m_width, m_height);
	}
#elif defined(HAVE_VUPLUS_EGL)
	updateVideoModeSurfaceSize("refresh");
#elif defined(HAVE_NXPL_EGL)
	updateVideoModeSurfaceSize("refresh");
	if (e2eglNxplUseVideoModeSurface() && m_fb && m_fb->Available()) {
		int fb_xres = surfaceWidth(), fb_yres = surfaceHeight(), fb_bpp = 32;
		m_fb->SetMode(surfaceWidth(), surfaceHeight(), 32);
		m_fb->getMode(fb_xres, fb_yres, fb_bpp);
		m_surface_width = fb_xres;
		m_surface_height = fb_yres;
		eDebug("[gEGLDC] NXPL framebuffer mode refreshed to %dx%dx%d logical=%dx%d", fb_xres, fb_yres, fb_bpp, m_width, m_height);
	}
#if defined(HAVE_NXPL_EGL) && defined(E2EGL_NXPL_SYNC_FB_DST)
	e2eglSyncNxplFramebufferDestination(m_osd_left, m_osd_top, m_osd_width, m_osd_height);
#endif
#elif defined(HAVE_V3DPLATFORM_EGL)
	eDebug("[gEGLDC] V3D OSD refresh recreates EGL window surface at %dx%d logical=%dx%d",
		surfaceWidth(), surfaceHeight(), m_width, m_height);
#endif

	if (eglGetCurrentContext() == m_egl_context)
		releaseCurrent(true);
	if (m_egl_surface != EGL_NO_SURFACE) {
		eglDestroySurface(m_egl_display, m_egl_surface);
		m_egl_surface = EGL_NO_SURFACE;
	}
	if (m_window_provider) {
#if defined(HAVE_V3DPLATFORM_EGL)
		if (auto *v3d_provider = dynamic_cast<V3DPlatformWindowProvider*>(m_window_provider))
			m_native_window_ready = v3d_provider->recreate(surfaceWidth(), surfaceHeight());
		else
#endif
			m_native_window_ready = m_window_provider->init(surfaceWidth(), surfaceHeight());
		if (!m_native_window_ready) {
			eDebug("[gEGLDC] native window provider refresh init failed for %dx%d logical=%dx%d",
				surfaceWidth(), surfaceHeight(), m_width, m_height);
			return;
		}
	}

	EGLNativeWindowType native_window = m_window_provider ? m_window_provider->getNativeWindow() : (EGLNativeWindowType)0;
	if (!native_window && e2eglRequiresNativeWindow()) {
		eDebug("[gEGLDC] native window is not available while refreshing %dx%d logical=%dx%d",
			surfaceWidth(), surfaceHeight(), m_width, m_height);
		return;
	}
	m_egl_surface = eglCreateWindowSurface(m_egl_display, m_egl_config, native_window, nullptr);
	if (m_egl_surface == EGL_NO_SURFACE) {
		eDebug("[gEGLDC] eglCreateWindowSurface failed while refreshing %dx%d logical=%dx%d. EGL error: 0x%x",
			surfaceWidth(), surfaceHeight(), m_width, m_height, eglGetError());
		return;
	}
	applySwapBehavior();

	if (makeCurrent()) {
		deleteFrameTextures();
		if (!preserve_scene)
			deleteSceneFramebuffer();
		m_scene_framebuffer_unavailable = false;
		m_pending_window_animation.active = false;
		m_pending_listbox_animation.active = false;
		m_pending_listbox_animation.selection_pixmap = nullptr;
		m_scene_animation_old_texture = 0;
		m_scene_animation_old_valid = false;
		invalidateSpinnerBackground();
		m_flip_count = 0;
		m_frame_stats_index = 0;
		resetFrameStats();
		applyWindowViewport();
		eglSwapInterval(m_egl_display, 1);
		m_basic_shader.setResolution((float)m_width, (float)m_height);
		m_advanced_shader.setResolution((float)m_width, (float)m_height);
		m_texture_shader.setResolution((float)m_width, (float)m_height);
		m_text_shader.setResolution((float)m_width, (float)m_height);
		primeEGLSurface(preserve_scene);
		if (preserve_scene && presentSceneFramebuffer()) {
			if (swapWindowFramebuffer())
				bindSceneFramebuffer();
		}
		eDebug("[gEGLDC] refreshed EGL surface at %dx%d logical=%dx%d", surfaceWidth(), surfaceHeight(), m_width, m_height);
		releaseCurrent(true);
	}
}

void gEGLDC::flip() {
	std::lock_guard<std::recursive_mutex> lock(m_egl_mutex);

	if (isInitialized() && m_egl_display != EGL_NO_DISPLAY && m_egl_surface != EGL_NO_SURFACE) {
		const bool already_current = eglGetCurrentContext() == m_egl_context;
		if (!already_current) {
			const unsigned long long context_make_start_us = e2eglNowUs();
			if (!makeCurrent())
				return;
			m_frame_stats.context_make_us += e2eglNowUs() - context_make_start_us;
			++m_frame_stats.context_make_calls;
		}
		if (sceneFramebufferWanted())
			bindSceneFramebuffer();
		flushTextBatch();
		const bool scene_presented = presentSceneFramebuffer();
		const bool swapped = swapWindowFramebuffer();
		if (swapped) {
			if (scene_presented)
				bindSceneFramebuffer();
			if (!already_current) {
				const unsigned long long context_release_start_us = e2eglNowUs();
				if (releaseCurrent(true)) {
					m_frame_stats.context_release_us += e2eglNowUs() - context_release_start_us;
					++m_frame_stats.context_release_calls;
				}
			}
			logAndResetFrameStats();
			m_frame_restore_pending = !scene_presented && !m_preserved_swap && m_last_frame_valid;
		}
		if (!already_current && !swapped) {
			const unsigned long long context_release_start_us = e2eglNowUs();
			if (releaseCurrent(true)) {
				m_frame_stats.context_release_us += e2eglNowUs() - context_release_start_us;
				++m_frame_stats.context_release_calls;
			}
		}
	}
}
