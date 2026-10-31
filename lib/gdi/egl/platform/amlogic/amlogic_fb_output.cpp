#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/amlogic/amlogic_fb_output.h>
#include <lib/gdi/fb.h>
#include <algorithm>
#include <climits>
#include <cerrno>
#include <fcntl.h>
#include <linux/fb.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#ifndef EGL_LINUX_DMA_BUF_EXT
#define EGL_LINUX_DMA_BUF_EXT 0x3270
#endif
#ifndef EGL_LINUX_DRM_FOURCC_EXT
#define EGL_LINUX_DRM_FOURCC_EXT 0x3271
#endif
#ifndef EGL_DMA_BUF_PLANE0_FD_EXT
#define EGL_DMA_BUF_PLANE0_FD_EXT 0x3272
#endif
#ifndef EGL_DMA_BUF_PLANE0_OFFSET_EXT
#define EGL_DMA_BUF_PLANE0_OFFSET_EXT 0x3273
#endif
#ifndef EGL_DMA_BUF_PLANE0_PITCH_EXT
#define EGL_DMA_BUF_PLANE0_PITCH_EXT 0x3274
#endif
#ifndef DRM_FORMAT_ARGB8888
#define DRM_FORMAT_ARGB8888 0x34325241
#endif

// Amlogic OSD driver: exports the whole framebuffer memory of the node as one dma-buf.
#define FBIOGET_OSD_DMABUF 0x46fc
// Waits for the next vsync and returns its CLOCK_MONOTONIC time in ns as s64, despite the declared size.
#define FBIO_WAITFORVSYNC_64 _IOW('F', 0x21, uint32_t)

struct OsdDmabufExport {
	uint32_t buffer_idx;
	uint32_t fd;
	uint32_t flags;
};

typedef void (*gEGLImageTargetTexture2DOESProc)(GLenum target, void* image);

static int64_t monotonicNs() {
	timespec now = {};
	clock_gettime(CLOCK_MONOTONIC, &now);
	return (int64_t)now.tv_sec * 1000000000LL + now.tv_nsec;
}

static bool waitForGPU() {
	GLsync fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
	if (!fence)
		return false;
	const GLenum result = glClientWaitSync(fence, GL_SYNC_FLUSH_COMMANDS_BIT, 200000000ULL);
	glDeleteSync(fence);
	return result == GL_ALREADY_SIGNALED || result == GL_CONDITION_SATISFIED;
}

AmlogicFramebufferOutput::~AmlogicFramebufferOutput() {
	destroy();
}

