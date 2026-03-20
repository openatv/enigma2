#pragma once

#include <EGL/egl.h>

class INativeWindowProvider {
public:
	virtual ~INativeWindowProvider() = default;

	// Initialisiert das plattformspezifische Windowing-System
	virtual bool init(int width, int height) = 0;

	// Liefert das native Display (z. B. wl_display bei Wayland)
	virtual EGLNativeDisplayType getNativeDisplay() = 0;

	// Liefert das native Fenster (z. B. wl_egl_window bei Wayland)
	virtual EGLNativeWindowType getNativeWindow() = 0;

	// Räumt plattformspezifische Ressourcen auf
	virtual void cleanup() = 0;
};
