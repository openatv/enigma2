#include <lib/gdi/gfbdc.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/econfig.h>

gFBDC *gFBDC::instance;

gFBDC::gFBDC()
{
	instance=this;
	fb=new fbClass;

	if (!fb->Available())
		eFatal("no framebuffer available");

	fb->SetMode(720, 576, 8);

	for (int y=0; y<576; y++)																		 // make whole screen transparent
		memset(fb->lfb+y*fb->Stride(), 0x00, fb->Stride());

	surface.type = 0;
	surface.x = 720;
	surface.y = 576;
	surface.bpp = 8;
	surface.bypp = 1;
	surface.stride = fb->Stride();
	surface.data = fb->lfb;
	surface.clut.colors=256;
	surface.clut.data=new gRGB[surface.clut.colors];
	
	m_pixmap = new gPixmap(&surface);
	
	memset(surface.clut.data, 0, sizeof(*surface.clut.data)*surface.clut.colors);
	reloadSettings();
}

gFBDC::~gFBDC()
{
	delete fb;
	instance=0;
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
		if (!fb->CMAP()->red[i])
			fb->CMAP()->red[i]=0x100;
	}
	fb->PutCMAP();
}

void gFBDC::exec(gOpcode *o)
{
	switch (o->opcode)
	{
	case gOpcode::setPalette:
	{
		gDC::exec(o);
		setPalette();
		break;
	}
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

void gFBDC::saveSettings()
{
	eConfig::getInstance()->setKey("/ezap/osd/alpha", alpha);
	eConfig::getInstance()->setKey("/ezap/osd/gamma", gamma);
	eConfig::getInstance()->setKey("/ezap/osd/brightness", brightness);
}

void gFBDC::reloadSettings()
{
	if (eConfig::getInstance()->getKey("/ezap/osd/alpha", alpha))
		alpha=255;
	if (eConfig::getInstance()->getKey("/ezap/osd/gamma", gamma))
		gamma=128;
	if (eConfig::getInstance()->getKey("/ezap/osd/brightness", brightness))
		brightness=128;

	calcRamp();
	setPalette();
}

// eAutoInitPtr<gFBDC> init_gFBDC(eAutoInitNumbers::graphic-1, "GFBDC");
