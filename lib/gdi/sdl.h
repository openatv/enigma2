#ifndef __lib_gdi_sdl_h
#define __lib_gdi_sdl_h

#include "fb.h"
#include "gpixmap.h"
#include "grc.h"

#include <SDL.h>

class gSDLDC: public gDC
{
	SDL_Surface *m_screen;
	static gSDLDC *m_instance;
	void exec(gOpcode *opcode);

	void setPalette();
	gSurface m_surface;
public:
	
	gSDLDC();
	virtual ~gSDLDC();
	static int getInstance(ePtr<gSDLDC> &ptr) { if (!m_instance) return -1; ptr = m_instance; return 0; }
	int islocked() { return 0; }
};


#endif
