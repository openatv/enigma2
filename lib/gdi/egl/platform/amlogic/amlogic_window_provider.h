#pragma once

#ifdef HAVE_EGL_FBDEV_WINDOW_H
#include <EGL/fbdev_window.h>
#else
typedef struct fbdev_window {
	unsigned short width;
	unsigned short height;
} fbdev_window;
#endif
#include <lib/gdi/egl/inative_window_provider.h>

class AmlogicWindowProvider : public INativeWindowProvider {
private:
	fbdev_window m_native_window;

public:
	AmlogicWindowProvider(int width = 1920, int height = 1080);
	virtual ~AmlogicWindowProvider();

	// INativeWindowProvider
	bool init(int width, int height) override;
	EGLNativeDisplayType getNativeDisplay() override;
	EGLNativeWindowType getNativeWindow() override;
	void cleanup() override;
};
