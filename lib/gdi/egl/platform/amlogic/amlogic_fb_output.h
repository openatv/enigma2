#pragma once

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <cstdint>

class fbClass;

// Renders straight into the OSD framebuffer pages: every page of fb0 is
// imported from the OSD dma-buf as an EGLImage and bound to its own FBO.
class AmlogicFramebufferOutput {
public:
	static const int MAX_PAGES = 3;

	AmlogicFramebufferOutput() = default;
	~AmlogicFramebufferOutput();
	AmlogicFramebufferOutput(const AmlogicFramebufferOutput&) = delete;
	AmlogicFramebufferOutput& operator=(const AmlogicFramebufferOutput&) = delete;

	// Needs a current GL context.
	bool create(EGLDisplay display, int width, int height);
	void destroy();

	bool active() const { return m_pages > 0; }
	int pages() const { return m_pages; }
	GLuint backFramebuffer() const { return active() ? m_framebuffers[m_back_page] : 0; }

	// Block until the page is no longer scanned out, which only happens when the pan away from it is younger than one vsync.
	void waitBackPage() {
		if (active())
			waitUntilHidden(m_back_page);
	}

	void clearPages();
	// Waits for the GPU, shows the back page and moves on to the next one.
	bool present(fbClass* fb);

private:
	// Longest vsync period of any output mode (23.976 Hz) plus some slack.
	static const int64_t MAX_VSYNC_PERIOD_NS = 43000000;
	static const int64_t VSYNC_MARGIN_NS = 2000000;

	void waitUntilHidden(int page);

	EGLDisplay m_display = EGL_NO_DISPLAY;
	int m_fb_fd = -1;
	int m_dmabuf_fd = -1;
	int m_pages = 0;
	int m_back_page = 0;
	int m_shown_page = 0;
	int m_height = 0;
	int64_t m_vsync_period_ns = 0;
	int64_t m_last_vsync_ns = 0;
	// Time of the pan that hid the page, 0 once a vsync has latched it.
	int64_t m_hidden_since_ns[MAX_PAGES] = {};
	EGLImageKHR m_images[MAX_PAGES] = {};
	GLuint m_textures[MAX_PAGES] = {};
	GLuint m_framebuffers[MAX_PAGES] = {};
};
