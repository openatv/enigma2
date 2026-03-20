#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/sdl/sdl_window_provider.h>


SdlWindowProvider::SdlWindowProvider() : m_window(nullptr), m_native_display(EGL_DEFAULT_DISPLAY), m_native_window(0) {}

SdlWindowProvider::~SdlWindowProvider() {
	cleanup();
}

bool SdlWindowProvider::init(int width, int height) {
	if (SDL_Init(SDL_INIT_VIDEO) < 0) {
		eDebug("[SdlWindowProvider] failed to initialize sdl2: %s", SDL_GetError());
		return false;
	}

	m_window = SDL_CreateWindow("Enigma2 GLES3.0 Debug Window", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, width, height, SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN);

	if (!m_window) {
		eDebug("[SdlWindowProvider] failed to create sdl2 window: %s", SDL_GetError());
		return false;
	}

	if (!extractNativeHandles()) {
		eDebug("[SdlWindowProvider] failed to extract native handles from sdl2 window.");
		return false;
	}

	return true;
}

bool SdlWindowProvider::extractNativeHandles() {
	SDL_SysWMinfo wm_info;
	SDL_VERSION(&wm_info.version);

	if (!SDL_GetWindowWMInfo(m_window, &wm_info)) {
		eDebug("[SdlWindowProvider] SDL_GetWindowWMInfo failed: %s", SDL_GetError());
		return false;
	}

	switch (wm_info.subsystem) {
#if defined(SDL_VIDEO_DRIVER_X11)
		case SDL_SYSWM_X11:
			m_native_display = reinterpret_cast<EGLNativeDisplayType>(wm_info.info.x11.display);
			m_native_window = reinterpret_cast<EGLNativeWindowType>(wm_info.info.x11.window);
			eDebug("[SdlWindowProvider] running on X11");
			return true;
#endif

#if defined(SDL_VIDEO_DRIVER_WAYLAND)
		case SDL_SYSWM_WAYLAND:
			m_native_display = reinterpret_cast<EGLNativeDisplayType>(wm_info.info.wl.display);
			m_native_window = reinterpret_cast<EGLNativeWindowType>(wm_info.info.wl.surface);
			// note: depending on sdl/wayland versions, you might need to wrap the surface into a wl_egl_window here,
			// similar to what we did in the pure wayland provider.
			eDebug("[SdlWindowProvider] running on Wayland");
			return true;
#endif

#if defined(SDL_VIDEO_DRIVER_WINDOWS)
		case SDL_SYSWM_WINDOWS:
			m_native_display = EGL_DEFAULT_DISPLAY; // often sufficient on windows
			m_native_window = reinterpret_cast<EGLNativeWindowType>(wm_info.info.win.window);
			eDebug("[SdlWindowProvider] running on Windows");
			return true;
#endif

		default:
			eDebug("[SdlWindowProvider] unsupported sdl subsystem target: %d", wm_info.subsystem);
			return false;
	}
}

EGLNativeDisplayType SdlWindowProvider::getNativeDisplay() {
	return m_native_display;
}

EGLNativeWindowType SdlWindowProvider::getNativeWindow() {
	return m_native_window;
}

void SdlWindowProvider::cleanup() {
	if (m_window) {
		SDL_DestroyWindow(m_window);
		m_window = nullptr;
	}
	SDL_QuitSubSystem(SDL_INIT_VIDEO);
}