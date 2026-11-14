#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/dreambcm/dreambcm_window_provider.h>

#include <stdlib.h>
#include <string.h>
#include <strings.h>

#ifdef HWDM7435
#include <dlfcn.h>
#include <map>
#include <mutex>

namespace {
BEGL_DisplayInterface originalDisplayInterface;
std::map<BEGL_BufferHandle, void*> swapchainBuffers;
std::mutex swapchainMutex;

BEGL_BufferHandle dreamBcmBufferGet(void *context, BEGL_BufferSettings *settings)
{
	BEGL_BufferHandle buffer = originalDisplayInterface.BufferGet(context, settings);
	if (buffer) {
		std::lock_guard<std::mutex> lock(swapchainMutex);
		swapchainBuffers[buffer] = settings->windowState.platformState;
	}
	return buffer;
}

BEGL_Error dreamBcmBufferDestroy(void *context, BEGL_BufferDisplayState *state)
{
	{
		std::lock_guard<std::mutex> lock(swapchainMutex);
		auto found = swapchainBuffers.find(state->buffer);
		if (found != swapchainBuffers.end() && found->second == state->windowState.platformState)
			return BEGL_Success;
	}
	return originalDisplayInterface.BufferDestroy(context, state);
}

BEGL_Error dreamBcmWindowDestroy(void *state)
{
	BEGL_Error result = originalDisplayInterface.WindowPlatformStateDestroy(state);
	if (result == BEGL_Success) {
		std::lock_guard<std::mutex> lock(swapchainMutex);
		size_t released = 0;
		for (auto entry = swapchainBuffers.begin(); entry != swapchainBuffers.end();) {
			if (entry->second == state) {
				entry = swapchainBuffers.erase(entry);
				++released;
			} else
				++entry;
		}
		eDebug("[DreamBcmWindowProvider] window released %zu borrowed swapchain buffer(s)", released);
	}
	return result;
}
}
#endif

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

bool DreamBcmWindowProvider::prepareEGL()
{
#ifdef HWDM7435
	// The legacy V3D driver calls BufferDestroy for buffers returned by BufferGet.
	// libvc5dream's BufferDestroy only owns pixmaps and asserts on swapchain buffers.
	// Track those borrowed handles; their owner is WindowPlatformStateDestroy.
	void *library = dlopen("libv3ddriver.so", RTLD_LAZY | RTLD_NOLOAD);
	if (!library) {
		eDebug("[DreamBcmWindowProvider] V3D driver is not loaded after EGL initialization");
		return false;
	}
	auto getInterfaces = reinterpret_cast<BEGL_DriverInterfaces *(*)()>(dlsym(library, "BEGL_GetDriverInterfaces"));
	BEGL_DriverInterfaces *interfaces = getInterfaces ? getInterfaces() : nullptr;
	dlclose(library);
	if (!interfaces || !interfaces->displayInterface) {
		eDebug("[DreamBcmWindowProvider] V3D display interface unavailable");
		return false;
	}
	BEGL_DisplayInterface *display = interfaces->displayInterface;
	if (display->BufferGet == dreamBcmBufferGet && display->BufferDestroy == dreamBcmBufferDestroy &&
		display->WindowPlatformStateDestroy == dreamBcmWindowDestroy)
		return true;
	if (!display->BufferGet || !display->BufferDestroy || !display->WindowPlatformStateDestroy) {
		eDebug("[DreamBcmWindowProvider] incomplete V3D buffer ownership interface");
		return false;
	}
	originalDisplayInterface = *display;
	display->BufferGet = dreamBcmBufferGet;
	display->BufferDestroy = dreamBcmBufferDestroy;
	display->WindowPlatformStateDestroy = dreamBcmWindowDestroy;
	eDebug("[DreamBcmWindowProvider] BCM7435 swapchain ownership compatibility enabled");
#endif
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
