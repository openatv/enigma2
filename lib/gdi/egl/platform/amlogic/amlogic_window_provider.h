#pragma once

#include <lib/gdi/egl/inative_window_provider.h>

// Standard Mali fbdev window structure used on Amlogic fbdev platforms.
// The Mali kernel driver resolves the display from the fbdev node itself,
// so no wl_display / X Display handle is needed here.
struct fbdev_window {
	unsigned short width;
	unsigned short height;
};

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
