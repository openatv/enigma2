#pragma once

#include <EGL/egl.h>
#include <lib/gdi/egl/inative_window_provider.h>

class V3DPlatformWindowProvider : public INativeWindowProvider
{
private:
	EGLNativeDisplayType m_native_display;
	void *m_native_window;
	void *m_platform_handle;
	int m_width;
	int m_height;

	void destroyNativeWindow();
	void unregisterDisplay();
	void setVisible(bool visible);
	bool createNativeWindow(int width, int height);

public:
	V3DPlatformWindowProvider();
	virtual ~V3DPlatformWindowProvider();

	bool init(int width, int height) override;
	bool recreate(int width, int height);
	EGLNativeDisplayType getNativeDisplay() override;
	EGLNativeWindowType getNativeWindow() override;
	void cleanup() override;
};
