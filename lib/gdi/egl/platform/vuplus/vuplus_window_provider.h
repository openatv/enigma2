#pragma once

#include <lib/gdi/egl/inative_window_provider.h>

class VuplusWindowProvider : public INativeWindowProvider {
private:
	EGLNativeDisplayType m_native_display;
	void *m_native_window;
	void *m_nxpl_handle;
	bool m_joined;
	bool m_registered;
	int m_width;
	int m_height;

	bool joinPlatform();
	bool registerDisplay();
	void destroyNativeWindow();
	void unregisterDisplay();
	void leavePlatform();

public:
	VuplusWindowProvider();
	virtual ~VuplusWindowProvider();

	bool init(int width, int height) override;
	bool suspend();
	EGLNativeDisplayType getNativeDisplay() override;
	EGLNativeWindowType getNativeWindow() override;
	void cleanup() override;
};
