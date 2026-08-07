#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/vuplus/vuplus_window_provider.h>

#include <cstdlib>
#include <stdint.h>

extern "C" {
typedef unsigned NEXUS_Error;
typedef void *NEXUS_DISPLAYHANDLE;
typedef void *NXPL_PlatformHandle;

typedef enum
{
	NEXUS_BlendFactor_eZero
} NEXUS_BlendFactor;

typedef struct
{
	NEXUS_BlendFactor a;
	NEXUS_BlendFactor b;
	bool subtract_cd;
	NEXUS_BlendFactor c;
	NEXUS_BlendFactor d;
	bool subtract_e;
	NEXUS_BlendFactor e;
} NEXUS_BlendEquation;

typedef struct
{
	uint32_t width;
	uint32_t height;
	uint32_t x;
	uint32_t y;
	bool stretch;
	uint32_t clientID;
	uint32_t zOrder;
	NEXUS_BlendEquation colorBlend;
	NEXUS_BlendEquation alphaBlend;
	uint32_t magic;
} NXPL_NativeWindowInfoEXT;

void NXPL_RegisterNexusDisplayPlatform(NXPL_PlatformHandle *handle, NEXUS_DISPLAYHANDLE display);
void NXPL_UnregisterNexusDisplayPlatform(NXPL_PlatformHandle handle);
void NXPL_GetDefaultNativeWindowInfoEXT(NXPL_NativeWindowInfoEXT *info);
void *NXPL_CreateNativeWindowEXT(const NXPL_NativeWindowInfoEXT *info);
void NXPL_DestroyNativeWindow(void *nativeWin);
NEXUS_Error NxClient_Join(const void *settings);
void NxClient_Uninit(void);
}

static bool vuplusUninitNexusClient()
{
	const char *env = getenv("E2EGL_VUPLUS_UNINIT_NEXUS");
	return env && *env && *env != '0';
}

static bool vuplusReleaseNexusResources()
{
	const char *env = getenv("E2EGL_VUPLUS_RELEASE_NXPL");
	return env && *env && *env != '0';
}

static void fillNativeWindowInfo(NXPL_NativeWindowInfoEXT &native_window, int width, int height)
{
	NXPL_GetDefaultNativeWindowInfoEXT(&native_window);
	native_window.x = 0;
	native_window.y = 0;
	native_window.width = width;
	native_window.height = height;
	native_window.stretch = true;
	native_window.clientID = 0;
	native_window.zOrder = 0;
}

VuplusWindowProvider::VuplusWindowProvider()
	: m_native_display(EGL_DEFAULT_DISPLAY),
	  m_native_window(nullptr),
	  m_nxpl_handle(nullptr),
	  m_joined(false),
	  m_registered(false),
	  m_width(0),
	  m_height(0)
{
}

VuplusWindowProvider::~VuplusWindowProvider()
{
	cleanup();
}

bool VuplusWindowProvider::joinPlatform()
{
	if (m_joined)
		return true;

	NEXUS_Error err = NxClient_Join(nullptr);
	if (err)
	{
		eDebug("[VuplusWindowProvider] NxClient_Join failed: %u", err);
		return false;
	}

	m_joined = true;
	eDebug("[VuplusWindowProvider] joined Nexus client");
	return true;
}

bool VuplusWindowProvider::registerDisplay()
{
	if (m_registered)
		return true;

	if (!joinPlatform())
		return false;

	NXPL_RegisterNexusDisplayPlatform((NXPL_PlatformHandle *)&m_nxpl_handle, nullptr);
	m_registered = true;
	eDebug("[VuplusWindowProvider] registered NXPL display handle=%p", m_nxpl_handle);
	return true;
}

void VuplusWindowProvider::destroyNativeWindow()
{
	if (!m_native_window)
		return;

	eDebug("[VuplusWindowProvider] destroy NXPL native window %p", m_native_window);
	NXPL_DestroyNativeWindow(m_native_window);
	m_native_window = nullptr;
}

void VuplusWindowProvider::unregisterDisplay()
{
	if (!m_registered)
		return;

	eDebug("[VuplusWindowProvider] unregister NXPL display handle=%p", m_nxpl_handle);
	NXPL_UnregisterNexusDisplayPlatform((NXPL_PlatformHandle)m_nxpl_handle);
	m_nxpl_handle = nullptr;
	m_registered = false;
}

void VuplusWindowProvider::leavePlatform()
{
	if (!m_joined)
		return;

	if (vuplusUninitNexusClient())
	{
		eDebug("[VuplusWindowProvider] leave Nexus client");
		NxClient_Uninit();
	}
	else
	{
		eDebug("[VuplusWindowProvider] keep Nexus client joined to avoid late shutdown crash");
	}
	m_joined = false;
}

bool VuplusWindowProvider::init(int width, int height)
{
	if (!registerDisplay())
		return false;

	NXPL_NativeWindowInfoEXT native_window;
	fillNativeWindowInfo(native_window, width, height);

	if (m_native_window)
	{
		if (m_width == width && m_height == height)
			return true;

		eDebug("[VuplusWindowProvider] recreate NXPL native window %p: %dx%d -> %dx%d",
			m_native_window, m_width, m_height, width, height);
		destroyNativeWindow();
	}

	m_native_window = NXPL_CreateNativeWindowEXT(&native_window);
	if (!m_native_window)
	{
		eDebug("[VuplusWindowProvider] failed to create NXPL native window for %dx%d", width, height);
		return false;
	}

	m_width = width;
	m_height = height;
	eDebug("[VuplusWindowProvider] NXPL native window %p for %dx%d stretch=%d", m_native_window, width, height, native_window.stretch ? 1 : 0);
	return true;
}

bool VuplusWindowProvider::suspend()
{
	destroyNativeWindow();
	return m_native_window == nullptr;
}

EGLNativeDisplayType VuplusWindowProvider::getNativeDisplay()
{
	return m_native_display;
}

EGLNativeWindowType VuplusWindowProvider::getNativeWindow()
{
	return (EGLNativeWindowType)m_native_window;
}

void VuplusWindowProvider::cleanup()
{
	if (!vuplusReleaseNexusResources())
	{
		eDebug("[VuplusWindowProvider] skip NXPL teardown at process shutdown native=%p display=%p joined=%d registered=%d",
			m_native_window, m_nxpl_handle, m_joined ? 1 : 0, m_registered ? 1 : 0);
		m_native_window = nullptr;
		m_nxpl_handle = nullptr;
		m_joined = false;
		m_registered = false;
		m_width = 0;
		m_height = 0;
		return;
	}

	destroyNativeWindow();
	unregisterDisplay();
	leavePlatform();
	m_width = 0;
	m_height = 0;
}
