#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/amlogic/amlogic_window_provider.h>

AmlogicWindowProvider::AmlogicWindowProvider(int width, int height) {
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
}

AmlogicWindowProvider::~AmlogicWindowProvider() {
	// nothing to tear down: fbdev_window is stack-allocated
}

bool AmlogicWindowProvider::init(int width, int height) {
	// The Amlogic/Mali-fbdev backend needs no display connection or
	// surface object — the kernel driver opens the fbdev node by itself.
	// We simply record the requested dimensions and return success.
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
	eDebug("[AmlogicWindowProvider] init %dx%d", width, height);
	return true;
}

EGLNativeDisplayType AmlogicWindowProvider::getNativeDisplay() {
	// Mali fbdev EGL resolves the display internally from the fbdev node.
	// EGL_DEFAULT_DISPLAY is the correct value here.
	return EGL_DEFAULT_DISPLAY;
}

EGLNativeWindowType AmlogicWindowProvider::getNativeWindow() {
	// Mali fbdev EGL expects a pointer to the fbdev_window struct.
	return reinterpret_cast<EGLNativeWindowType>(&m_native_window);
}

void AmlogicWindowProvider::cleanup() {
	// Nothing to release: no display connection, no allocated surface.
}
