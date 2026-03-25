#pragma once

#include <SDL2/SDL.h>
#include <SDL2/SDL_syswm.h>
#include <lib/gdi/inative_window_provider.h>

class SdlWindowProvider : public INativeWindowProvider {
private:
	SDL_Window* m_window;

	EGLNativeDisplayType m_native_display;
	EGLNativeWindowType m_native_window;

	bool extractNativeHandles();

public:
	SdlWindowProvider();
	virtual ~SdlWindowProvider();

	bool init(int width, int height) override;
	EGLNativeDisplayType getNativeDisplay() override;
	EGLNativeWindowType getNativeWindow() override;
	void cleanup() override;

	// optional: access to the sdl window to handle events (keyboard, mouse) later
	SDL_Window* getSdlWindow() const { return m_window; }
};