#include <lib/base/eerror.h>
#include <lib/base/modelinformation.h>
#include <lib/gdi/egl/platform/nxpl/nxpl_window_provider.h>

#include <cstdlib>
#include <dlfcn.h>
#include <fstream>
#include <stdint.h>
#include <string.h>
#include <string>

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
int NEXUS_Platform_AuthenticatedJoin(const void *settings);
}

typedef NEXUS_Error (*NxClientJoinProc)(const void *settings);
typedef void (*NxClientUninitProc)(void);
typedef void (*NxplUpdateNativeWindowProc)(void *nativeWin, NXPL_NativeWindowInfoEXT *info);
typedef void (*NxplShowNativeWindowProc)(void *nativeWin, bool show);

static NxClientJoinProc nxClientJoinProc()
{
	return (NxClientJoinProc)dlsym(RTLD_DEFAULT, "NxClient_Join");
}

static NxClientUninitProc nxClientUninitProc()
{
	return (NxClientUninitProc)dlsym(RTLD_DEFAULT, "NxClient_Uninit");
}

static NxplUpdateNativeWindowProc nxplUpdateNativeWindowProc()
{
	return (NxplUpdateNativeWindowProc)dlsym(RTLD_DEFAULT, "NXPL_UpdateNativeWindowEXT");
}

static NxplShowNativeWindowProc nxplShowNativeWindowProc()
{
	return (NxplShowNativeWindowProc)dlsym(RTLD_DEFAULT, "NXPL_ShowNativeWindowEXT");
}

static std::string nxplReadTextFile(const char *filename)
{
	std::ifstream file(filename);
	std::string value;
	if (file.good())
		std::getline(file, value);
	return value;
}

static bool nxplNeedsLegacyWindowHandling(const std::string &value)
{
	return value == "hd2400" || value == "mutant2400" || value == "quadbox2400" ||
	       value == "triplex" ||
	       value == "et10000" ||
	       value == "formuler1" || value == "formuler1tc" || value == "f1";
}

static bool nxplNeedsLegacyWindowHandling()
{
	const std::string machine = eModelInformation::getInstance().getValue("machinebuild");
	const std::string boxtype = nxplReadTextFile("/proc/stb/info/boxtype");
	return nxplNeedsLegacyWindowHandling(machine) || nxplNeedsLegacyWindowHandling(boxtype);
}

static bool nxplForceNativeWindowRefresh()
{
	return nxplNeedsLegacyWindowHandling();
}

static bool nxplUseStretch()
{
	return !nxplNeedsLegacyWindowHandling();
}

static bool nxplUninitNexusClient()
{
	const char *env = getenv("E2EGL_NXPL_UNINIT_NEXUS");
	return env && *env && *env != '0';
}

static bool nxplReleaseNexusResources()
{
	const char *env = getenv("E2EGL_NXPL_RELEASE_NXPL");
	return env && *env && *env != '0';
}

static void fillNativeWindowInfo(NXPL_NativeWindowInfoEXT &native_window, int width, int height)
{
	NXPL_GetDefaultNativeWindowInfoEXT(&native_window);
	native_window.x = 0;
	native_window.y = 0;
	native_window.width = width;
	native_window.height = height;
	native_window.stretch = nxplUseStretch();
	native_window.clientID = 0;
	native_window.zOrder = 0;
}

NxplWindowProvider::NxplWindowProvider()
	: m_native_display(EGL_DEFAULT_DISPLAY),
	  m_native_window(nullptr),
	  m_nxpl_handle(nullptr),
	  m_joined(false),
	  m_joined_with_nxclient(false),
	  m_registered(false),
	  m_width(0),
	  m_height(0)
{
}

NxplWindowProvider::~NxplWindowProvider()
{
	cleanup();
}

bool NxplWindowProvider::joinPlatform()
{
	if (m_joined)
		return true;

	if (NxClientJoinProc join = nxClientJoinProc())
	{
		NEXUS_Error err = join(nullptr);
		if (!err)
		{
			m_joined = true;
			m_joined_with_nxclient = true;
			eDebug("[NxplWindowProvider] joined Nexus client via NxClient");
			return true;
		}
		eDebug("[NxplWindowProvider] NxClient_Join failed: %u, trying NEXUS join", err);
	}

	int err = NEXUS_Platform_AuthenticatedJoin(nullptr);
	if (err)
	{
		eDebug("[NxplWindowProvider] NEXUS platform join failed: %d", err);
		return false;
	}

	m_joined = true;
	m_joined_with_nxclient = false;
	eDebug("[NxplWindowProvider] joined Nexus platform");
	return true;
}

