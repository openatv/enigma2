#pragma once

#include <EGL/fbdev_window.h>
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
