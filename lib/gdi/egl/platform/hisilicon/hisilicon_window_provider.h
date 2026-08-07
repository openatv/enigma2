#pragma once

#include <lib/gdi/egl/inative_window_provider.h>

#ifndef HAVE_FBDEV_WINDOW_TYPE
#ifdef HAVE_EGL_FBDEV_WINDOW_H
#include <EGL/fbdev_window.h>
#else
typedef struct fbdev_window {
	unsigned short width;
	unsigned short height;
} fbdev_window;
#endif
#endif

class HisiliconWindowProvider : public INativeWindowProvider {
private:
	fbdev_window m_native_window;

public:
	HisiliconWindowProvider(int width = 1280, int height = 720);
	virtual ~HisiliconWindowProvider();

	bool init(int width, int height) override;
	EGLNativeDisplayType getNativeDisplay() override;
	EGLNativeWindowType getNativeWindow() override;
	void cleanup() override;
};
