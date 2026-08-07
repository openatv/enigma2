#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/gdi/egl/egl_config.h>
#include <lib/gdi/egl/gegldc.h>

#ifdef DREAMNEXTGEN
#include <lib/gdi/egl/platform/amlogic/amlogic_window_provider.h>
#endif

class gEGLDCAutoInit : protected eAutoInit
{
	ePtr<gEGLDC> m_dc;
	void initNow() override
	{
		if (m_dc)
			return;

		if (egl_config::disable_egl)
		{
			eDebug("[gEGLDC] EGL disabled via command line");
			return;
		}

		ePtr<gMainDC> existing_dc;
		if (gMainDC::getInstance(existing_dc) == 0)
		{
			eDebug("[gEGLDC] gMainDC already initialized, skipping gEGLDC");
			return;
		}

		INativeWindowProvider *provider = nullptr;

#if !defined(DREAMNEXTGEN) && !defined(HAVE_VUPLUS_EGL) && !defined(HAVE_VUPLUS_MIPSEL_EGL) && !defined(HAVE_NXPL_EGL) && !defined(HAVE_V3DPLATFORM_EGL) && !defined(HAVE_HISILICON_EGL) && !defined(HAVE_DREAMBCM_EGL)
		// Fallback for other platforms (SDL/Wayland) once implemented
		// For now, if not HWDREAMONE, we don't have a default provider here
		// unless we add SDLWindowProvider or WaylandWindowProvider detection.
		if (!provider)
			return;
#endif

		eDebug("[eInit] + (%d) gEGLDC", rl);
		m_dc = new gEGLDC(provider);
		if (!m_dc->initEGL())
		{
			eDebug("[gEGLDC] initEGL failed, falling back...");
			m_dc = nullptr;
		}
	}

	void closeNow() override
	{
		m_dc = nullptr;
	}

public:
	gEGLDCAutoInit()
		: eAutoInit(eAutoInitNumbers::graphic - 2, "gEGLDC"), m_dc(nullptr)
	{
		eInit::add(rl, this);
	}

	~gEGLDCAutoInit()
	{
		eInit::remove(rl, this);
	}
};

static gEGLDCAutoInit init_gEGLDC_custom;
