#include <lib/gdi/sdl.h>
#include <lib/actions/action.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>
#include <lib/driver/rcsdl.h>

#include <SDL.h>

gSDLDC::gSDLDC() : m_pump(eApp, 1)
{
	if (SDL_Init(SDL_INIT_VIDEO) < 0) {
		eWarning("[gSDLDC] Could not initialize SDL: %s", SDL_GetError());
		return;
	}

	setResolution(720, 576);

	CONNECT(m_pump.recv_msg, gSDLDC::pumpEvent);

	m_surface.type = 0;
	m_surface.clut.colors = 256;
	m_surface.clut.data = new gRGB[m_surface.clut.colors];

	m_pixmap = new gPixmap(&m_surface);

	memset(m_surface.clut.data, 0, sizeof(*m_surface.clut.data)*m_surface.clut.colors);

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

void gSDLDC::setResolution(int xres, int yres)
{
	pushEvent(EV_SET_VIDEO_MODE, (void *)xres, (void *)yres);
}

/*
 * SDL thread below...
 */

void gSDLDC::evSetVideoMode(unsigned long xres, unsigned long yres)
{
	m_screen = SDL_SetVideoMode(xres, yres, 32, SDL_HWSURFACE);
	if (!m_screen) {
		eFatal("[gSDLDC] Could not create SDL surface: %s", SDL_GetError());
		return;
	}

	m_surface.x = m_screen->w;
	m_surface.y = m_screen->h;
	m_surface.bpp = m_screen->format->BitsPerPixel;
	m_surface.bypp = m_screen->format->BytesPerPixel;
	m_surface.stride = m_screen->pitch;
	m_surface.data = m_screen->pixels;

	SDL_EnableUNICODE(1);
}

void gSDLDC::evFlip()
{
	SDL_Flip(m_screen);
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
