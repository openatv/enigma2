#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <memory.h>
#include <linux/kd.h>

#include <lib/gdi/fblcd.h>

#ifndef FBIO_BLIT
#define FBIO_SET_MANUAL_BLIT _IOW('F', 0x21, __u8)
#define FBIO_BLIT 0x22
#endif

eFbLCD::eFbLCD(const char *fb)
{
	m_manual_blit = -1;
	instance = this;
	locked = 0;
	_buffer = 0;
	m_available = 0;
	m_cmap.start = 0;
	m_cmap.len = 256;
	m_cmap.red = m_red;
	m_cmap.green = m_green;
	m_cmap.blue = m_blue;
	m_cmap.transp = m_trans;
	m_alpha = 255;
	m_gamma = 128;
	m_brightness = 128;

	lcdfd = open(fb, O_RDWR);
	if (lcdfd < 0)
	{
		eDebug("[eFbLCD] %s: %m", fb);
		goto nolfb;
	}

	if (ioctl(lcdfd, FBIOGET_VSCREENINFO, &m_screeninfo) < 0)
	{
		eDebug("[eFbLCD] FBIOGET_VSCREENINFO: %m");
		goto nolfb;
	}

	fb_fix_screeninfo fix;
	if (ioctl(lcdfd, FBIOGET_FSCREENINFO, &fix) < 0)
	{
		eDebug("[eFbLCD] FBIOGET_FSCREENINFO: %m");
		goto nolfb;
	}

	m_available = fix.smem_len;
	m_phys_mem = fix.smem_start;
	eDebug("[eFbLCD] %s %dk video mem", fb, m_available / 1024);
	_buffer=(unsigned char*)mmap(0, m_available, PROT_WRITE|PROT_READ, MAP_SHARED, lcdfd, 0);
	if (!_buffer)
	{
		eDebug("[eFbLCD] mmap: %m");
		goto nolfb;
	}

	lcd_type = 4;
	calcRamp();
	getMode();
	setMode(m_xRes, m_yRes, m_bpp);
	enableManualBlit();

	return;
nolfb:
	if (lcdfd >= 0)
	{
		::close(lcdfd);
		lcdfd = -1;
	}
	eDebug("[eFbLCD] framebuffer %s not available", fb);
	return;
}

eFbLCD::~eFbLCD()
{
	if (_buffer)
	{
		msync(_buffer, m_available, MS_SYNC);
		munmap(_buffer, m_available);
		_buffer = 0;
	}
	if (lcdfd >= 0)
	{
		::close(lcdfd);
		lcdfd = -1;
	}
}

int eFbLCD::setMode(int nxRes, int nyRes, int nbpp)
{
	m_screeninfo.xres_virtual = m_screeninfo.xres = nxRes;
	m_screeninfo.yres_virtual = (m_screeninfo.yres = nyRes) * 2;
	m_screeninfo.height = 0;
	m_screeninfo.width = 0;
	m_screeninfo.xoffset = m_screeninfo.yoffset = 0;
	m_screeninfo.bits_per_pixel = nbpp;

	switch (nbpp) {
	case 16:
		// ARGB 1555
		m_screeninfo.transp.offset = 15;
		m_screeninfo.transp.length = 1;
		m_screeninfo.red.offset = 10;
		m_screeninfo.red.length = 5;
		m_screeninfo.green.offset = 5;
		m_screeninfo.green.length = 5;
		m_screeninfo.blue.offset = 0;
		m_screeninfo.blue.length = 5;
		break;
	case 32:
		// ARGB 8888
		m_screeninfo.transp.offset = 24;
		m_screeninfo.transp.length = 8;
		m_screeninfo.red.offset = 16;
		m_screeninfo.red.length = 8;
		m_screeninfo.green.offset = 8;
		m_screeninfo.green.length = 8;
		m_screeninfo.blue.offset = 0;
		m_screeninfo.blue.length = 8;
		break;
	}

	if (ioctl(lcdfd, FBIOPUT_VSCREENINFO, &m_screeninfo) < 0)
	{
		// try single buffering
		m_screeninfo.yres_virtual = m_screeninfo.yres=nyRes;

		if (ioctl(lcdfd, FBIOPUT_VSCREENINFO, &m_screeninfo) < 0)
		{
			eDebug("[eFbLCD] FBIOPUT_VSCREENINFO: %m");
			return -1;
		}
		eDebug("[eFbLCD] double buffering not available.");
	}
	else
		eDebug("[eFbLCD] double buffering available!");

	ioctl(lcdfd, FBIOGET_VSCREENINFO, &m_screeninfo);

	if ((m_screeninfo.xres != nxRes) && (m_screeninfo.yres != nyRes) && (m_screeninfo.bits_per_pixel != nbpp))
	{
		eDebug("[eFbLCD] SetMode failed: wanted: %dx%dx%d, got %dx%dx%d",
			nxRes, nyRes, nbpp,
			m_screeninfo.xres, m_screeninfo.yres, m_screeninfo.bits_per_pixel);
	}
	m_xRes = m_screeninfo.xres;
	m_yRes = m_screeninfo.yres;
	m_bpp = m_screeninfo.bits_per_pixel;
	fb_fix_screeninfo fix;
	if (ioctl(lcdfd, FBIOGET_FSCREENINFO, &fix) < 0)
	{
		eDebug("[eFbLCD] FBIOGET_FSCREENINFO: %m");
	}
	_stride = fix.line_length;
	memset(_buffer, 0, _stride * m_yRes);
	update();
	return 0;
}