bool AmlogicFramebufferOutput::create(EGLDisplay display, int width, int height) {
	destroy();

	m_fb_fd = open("/dev/fb0", O_RDWR | O_CLOEXEC);
	if (m_fb_fd < 0) {
		eDebug("[AmlogicFramebufferOutput] open /dev/fb0 failed: %m");
		return false;
	}
	fb_fix_screeninfo fix = {};
	fb_var_screeninfo var = {};
	OsdDmabufExport dmabuf = {};
	if (ioctl(m_fb_fd, FBIOGET_FSCREENINFO, &fix) < 0 || ioctl(m_fb_fd, FBIOGET_VSCREENINFO, &var) < 0 || ioctl(m_fb_fd, FBIOGET_OSD_DMABUF, &dmabuf) < 0) {
		eDebug("[AmlogicFramebufferOutput] framebuffer query failed: %m");
		destroy();
		return false;
	}
	m_dmabuf_fd = (int)dmabuf.fd;

	if (width <= 0 || height <= 0 || (int)var.xres != width || (int)var.yres != height || var.bits_per_pixel != 32 ||
		var.xres_virtual < var.xres || var.yres_virtual < var.yres || var.xoffset || var.yoffset % var.yres ||
		fix.line_length < static_cast<uint64_t>(width) * 4 || fix.line_length % 4 || fix.line_length > INT_MAX ||
		var.red.offset != 16 || var.green.offset != 8 || var.blue.offset != 0 || var.transp.offset != 24 ||
		var.red.length != 8 || var.green.length != 8 || var.blue.length != 8 || var.transp.length != 8 ||
		var.red.msb_right || var.green.msb_right || var.blue.msb_right || var.transp.msb_right || m_dmabuf_fd < 0) {
		eDebug("[AmlogicFramebufferOutput] framebuffer is %ux%ux%u, expected %dx%dx32", var.xres, var.yres, var.bits_per_pixel, width, height);
		destroy();
		return false;
	}
	if (fcntl(m_dmabuf_fd, F_SETFD, FD_CLOEXEC) < 0) {
		destroy();
		return false;
	}
	const uint64_t page_size = static_cast<uint64_t>(fix.line_length) * var.yres;
	const int pages = std::min<int>({MAX_PAGES, (int)(var.yres_virtual / var.yres), (int)(fix.smem_len / page_size)});
	if (pages < MAX_PAGES || page_size * (pages - 1) > INT_MAX || var.yoffset / var.yres >= static_cast<unsigned>(pages)) {
		eDebug("[AmlogicFramebufferOutput] only %d framebuffer page(s) available, %d needed", pages, MAX_PAGES);
		destroy();
		return false;
	}

	PFNEGLCREATEIMAGEKHRPROC eglCreateImageKHR = (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
	gEGLImageTargetTexture2DOESProc glEGLImageTargetTexture2DOES = (gEGLImageTargetTexture2DOESProc)eglGetProcAddress("glEGLImageTargetTexture2DOES");
	if (!eglCreateImageKHR || !glEGLImageTargetTexture2DOES) {
		eDebug("[AmlogicFramebufferOutput] EGLImage functions unavailable");
		destroy();
		return false;
	}

	m_display = display;
	GLint previous_framebuffer = 0;
	GLint previous_texture = 0;
	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glGetIntegerv(GL_TEXTURE_BINDING_2D, &previous_texture);

	bool complete = true;
	for (int page = 0; page < pages && complete; ++page) {
		const EGLint attribs[] = {
			EGL_WIDTH, width,
			EGL_HEIGHT, height,
			EGL_LINUX_DRM_FOURCC_EXT, DRM_FORMAT_ARGB8888,
			EGL_DMA_BUF_PLANE0_FD_EXT, m_dmabuf_fd,
			EGL_DMA_BUF_PLANE0_OFFSET_EXT, (EGLint)(page * page_size),
			EGL_DMA_BUF_PLANE0_PITCH_EXT, (EGLint)fix.line_length,
			EGL_NONE};
		m_images[page] = eglCreateImageKHR(display, EGL_NO_CONTEXT, EGL_LINUX_DMA_BUF_EXT, (EGLClientBuffer) nullptr, attribs);
		if (m_images[page] == EGL_NO_IMAGE_KHR) {
			eDebug("[AmlogicFramebufferOutput] eglCreateImageKHR for page %d failed: 0x%x", page, eglGetError());
			complete = false;
			break;
		}
		glGenTextures(1, &m_textures[page]);
		glBindTexture(GL_TEXTURE_2D, m_textures[page]);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
		glEGLImageTargetTexture2DOES(GL_TEXTURE_2D, (void*)m_images[page]);
		glGenFramebuffers(1, &m_framebuffers[page]);
		glBindFramebuffer(GL_FRAMEBUFFER, m_framebuffers[page]);
		glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, m_textures[page], 0);
		const GLenum status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
		if (status != GL_FRAMEBUFFER_COMPLETE) {
			eDebug("[AmlogicFramebufferOutput] page %d framebuffer incomplete: 0x%x", page, status);
			complete = false;
		}
	}
	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
	glBindTexture(GL_TEXTURE_2D, previous_texture);
	if (!complete) {
		destroy();
		return false;
	}

	m_pages = pages;
	m_height = height;
	// Start on the page after the one currently shown.
	m_shown_page = (int)(var.yoffset / var.yres) % pages;
	m_back_page = (m_shown_page + 1) % pages;
	watchRunning = true;
	try {
		vsyncThread = std::thread(&AmlogicFramebufferOutput::watchVsync, this);
	} catch (const std::system_error& error) {
		eWarning("[AmlogicFramebufferOutput] VSync observer unavailable: %s", error.what());
		destroy();
		return false;
	}
	eDebug("[AmlogicFramebufferOutput] %d framebuffer pages %dx%d stride=%u active, back page %d", pages, width, height, fix.line_length, m_back_page);
	return true;
}

