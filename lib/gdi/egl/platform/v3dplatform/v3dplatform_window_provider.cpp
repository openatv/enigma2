#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/v3dplatform/v3dplatform_window_provider.h>

#include <stdint.h>

extern "C" {
typedef void *V3D_PlatformHandle;

typedef struct
{
	uint32_t width;
	uint32_t height;
	uint32_t x;
	uint32_t y;
	bool stretch;
	uint32_t clientID;
	uint32_t zOrder;
} V3D_NativeWindowInfo;

void V3D_RegisterDisplayPlatform(V3D_PlatformHandle *handle, void *display);
void V3D_UnregisterDisplayPlatform(V3D_PlatformHandle handle);
void *V3D_CreateNativeWindow(const V3D_NativeWindowInfo *info);
void V3D_DestroyNativeWindow(void *nativeWin);
bool V3D_SetVisible(V3D_PlatformHandle handle, bool visible);
}

static void fillNativeWindowInfo(V3D_NativeWindowInfo &native_window, int width, int height)
{
	native_window.x = 0;
	native_window.y = 0;
	native_window.width = width;
	native_window.height = height;
	native_window.stretch = false;
	native_window.clientID = 0;
	native_window.zOrder = 0;
}

V3DPlatformWindowProvider::V3DPlatformWindowProvider()
	: m_native_display(EGL_DEFAULT_DISPLAY),
	  m_native_window(nullptr),
	  m_platform_handle(nullptr),
	  m_width(0),
	  m_height(0)
{
}

V3DPlatformWindowProvider::~V3DPlatformWindowProvider()
{
	cleanup();
}

bool V3DPlatformWindowProvider::init(int width, int height)
{
	if (!m_platform_handle)
	{
		V3D_RegisterDisplayPlatform((V3D_PlatformHandle *)&m_platform_handle, (void *)m_native_display);
		if (!m_platform_handle)
		{
			eDebug("[V3DPlatformWindowProvider] failed to register V3D display");
			return false;
		}
		eDebug("[V3DPlatformWindowProvider] registered V3D display handle=%p", m_platform_handle);
	}

	if (m_native_window && m_width == width && m_height == height)
	{
		setVisible(true);
		eDebug("[V3DPlatformWindowProvider] reuse V3D native window %p for %dx%d", m_native_window, width, height);
		return true;
	}

	if (m_native_window)
		destroyNativeWindow();

	return createNativeWindow(width, height);
}

bool V3DPlatformWindowProvider::recreate(int width, int height)
{
	eDebug("[V3DPlatformWindowProvider] recreate V3D native window for %dx%d", width, height);
	if (m_native_window)
		destroyNativeWindow();
	return init(width, height);
}

bool V3DPlatformWindowProvider::createNativeWindow(int width, int height)
{
	V3D_NativeWindowInfo native_window;
	fillNativeWindowInfo(native_window, width, height);
	m_native_window = V3D_CreateNativeWindow(&native_window);
	if (!m_native_window)
	{
		eDebug("[V3DPlatformWindowProvider] failed to create V3D native window for %dx%d", width, height);
		return false;
	}
	eDebug("[V3DPlatformWindowProvider] V3D native window %p for %dx%d stretch=%d", m_native_window, width, height, native_window.stretch ? 1 : 0);
	setVisible(true);

	m_width = width;
	m_height = height;
	return true;
}

EGLNativeDisplayType V3DPlatformWindowProvider::getNativeDisplay()
{
	return m_native_display;
}

EGLNativeWindowType V3DPlatformWindowProvider::getNativeWindow()
{
	return (EGLNativeWindowType)m_native_window;
}

void V3DPlatformWindowProvider::destroyNativeWindow()
{
	if (!m_native_window)
		return;

	setVisible(false);
	eDebug("[V3DPlatformWindowProvider] destroy V3D native window %p", m_native_window);
	V3D_DestroyNativeWindow(m_native_window);
	m_native_window = nullptr;
}

void V3DPlatformWindowProvider::unregisterDisplay()
{
	if (!m_platform_handle)
		return;

	eDebug("[V3DPlatformWindowProvider] unregister V3D display handle=%p", m_platform_handle);
	V3D_UnregisterDisplayPlatform((V3D_PlatformHandle)m_platform_handle);
	m_platform_handle = nullptr;
}

void V3DPlatformWindowProvider::setVisible(bool visible)
{
	if (!m_platform_handle)
		return;

	if (!V3D_SetVisible((V3D_PlatformHandle)m_platform_handle, visible))
		eDebug("[V3DPlatformWindowProvider] V3D_SetVisible(%d) native=0 failed", visible ? 1 : 0);
	else
		eDebug("[V3DPlatformWindowProvider] V3D_SetVisible(%d) native=0", visible ? 1 : 0);
}

void V3DPlatformWindowProvider::cleanup()
{
	eDebug("[V3DPlatformWindowProvider] skip V3D platform teardown at process shutdown native=%p display=%p",
		m_native_window, m_platform_handle);
	m_native_window = nullptr;
	m_platform_handle = nullptr;
	m_width = 0;
	m_height = 0;
}