bool NxplWindowProvider::registerDisplay()
{
	if (m_registered)
		return true;

	if (!joinPlatform())
		return false;

	NXPL_RegisterNexusDisplayPlatform((NXPL_PlatformHandle *)&m_nxpl_handle, nullptr);
	m_registered = true;
	eDebug("[NxplWindowProvider] registered NXPL display handle=%p", m_nxpl_handle);
	return true;
}

bool NxplWindowProvider::init(int width, int height)
{
	if (!registerDisplay())
		return false;

	NXPL_NativeWindowInfoEXT native_window;
	fillNativeWindowInfo(native_window, width, height);

	if (m_native_window)
	{
		if (m_width != width || m_height != height || nxplForceNativeWindowRefresh())
			destroyNativeWindow();
		else if (NxplUpdateNativeWindowProc update = nxplUpdateNativeWindowProc())
		{
			update(m_native_window, &native_window);
			m_width = width;
			m_height = height;
			eDebug("[NxplWindowProvider] updated NXPL native window %p for %dx%d stretch=%d",
				m_native_window, width, height, native_window.stretch ? 1 : 0);
			return true;
		}
	}

	if (!m_native_window)
	{
		m_native_window = NXPL_CreateNativeWindowEXT(&native_window);
		if (!m_native_window)
		{
			eDebug("[NxplWindowProvider] failed to create NXPL native window for %dx%d", width, height);
			return false;
		}
		if (NxplShowNativeWindowProc show = nxplShowNativeWindowProc())
			show(m_native_window, true);
		eDebug("[NxplWindowProvider] NXPL native window %p for %dx%d stretch=%d", m_native_window, width, height, native_window.stretch ? 1 : 0);
	}

	m_width = width;
	m_height = height;
	return true;
}

bool NxplWindowProvider::suspend()
{
	destroyNativeWindow();
	return m_native_window == nullptr;
}

EGLNativeDisplayType NxplWindowProvider::getNativeDisplay()
{
	return m_native_display;
}

EGLNativeWindowType NxplWindowProvider::getNativeWindow()
{
	return (EGLNativeWindowType)m_native_window;
}

void NxplWindowProvider::destroyNativeWindow()
{
	if (!m_native_window)
		return;

	eDebug("[NxplWindowProvider] destroy NXPL native window %p", m_native_window);
	if (NxplShowNativeWindowProc show = nxplShowNativeWindowProc())
		show(m_native_window, false);
	NXPL_DestroyNativeWindow(m_native_window);
	m_native_window = nullptr;
}

void NxplWindowProvider::unregisterDisplay()
{
	if (!m_registered)
		return;

	eDebug("[NxplWindowProvider] unregister NXPL display handle=%p", m_nxpl_handle);
	NXPL_UnregisterNexusDisplayPlatform((NXPL_PlatformHandle)m_nxpl_handle);
	m_nxpl_handle = nullptr;
	m_registered = false;
}

void NxplWindowProvider::leavePlatform()
{
	if (!m_joined)
		return;

	if (m_joined_with_nxclient && nxplUninitNexusClient())
	{
		if (NxClientUninitProc uninit = nxClientUninitProc())
		{
			eDebug("[NxplWindowProvider] leave Nexus client");
			uninit();
		}
	}
	else
	{
		eDebug("[NxplWindowProvider] keep Nexus client joined to avoid late shutdown crash");
	}

	m_joined = false;
	m_joined_with_nxclient = false;
}

void NxplWindowProvider::cleanup()
{
	if (!nxplReleaseNexusResources())
	{
		eDebug("[NxplWindowProvider] skip NXPL teardown at process shutdown native=%p display=%p joined=%d registered=%d",
			m_native_window, m_nxpl_handle, m_joined ? 1 : 0, m_registered ? 1 : 0);
		m_native_window = nullptr;
		m_nxpl_handle = nullptr;
		m_joined = false;
		m_joined_with_nxclient = false;
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