void eFbLCD::getMode()
{
	m_xRes = m_screeninfo.xres;
	m_yRes = m_screeninfo.yres;
	m_bpp = m_screeninfo.bits_per_pixel;
}

int eFbLCD::waitVSync()
{
	int c = 0;
	return ioctl(lcdfd, FBIO_WAITFORVSYNC, &c);
}

void eFbLCD::update() // blit
{
	if (m_manual_blit == 1)
	{
		if (ioctl(lcdfd, FBIO_BLIT) < 0)
			eDebug("[eFbLCD] FBIO_BLIT: %m");
	}
}

int eFbLCD::putCMAP()
{
	return ioctl(lcdfd, FBIOPUTCMAP, &m_cmap);
}

int eFbLCD::lock()
{
	if (locked)
		return -1;
	if (m_manual_blit == 1)
	{
		locked = 2;
		disableManualBlit();
	}
	else
		locked = 1;
	return lcdfd;
}

void eFbLCD::unlock()
{
	if (!locked)
		return;
	if (locked == 2)  // re-enable manualBlit
		enableManualBlit();
	locked = 0;
	setMode(m_xRes, m_yRes, m_bpp);
	putCMAP();
}

void eFbLCD::calcRamp()
{
	for (int i = 0; i < 256; i++)
	{
		int d;
		d = i;
		d = (d-128)*(m_gamma+64)/(128+64)+128;
		d += m_brightness-128; // brightness correction
		if (d < 0)
			d = 0;
		if (d > 255)
			d = 255;
		m_ramp[i] = d;

		m_rampalpha[i] = i*m_alpha/256;
	}

	m_rampalpha[255] = 255; // transparent BLEIBT bitte so.
}

void eFbLCD::setPalette(gUnmanagedSurface surface)
{
	if (!surface.clut.data)
		return;

	for (int i=0; i < 256; ++i)
	{
		m_cmap.red[i] = m_ramp[surface.clut.data[i].r]<<8;
		m_cmap.green[i] = m_ramp[surface.clut.data[i].g]<<8;
		m_cmap.blue[i] = m_ramp[surface.clut.data[i].b]<<8;
		m_cmap.transp[i] = m_rampalpha[surface.clut.data[i].a]<<8;
	}
	putCMAP();
}

void eFbLCD::enableManualBlit()
{
	unsigned char tmp = 1;
	if (ioctl(lcdfd, FBIO_SET_MANUAL_BLIT, &tmp) < 0)
		eDebug("[eFbLCD] enable FBIO_SET_MANUAL_BLIT: %m");
	else
		m_manual_blit = 1;
}

void eFbLCD::disableManualBlit()
{
	unsigned char tmp = 0;
	if (ioctl(lcdfd, FBIO_SET_MANUAL_BLIT, &tmp) < 0)
		eDebug("[eFbLCD] disable FBIO_SET_MANUAL_BLIT: %m");
	else
		m_manual_blit = 0;
}

int eFbLCD::setLCDBrightness(int brightness)
{
	eDebug("[eFbLCD] setLCDBrightness %d", brightness);
	FILE *f = fopen("/proc/stb/lcd/oled_brightness", "w");
	if (f)
	{
		if (fprintf(f, "%d", brightness) == 0)
			eDebug("[eFbLCD] write /proc/stb/lcd/oled_brightness failed: %m");
		fclose(f);
	}
	return 0;
}
