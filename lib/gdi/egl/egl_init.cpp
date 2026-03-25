#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/gdi/egl/egl_config.h>
#include <lib/gdi/egl/gegldc.h>

#ifdef HWDREAMONE
#include <lib/gdi/egl/platform/amlogic/amlogic_window_provider.h>
#endif

class gEGLDCAutoInit : protected eAutoInit
{
	gEGLDC *m_dc;
	void initNow() override
	{
		if (egl_config::disable_egl)
		{
			eDebug("[gEGLDC] EGL disabled via command line");
			return;
		}

		INativeWindowProvider *provider = nullptr;

#ifdef HWDREAMONE
		provider = new AmlogicWindowProvider();
#else
		// Fallback for other platforms (SDL/Wayland) once implemented
		// For now, if not HWDREAMONE, we don't have a default provider here
		// unless we add SDLWindowProvider or WaylandWindowProvider detection.
#endif

		if (provider)
		{
			eDebug("[eInit] + (%d) gEGLDC", rl);
			m_dc = new gEGLDC(provider);
			if (!m_dc->initEGL())
			{
				eDebug("[gEGLDC] initEGL failed, falling back...");
				delete m_dc;
				m_dc = nullptr;
			}
		}
	}

	void closeNow() override
	{
		if (m_dc)
		{
			delete m_dc;
			m_dc = nullptr;
		}
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
