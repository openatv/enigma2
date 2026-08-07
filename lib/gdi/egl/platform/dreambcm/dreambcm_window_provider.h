#pragma once

#include <lib/gdi/egl/inative_window_provider.h>

struct DreamBcmNativeWindow
{
	unsigned short width;
	unsigned short height;
};

class DreamBcmWindowProvider : public INativeWindowProvider
{
private:
	DreamBcmNativeWindow m_native_window;
	bool m_use_native_window;

public:
	DreamBcmWindowProvider(int width = 1280, int height = 720);
	virtual ~DreamBcmWindowProvider();

	bool init(int width, int height) override;
	EGLNativeDisplayType getNativeDisplay() override;
	EGLNativeWindowType getNativeWindow() override;
	void cleanup() override;
};
