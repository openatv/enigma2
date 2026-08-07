#pragma once

#include <lib/gdi/egl/inative_window_provider.h>
#include <eglvuplus.h>

class VuplusMipsWindowProvider : public INativeWindowProvider {
private:
	EGLNativeDisplayType m_native_display;
	void *m_native_window;
	VUGLES_PlatformHandle m_platform_handle;
	int m_client_id;
	bool m_platform_initialized;
	bool m_registered;
	int m_width;
	int m_height;

	bool initPlatform(int width, int height);
	bool registerDisplay(int width, int height);
	void updateWindowGeometry(int width, int height);
	void destroyNativeWindow();
	void unregisterDisplay();
	void termPlatform();

public:
	VuplusMipsWindowProvider();
	virtual ~VuplusMipsWindowProvider();

	bool init(int width, int height) override;
	EGLNativeDisplayType getNativeDisplay() override;
	EGLNativeWindowType getNativeWindow() override;
	void cleanup() override;
};
