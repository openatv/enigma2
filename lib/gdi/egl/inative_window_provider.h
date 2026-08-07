#pragma once

#include <EGL/egl.h>

class INativeWindowProvider {
public:
	virtual ~INativeWindowProvider() = default;

	// Initializes the platform windowing system.
	virtual bool init(int width, int height) = 0;

	// Returns the native display (e.g. wl_display on Wayland).
	virtual EGLNativeDisplayType getNativeDisplay() = 0;

	// Returns the native window (e.g. wl_egl_window on Wayland).
	virtual EGLNativeWindowType getNativeWindow() = 0;

	// Releases the platform resources.
	virtual void cleanup() = 0;
};
