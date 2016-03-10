#include <lib/gdi/gfbdc.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <lib/gdi/accel.h>

#include <time.h>

#ifdef USE_LIBVUGLES2
#include <vuplus_gles.h>
#endif

#ifdef HAVE_OSDANIMATION
#include <lib/base/cfile.h>
#endif

gFBDC::gFBDC()
{
	fb=new fbClass;

	if (!fb->Available())
		eFatal("no framebuffer available");

	int xres;
	int yres;
	int bpp;
	fb->getMode(xres, yres, bpp);

	/* we can only use one of these three modes: */
	if (!((xres == 720 && yres == 576)
		|| (xres == 1280 && yres == 720)
		|| (xres == 1920 && yres == 1080)))
	{
		/* fallback to a decent default */
		xres = 720;
		yres = 576;
	}

	surface.clut.data = 0;
	setResolution(xres, yres); // default res

	reloadSettings();
}

gFBDC::~gFBDC()
{
	delete fb;
	delete[] surface.clut.data;
}

void gFBDC::calcRamp()
{
#if 0
	float fgamma=gamma ? gamma : 1;
	fgamma/=10.0;
	fgamma=1/log(fgamma);
	for (int i=0; i<256; i++)
	{
		float raw=i/255.0; // IIH, float.
		float corr=pow(raw, fgamma) * 256.0;

		int d=corr * (float)(256-brightness) / 256 + brightness;
		if (d < 0)
			d=0;
		if (d > 255)
			d=255;
		ramp[i]=d;

		rampalpha[i]=i*alpha/256;
	}
#endif
	for (int i=0; i<256; i++)
	{
		int d;
		d=i;
		d=(d-128)*(gamma+64)/(128+64)+128;
		d+=brightness-128; // brightness correction
		if (d<0)
			d=0;
		if (d>255)
			d=255;
		ramp[i]=d;

		rampalpha[i]=i*alpha/256;
	}

	rampalpha[255]=255; // transparent BLEIBT bitte so.
}

void gFBDC::setPalette()
{
	if (!surface.clut.data)
		return;

	for (int i=0; i<256; ++i)
	{
		fb->CMAP()->red[i]=ramp[surface.clut.data[i].r]<<8;
		fb->CMAP()->green[i]=ramp[surface.clut.data[i].g]<<8;
		fb->CMAP()->blue[i]=ramp[surface.clut.data[i].b]<<8;
		fb->CMAP()->transp[i]=rampalpha[surface.clut.data[i].a]<<8;
	}
	fb->PutCMAP();
}

void gFBDC::exec(const gOpcode *o)
{
	switch (o->opcode)
	{
	case gOpcode::setPalette:
	{
		gDC::exec(o);
		setPalette();
		break;
	}
	case gOpcode::flip:
	{
		if (surface_back.data_phys)
		{
			gUnmanagedSurface s(surface);
			surface = surface_back;
			surface_back = s;

			if (surface.data_phys > surface_back.data_phys)
				fb->setOffset(surface_back.y);
			else
				fb->setOffset(0);
		}
		break;
	}
	case gOpcode::waitVSync:
	{
		static timeval l;
		static int t;
		timeval now;

		if (t == 1000)
		{
			gettimeofday(&now, 0);

			int diff = (now.tv_sec - l.tv_sec) * 1000 + (now.tv_usec - l.tv_usec) / 1000;
			eDebug("%d ms latency (%d fps)", diff, t * 1000 / (diff ? diff : 1));
			l = now;
			t = 0;
		}

		++t;

		fb->blit();
		fb->waitVSync();
		break;
	}
	case gOpcode::flush:
#ifdef USE_LIBVUGLES2
		if (gles_is_animation())
			gles_do_animation();
		else
			fb->blit();
#else
		fb->blit();
#endif
		break;
	case gOpcode::sendShow:
	{
#ifdef HAVE_OSDANIMATION
		CFile::writeIntHex("/proc/stb/fb/animation_mode", 0x01);
#endif
#ifdef USE_LIBVUGLES2
		gles_set_buffer((unsigned int *)surface.data);
		gles_set_animation(1, o->parm.setShowHideInfo->point.x(), o->parm.setShowHideInfo->point.y(), o->parm.setShowHideInfo->size.width(), o->parm.setShowHideInfo->size.height());
#endif
		break;
	}
	case gOpcode::sendHide:
	{
#ifdef HAVE_OSDANIMATION
		CFile::writeIntHex("/proc/stb/fb/animation_mode", 0x10);
#endif
#ifdef USE_LIBVUGLES2
		gles_set_buffer((unsigned int *)surface.data);
		gles_set_animation(0, o->parm.setShowHideInfo->point.x(), o->parm.setShowHideInfo->point.y(), o->parm.setShowHideInfo->size.width(), o->parm.setShowHideInfo->size.height());
#endif
		break;
	}
#ifdef USE_LIBVUGLES2
	case gOpcode::setView:
	{
		gles_viewport(o->parm.setViewInfo->size.width(), o->parm.setViewInfo->size.height(), fb->Stride());
		break;
	}
#endif

	default:
		gDC::exec(o);
		break;
	}
}

