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
	// Nothing to connect: gEGLDC renders into a pbuffer and copies each frame into the fb0 pages itself.
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
	eDebug("[AmlogicWindowProvider] init %dx%d", width, height);
	return true;
}

EGLNativeDisplayType AmlogicWindowProvider::getNativeDisplay() {
	// Mali EGL opens its display without a native handle.
	return EGL_DEFAULT_DISPLAY;
}

EGLNativeWindowType AmlogicWindowProvider::getNativeWindow() {
	// Unused: no window surface is created for the fb0 output.
	return reinterpret_cast<EGLNativeWindowType>(&m_native_window);
}

void AmlogicWindowProvider::cleanup() {
	// Nothing to release.
}
