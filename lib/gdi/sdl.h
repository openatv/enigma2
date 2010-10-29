#ifndef __lib_gdi_sdl_h
#define __lib_gdi_sdl_h

#include "fb.h"
#include "gpixmap.h"
#include "gmaindc.h"

#include <SDL.h>

class gSDLDC: public gMainDC
{
	SDL_Surface *m_screen;
	void exec(const gOpcode *opcode);

	void setPalette();
	gSurface m_surface;
public:
	
	void setResolution(int xres, int yres);
	gSDLDC();
	virtual ~gSDLDC();
	int islocked() { return 0; }
};

#endif
