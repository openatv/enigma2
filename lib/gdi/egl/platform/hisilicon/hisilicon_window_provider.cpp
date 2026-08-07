#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/hisilicon/hisilicon_window_provider.h>

HisiliconWindowProvider::HisiliconWindowProvider(int width, int height) {
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
}

HisiliconWindowProvider::~HisiliconWindowProvider() {
}

bool HisiliconWindowProvider::init(int width, int height) {
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
	eDebug("[HisiliconWindowProvider] init %dx%d", width, height);
	return true;
}

EGLNativeDisplayType HisiliconWindowProvider::getNativeDisplay() {
	return EGL_DEFAULT_DISPLAY;
}

EGLNativeWindowType HisiliconWindowProvider::getNativeWindow() {
	return reinterpret_cast<EGLNativeWindowType>(&m_native_window);
}

void HisiliconWindowProvider::cleanup() {
}
