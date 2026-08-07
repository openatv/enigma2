#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/vuplus_mips/vuplus_mips_window_provider.h>

static void fillNativeWindowInfo(VUGLES_NativeWindowInfo &native_window, int width, int height)
{
	VUGLES_GetDefaultNativeWindowInfo(&native_window);
	native_window.width = width;
	native_window.height = height;
	native_window.x = 0;
	native_window.y = 0;
	native_window.stretch = true;
	native_window.clientID = 0;
	native_window.zOrder = 0;
}

VuplusMipsWindowProvider::VuplusMipsWindowProvider()
	: m_native_display(EGL_DEFAULT_DISPLAY),
	  m_native_window(nullptr),
	  m_platform_handle(nullptr),
	  m_client_id(0),
	  m_platform_initialized(false),
	  m_registered(false),
	  m_width(0),
	  m_height(0)
{
}

VuplusMipsWindowProvider::~VuplusMipsWindowProvider()
{
	cleanup();
}

bool VuplusMipsWindowProvider::initPlatform(int width, int height)
{
	if (m_platform_initialized)
		return true;

	float aspect = 1.0f;
	vuInitResult result = VUGLES_InitPlatformAndDefaultDisplay("Enigma2", &aspect, width, height);
	if (result != vuInitSuccess)
	{
		eDebug("[VuplusMipsWindowProvider] VUGLES_InitPlatformAndDefaultDisplay failed: %d", (int)result);
		return false;
	}

	m_platform_initialized = true;
	eDebug("[VuplusMipsWindowProvider] VUGLES platform initialised for %dx%d aspect=%f", width, height, aspect);
	return true;
}

bool VuplusMipsWindowProvider::registerDisplay(int width, int height)
{
	if (m_registered)
		return true;

	if (!initPlatform(width, height))
		return false;

	VUGLES_RegisterDisplayPlatform(&m_platform_handle);
	if (!m_platform_handle)
	{
		eDebug("[VuplusMipsWindowProvider] failed to register VUGLES display");
		return false;
	}

	m_registered = true;
	eDebug("[VuplusMipsWindowProvider] registered VUGLES display handle=%p", m_platform_handle);
	return true;
}

bool VuplusMipsWindowProvider::init(int width, int height)
{
	if (!registerDisplay(width, height))
		return false;

	VUGLES_NativeWindowInfo native_window;
	fillNativeWindowInfo(native_window, width, height);

	if (m_native_window)
	{
		if (width == m_width && height == m_height)
		{
			eDebug("[VuplusMipsWindowProvider] keeping VUGLES native window %p client=%d for unchanged %dx%d",
				m_native_window, m_client_id, width, height);
			return true;
		}
		native_window.clientID = m_client_id;
		VUGLES_UpdateNativeWindow(m_native_window, &native_window);
		m_width = width;
		m_height = height;
		updateWindowGeometry(width, height);
		eDebug("[VuplusMipsWindowProvider] updated VUGLES native window %p client=%d for %dx%d stretch=%d",
			m_native_window, m_client_id, width, height, native_window.stretch ? 1 : 0);
		return true;
	}

	m_native_window = VUGLES_CreateNativeWindow(&native_window);
	if (!m_native_window)
	{
		eDebug("[VuplusMipsWindowProvider] failed to create VUGLES native window for %dx%d", width, height);
		return false;
	}

	m_client_id = VUGLES_GetClientID(m_native_window);
	m_width = width;
	m_height = height;
	updateWindowGeometry(width, height);
	eDebug("[VuplusMipsWindowProvider] VUGLES native window %p client=%d for %dx%d stretch=%d", m_native_window, m_client_id, width, height, native_window.stretch ? 1 : 0);
	return true;
}

EGLNativeDisplayType VuplusMipsWindowProvider::getNativeDisplay()
{
	return m_native_display;
}

EGLNativeWindowType VuplusMipsWindowProvider::getNativeWindow()
{
	return (EGLNativeWindowType)m_native_window;
}

void VuplusMipsWindowProvider::updateWindowGeometry(int width, int height)
{
	if (!m_client_id)
		return;

	vuRect rect;
	rect.x = 0;
	rect.y = 0;
	rect.width = (uint16_t)width;
	rect.height = (uint16_t)height;
	VUGLES_SetPosition(m_client_id, rect, true);
}

void VuplusMipsWindowProvider::destroyNativeWindow()
{
	if (!m_native_window)
		return;

	eDebug("[VuplusMipsWindowProvider] destroy VUGLES native window %p client=%d", m_native_window, m_client_id);
	VUGLES_DestroyNativeWindow(m_native_window);
	m_native_window = nullptr;
	m_client_id = 0;
}

void VuplusMipsWindowProvider::unregisterDisplay()
{
	if (!m_registered)
		return;

	eDebug("[VuplusMipsWindowProvider] unregister VUGLES display handle=%p", m_platform_handle);
	VUGLES_UnregisterDisplayPlatform(m_platform_handle);
	m_platform_handle = nullptr;
	m_registered = false;
}

void VuplusMipsWindowProvider::termPlatform()
{
	if (!m_platform_initialized)
		return;

	eDebug("[VuplusMipsWindowProvider] terminate VUGLES platform");
	VUGLES_TermPlatform();
	m_platform_initialized = false;
}

void VuplusMipsWindowProvider::cleanup()
{
	destroyNativeWindow();
	unregisterDisplay();
	termPlatform();
	m_width = 0;
	m_height = 0;
}
