#include <lib/gdi/sdl.h>
#include <lib/actions/action.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>
#include <lib/driver/rcsdl.h>

#include <SDL2/SDL.h>

gSDLDC::gSDLDC() : m_window(nullptr), m_osd_tex(nullptr), m_pump(eApp, 1,"gSDLDC")
{
	if (SDL_Init(SDL_INIT_VIDEO) < 0) {
		eWarning("[gSDLDC] Could not initialize SDL: %s", SDL_GetError());
		return;
	}

	CONNECT(m_pump.recv_msg, gSDLDC::pumpEvent);

	m_surface.clut.colors = 256;
	m_surface.clut.data = new gRGB[m_surface.clut.colors];

	m_pixmap = new gPixmap(&m_surface);

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wclass-memaccess"
	memset(m_surface.clut.data, 0, sizeof(*m_surface.clut.data)*m_surface.clut.colors);
#pragma GCC diagnostic pop

	run();
}

gSDLDC::~gSDLDC()
{
	pushEvent(EV_QUIT);
	kill();
	SDL_Quit();
}

void gSDLDC::keyEvent(const SDL_Event &event)
{
	eSDLInputDriver *driver = eSDLInputDriver::getInstance();

	eDebug("[gSDLDC] Key %s: key=%d", (event.type == SDL_KEYDOWN) ? "Down" : "Up", event.key.keysym.sym);

	if (driver)
		driver->keyPressed(&event.key);
}

void gSDLDC::pumpEvent(const SDL_Event &event)
{
	switch (event.type) {
	case SDL_KEYDOWN:
	case SDL_KEYUP:
		keyEvent(event);
		break;
	case SDL_QUIT:
		eDebug("[gSDLDC] Quit");
		extern void quitMainloop(int exit_code);
		quitMainloop(0);
		break;
	}
}

void gSDLDC::pushEvent(enum event code, void *data1, void *data2)
{
	SDL_Event event;

	event.type = SDL_USEREVENT;
	event.user.code = code;
	event.user.data1 = data1;
	event.user.data2 = data2;

	SDL_PushEvent(&event);
}

void gSDLDC::exec(const gOpcode *o)
{
	switch (o->opcode) {
	case gOpcode::flush:
		pushEvent(EV_FLIP);
		eDebug("[gSDLDC] FLUSH");
		break;
	default:
		gDC::exec(o);
		break;
	}
}

void gSDLDC::setResolution(int xres, int yres, int bpp)
{
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-to-pointer-cast"
	pushEvent(EV_SET_VIDEO_MODE, (void *)xres, (void *)yres);
#pragma GCC diagnostic pop
}

/*
 * SDL thread below...
 */

void gSDLDC::evSetVideoMode(unsigned long xres, unsigned long yres)
{
	m_window = SDL_CreateWindow("enigma2-SDL2", 0, 0, xres, yres, SDL_WINDOW_RESIZABLE);
	if (!m_window) {
		eFatal("[gSDLDC] Could not create SDL window: %s", SDL_GetError());
		return;
	}
	m_render = SDL_CreateRenderer(m_window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
	if (!m_render) {
		eFatal("[gSDLDC] Could not create SDL renderer: %s", SDL_GetError());
		return;
	}
	m_osd = SDL_CreateRGBSurface(SDL_SWSURFACE, xres, yres, 32, 0, 0, 0, 0);
	SDL_SetColorKey(m_osd, SDL_TRUE, SDL_MapRGB(m_osd->format, 0, 0, 0));
	m_osd_tex = SDL_CreateTexture(m_render, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STATIC, xres, yres);
	SDL_SetTextureBlendMode(m_osd_tex, SDL_BLENDMODE_BLEND);

	m_surface.x = m_osd->w;
	m_surface.y = m_osd->h;
	m_surface.bpp = m_osd->format->BitsPerPixel;
	m_surface.bypp = m_osd->format->BytesPerPixel;
	m_surface.stride = m_osd->pitch;
	m_surface.data = m_osd->pixels;
}

void gSDLDC::evFlip()
{
	if (!m_window)
		return;
	
	// Clear
	SDL_SetRenderDrawColor(m_render, 0, 0, 0, 0);
	SDL_RenderClear(m_render);
	
	// Render OSD
	SDL_UpdateTexture(m_osd_tex, NULL, m_osd->pixels, m_osd->pitch);
	SDL_RenderCopy(m_render, m_osd_tex, NULL, NULL);

	SDL_RenderPresent(m_render);
}

void gSDLDC::thread()
{
	hasStarted();

	bool stop = false;
	while (!stop) {
		SDL_Event event;
		if (SDL_WaitEvent(&event)) {
			switch (event.type) {
			case SDL_KEYDOWN:
			case SDL_KEYUP:
			case SDL_QUIT:
				m_pump.send(event);
				break;
			case SDL_USEREVENT:
				switch (event.user.code) {
				case EV_SET_VIDEO_MODE:
					evSetVideoMode((unsigned long)event.user.data1, (unsigned long)event.user.data2);
					break;
				case EV_FLIP:
					evFlip();
					break;
				case EV_QUIT:
					stop = true;
					break;
				}
				break;
			}
		}
	}
}

eAutoInitPtr<gSDLDC> init_gSDLDC(eAutoInitNumbers::graphic-1, "gSDLDC");
