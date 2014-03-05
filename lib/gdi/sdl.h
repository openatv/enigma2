#ifndef __lib_gdi_sdl_h
#define __lib_gdi_sdl_h

#include <lib/base/thread.h>
#include <lib/gdi/gmaindc.h>

#include <SDL.h>

class gSDLDC: public gMainDC, public eThread, public Object
{
private:
	SDL_Surface *m_screen;
	void exec(const gOpcode *opcode);

	gUnmanagedSurface m_surface;

	eFixedMessagePump<SDL_Event> m_pump;
	void keyEvent(const SDL_Event &event);
	void pumpEvent(const SDL_Event &event);
	virtual void thread();

	enum event {
		EV_SET_VIDEO_MODE,
		EV_FLIP,
		EV_QUIT,
	};

	void pushEvent(enum event code, void *data1 = 0, void *data2 = 0);
	void evSetVideoMode(unsigned long xres, unsigned long yres);
	void evFlip();

public:
	void setResolution(int xres, int yres);
	gSDLDC();
	virtual ~gSDLDC();
	int islocked() const { return 0; }
};

#endif
