#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/dreambcm/dreambcm_window_provider.h>

#include <stdlib.h>
#include <string.h>
#include <strings.h>

static bool dreamBcmUseNativeWindow()
{
	const char *env = getenv("E2EGL_DREAMBCM_WINDOW");
	if (!env || !*env)
		return false;

	return !(!strcmp(env, "0") || !strcasecmp(env, "none") || !strcasecmp(env, "null"));
}

DreamBcmWindowProvider::DreamBcmWindowProvider(int width, int height)
	: m_use_native_window(dreamBcmUseNativeWindow())
{
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
}

DreamBcmWindowProvider::~DreamBcmWindowProvider()
{
	cleanup();
}

bool DreamBcmWindowProvider::init(int width, int height)
{
	m_native_window.width = static_cast<unsigned short>(width);
	m_native_window.height = static_cast<unsigned short>(height);
	eDebug("[DreamBcmWindowProvider] init %dx%d native_window=%s", width, height, m_use_native_window ? "fbdev" : "default");
	return true;
}

EGLNativeDisplayType DreamBcmWindowProvider::getNativeDisplay()
{
	return EGL_DEFAULT_DISPLAY;
}

EGLNativeWindowType DreamBcmWindowProvider::getNativeWindow()
{
	if (!m_use_native_window)
		return (EGLNativeWindowType)0;

	return reinterpret_cast<EGLNativeWindowType>(&m_native_window);
}

void DreamBcmWindowProvider::cleanup()
{
}