void gFBDC::setAlpha(int a)
{
	alpha=a;

	calcRamp();
	setPalette();
}

void gFBDC::setBrightness(int b)
{
	brightness=b;

	calcRamp();
	setPalette();
}

void gFBDC::setGamma(int g)
{
	gamma=g;

	calcRamp();
	setPalette();
}

void gFBDC::setResolution(int xres, int yres, int bpp)
{
#if defined(__sh__)
	/* if xres and yres are negative call SetMode with the lates xres and yres
	 * we need that to read the new screen dimesnions after a resolution change
	 * without changing the frambuffer dimensions
	 */
	if (xres<0 && yres<0 ) {
		fb->SetMode(surface.x, surface.y, bpp);
		return;
	}
#else
	if (m_pixmap && (surface.x == xres) && (surface.y == yres) && (surface.bpp == bpp))
		return;
#endif

	if (gAccel::getInstance())
		gAccel::getInstance()->releaseAccelMemorySpace();

	fb->SetMode(xres, yres, bpp);

#if defined(__sh__)
	for (int y = 0; y<yres; y++) { // make whole screen transparent
		memset(fb->lfb+y*fb->Stride(), 0x00, fb->Stride());
	}
#endif
	surface.x = xres;
	surface.y = yres;
	surface.bpp = bpp;
	surface.bypp = bpp / 8;
	surface.stride = fb->Stride();
	surface.data = fb->lfb;
	
	for (int y=0; y<yres; y++)    // make whole screen transparent 
		memset(fb->lfb+ y * xres * 4, 0x00, xres * 4);	

	surface.data_phys = fb->getPhysAddr();

	int fb_size = surface.stride * surface.y;

	if (fb->getNumPages() > 1)
	{
		surface_back = surface;
		surface_back.data = fb->lfb + fb_size;
		surface_back.data_phys = surface.data_phys + fb_size;
		fb_size *= 2;
	}
	else
	{
		surface_back.data = 0;
		surface_back.data_phys = 0;
	}

	eDebug("%dkB available for acceleration surfaces.", (fb->Available() - fb_size)/1024);
	eDebug("resolution: %d x %d x %d (stride: %d)", surface.x, surface.y, surface.bpp, fb->Stride());

	if (gAccel::getInstance())
		gAccel::getInstance()->setAccelMemorySpace(fb->lfb + fb_size, surface.data_phys + fb_size, fb->Available() - fb_size);

	if (!surface.clut.data)
	{
		surface.clut.colors = 256;
		surface.clut.data = new gRGB[surface.clut.colors];
		memset(surface.clut.data, 0, sizeof(*surface.clut.data)*surface.clut.colors);
	}

	surface_back.clut = surface.clut;

	m_pixmap = new gPixmap(&surface);
}

void gFBDC::saveSettings()
{
}

void gFBDC::reloadSettings()
{
	alpha=255;
	gamma=128;
	brightness=128;

	calcRamp();
	setPalette();
}

eAutoInitPtr<gFBDC> init_gFBDC(eAutoInitNumbers::graphic-1, "GFBDC");

#ifdef HAVE_OSDANIMATION
void setAnimation_current(int a) {
	switch (a) {
		case 1:
			CFile::writeStr("/proc/stb/fb/animation_current", "simplefade");
			break;
		case 2:
			CFile::writeStr("/proc/stb/fb/animation_current", "simplezoom");
			break;
		case 3:
			CFile::writeStr("/proc/stb/fb/animation_current", "growdrop");
			break;
		case 4:
			CFile::writeStr("/proc/stb/fb/animation_current", "growfromleft");
			break;
		case 5:
			CFile::writeStr("/proc/stb/fb/animation_current", "extrudefromleft");
			break;
		case 6:
			CFile::writeStr("/proc/stb/fb/animation_current", "popup");
			break;
		case 7:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidedrop");
			break;
		case 8:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidefromleft");
			break;
		case 9:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidelefttoright");
			break;
		case 10:
			CFile::writeStr("/proc/stb/fb/animation_current", "sliderighttoleft");
			break;
		case 11:
			CFile::writeStr("/proc/stb/fb/animation_current", "slidetoptobottom");
			break;
		case 12:
			CFile::writeStr("/proc/stb/fb/animation_current", "zoomfromleft");
			break;
		case 13:
			CFile::writeStr("/proc/stb/fb/animation_current", "zoomfromright");
			break;
		case 14:
			CFile::writeStr("/proc/stb/fb/animation_current", "stripes");
			break;
		default:
			CFile::writeStr("/proc/stb/fb/animation_current", "disable");
			break;
	}
}

void setAnimation_speed(int speed) {
	CFile::writeInt("/proc/stb/fb/animation_speed", speed);
}
#endif