void AmlogicFramebufferOutput::destroy() {
	watchRunning = false;
	vsyncChanged.notify_all();
	// This driver's FBIO_WAITFORVSYNC has a kernel timeout of one second.
	// Keep the fd alive until the observer has left that ioctl.
	if (vsyncThread.joinable()) vsyncThread.join();
	const bool gl_current = eglGetCurrentContext() != EGL_NO_CONTEXT;
	PFNEGLDESTROYIMAGEKHRPROC eglDestroyImageKHR = (PFNEGLDESTROYIMAGEKHRPROC)eglGetProcAddress("eglDestroyImageKHR");
	for (int page = 0; page < MAX_PAGES; ++page) {
		if (gl_current && m_framebuffers[page])
			glDeleteFramebuffers(1, &m_framebuffers[page]);
		if (gl_current && m_textures[page])
			glDeleteTextures(1, &m_textures[page]);
		if (m_images[page] != EGL_NO_IMAGE_KHR && eglDestroyImageKHR && m_display != EGL_NO_DISPLAY)
			eglDestroyImageKHR(m_display, m_images[page]);
		m_framebuffers[page] = 0;
		m_textures[page] = 0;
		m_images[page] = EGL_NO_IMAGE_KHR;
	}
	if (m_dmabuf_fd >= 0)
		close(m_dmabuf_fd);
	if (m_fb_fd >= 0)
		close(m_fb_fd);
	m_dmabuf_fd = -1;
	m_fb_fd = -1;
	m_display = EGL_NO_DISPLAY;
	m_pages = 0;
	m_back_page = 0;
	m_shown_page = 0;
	m_height = 0;
	observedVsync = 0;
	vsyncFailed = false;
	pageReady = true;
	for (int64_t& hidden_since : m_hidden_since_ns)
		hidden_since = 0;
}

void AmlogicFramebufferOutput::watchVsync() {
	while (watchRunning) {
		int64_t vsync = 0;
		const int result = ioctl(m_fb_fd, FBIO_WAITFORVSYNC_64, &vsync);
		if (result < 0 && errno == EINTR) continue;
		// A disabled HDMI clock can time out without a new timestamp. Keep
		// observing; waitUntilHidden still refuses an unconfirmed page.
		if (result == 0 && vsync == observedVsync) continue;
		{
			std::lock_guard<std::mutex> lock(vsyncMutex);
			if (result < 0 || vsync <= observedVsync || vsync > monotonicNs()) {
				vsyncFailed = watchRunning.load();
				vsyncChanged.notify_all();
				return;
			}
			observedVsync = vsync;
		}
		vsyncChanged.notify_all();
	}
}

bool AmlogicFramebufferOutput::waitUntilHidden(int page) {
	if (!m_hidden_since_ns[page]) return true;
	std::unique_lock<std::mutex> lock(vsyncMutex);
	const int64_t hidden = m_hidden_since_ns[page];
	if (!vsyncChanged.wait_for(lock, std::chrono::milliseconds(120), [&] { return observedVsync > hidden || vsyncFailed || !watchRunning; }) || vsyncFailed)
		return false;
	const int64_t vsync = observedVsync;
	// That vsync has latched every pan issued before it.
	for (int64_t& hidden_since : m_hidden_since_ns) {
		if (hidden_since && hidden_since < vsync)
			hidden_since = 0;
	}
	return m_hidden_since_ns[page] == 0;
}

bool AmlogicFramebufferOutput::waitBackPage() {
	// Standby disables the HDMI clock. Keep the pending page protected and
	// discard output into the existing 1x1 EGL pbuffer until VSync resumes.
	// No new full-size buffer, no guessed retirement and no restart loop.
	if (!pageReady && monotonicNs() - observedVsync.load() > 120000000LL)
		return false;
	const bool ready = active() && waitUntilHidden(m_back_page);
	if (ready != pageReady)
		eDebug("[AmlogicFramebufferOutput] output %s: framebuffer retirement %s", ready ? "resumed" : "deferred", ready ? "confirmed" : "pending");
	pageReady = ready;
	return ready;
}

void AmlogicFramebufferOutput::clearPages() {
	GLint previous_framebuffer = 0;
	glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous_framebuffer);
	glDisable(GL_SCISSOR_TEST);
	glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
	glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
	for (int page = 0; page < m_pages; ++page) {
		glBindFramebuffer(GL_FRAMEBUFFER, m_framebuffers[page]);
		glClear(GL_COLOR_BUFFER_BIT);
	}
	glBindFramebuffer(GL_FRAMEBUFFER, previous_framebuffer);
	if (!waitForGPU())
		eFatal("[AmlogicFramebufferOutput] timed out clearing framebuffer pages");
}

bool AmlogicFramebufferOutput::present(fbClass* fb) {
	if (!active() || !fb || !pageReady)
		return false;

	// The display reads the page as soon as it is panned, so the GPU has to be done with it.
	if (!waitForGPU()) {
		eWarning("[AmlogicFramebufferOutput] GPU completion failed; page not presented");
		return false;
	}
	if (fb->setOffset(m_back_page * m_height) < 0) {
		eDebug("[AmlogicFramebufferOutput] FBIOPAN_DISPLAY to page %d failed: %m", m_back_page);
		return false;
	}
	// The previous page stays on screen until the next vsync, the wait for it is deferred to its next use.
	m_hidden_since_ns[m_shown_page] = monotonicNs();
	m_shown_page = m_back_page;
	m_back_page = (m_back_page + 1) % m_pages;
	return true;
}
