#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <memory.h>
#include <linux/kd.h>

#include <lib/gdi/fb.h>

#ifndef FBIO_WAITFORVSYNC
#define FBIO_WAITFORVSYNC _IOW('F', 0x20, uint32_t)
#endif

#ifndef FBIO_BLIT
#define FBIO_SET_MANUAL_BLIT _IOW('F', 0x21, __u8)
#define FBIO_BLIT 0x22
#endif

fbClass *fbClass::instance;

fbClass *fbClass::getInstance()
{
	return instance;
}

fbClass::fbClass(const char *fb)
{
	m_manual_blit=-1;
	instance=this;
	locked=0;
	lfb = 0;
	available=0;
	cmap.start=0;
	cmap.len=256;
	cmap.red=red;
	cmap.green=green;
	cmap.blue=blue;
	cmap.transp=trans;

	fbFd=open(fb, O_RDWR);
	if (fbFd<0)
	{
		eDebug("[fb] %s %m", fb);
		goto nolfb;
	}


	if (ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo)<0)
	{
		eDebug("[fb] FBIOGET_VSCREENINFO: %m");
		goto nolfb;
	}

	fb_fix_screeninfo fix;
	if (ioctl(fbFd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		eDebug("[fb] FBIOGET_FSCREENINFO: %m");
		goto nolfb;
	}

	available=fix.smem_len;
	m_phys_mem = fix.smem_start;
	eDebug("[fb] %s: %dk video mem", fb, available/1024);
	lfb=(unsigned char*)mmap(0, available, PROT_WRITE|PROT_READ, MAP_SHARED, fbFd, 0);
	if (!lfb)
	{
		eDebug("[fb] mmap: %m");
		goto nolfb;
	}

	showConsole(0);

	enableManualBlit();
	return;
nolfb:
	if (fbFd >= 0)
	{
		::close(fbFd);
		fbFd = -1;
	}
	eDebug("[fb] framebuffer %s not available", fb);
	return;
}

int fbClass::showConsole(int state)
{
	int fd=open("/dev/tty0", O_RDWR);
	if(fd>=0)
	{
		if(ioctl(fd, KDSETMODE, state?KD_TEXT:KD_GRAPHICS)<0)
		{
			eDebug("[fb] setting /dev/tty0 status failed.");
		}
		close(fd);
	}
	return 0;
}

int fbClass::SetMode(int nxRes, int nyRes, int nbpp)
{
	if (fbFd < 0) return -1;
	screeninfo.xres_virtual=screeninfo.xres=nxRes;
	screeninfo.yres_virtual=(screeninfo.yres=nyRes)*2;
	screeninfo.height=0;
	screeninfo.width=0;
	screeninfo.xoffset=screeninfo.yoffset=0;
	screeninfo.bits_per_pixel=nbpp;

	switch (nbpp) {
	case 16:
		// ARGB 1555
		screeninfo.transp.offset = 15;
		screeninfo.transp.length = 1;
		screeninfo.red.offset = 10;
		screeninfo.red.length = 5;
		screeninfo.green.offset = 5;
		screeninfo.green.length = 5;
		screeninfo.blue.offset = 0;
		screeninfo.blue.length = 5;
		break;
	case 32:
		// ARGB 8888
		screeninfo.transp.offset = 24;
		screeninfo.transp.length = 8;
		screeninfo.red.offset = 16;
		screeninfo.red.length = 8;
		screeninfo.green.offset = 8;
		screeninfo.green.length = 8;
		screeninfo.blue.offset = 0;
		screeninfo.blue.length = 8;
		break;
	}

	if (ioctl(fbFd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
	{
		// try single buffering
		screeninfo.yres_virtual=screeninfo.yres=nyRes;

		if (ioctl(fbFd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
		{
			eDebug("[fb] FBIOPUT_VSCREENINFO: %m");
			return -1;
		}
		eDebug("[fb] double buffering not available.");
	} else
		eDebug("[fb] double buffering available!");

	m_number_of_pages = screeninfo.yres_virtual / nyRes;

	ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo);

	if ((screeninfo.xres != (unsigned int)nxRes) || (screeninfo.yres != (unsigned int)nyRes) ||
		(screeninfo.bits_per_pixel != (unsigned int)nbpp))
	{
		eDebug("[fb] SetMode failed: wanted: %dx%dx%d, got %dx%dx%d",
			nxRes, nyRes, nbpp,
			screeninfo.xres, screeninfo.yres, screeninfo.bits_per_pixel);
	}
	xRes=screeninfo.xres;
	yRes=screeninfo.yres;
	bpp=screeninfo.bits_per_pixel;
	fb_fix_screeninfo fix;
	if (ioctl(fbFd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		eDebug("[fb] FBIOGET_FSCREENINFO: %m");
	}
	stride=fix.line_length;
	memset(lfb, 0, stride*yRes);
	blit();
	return 0;
}

void fbClass::getMode(int &xres, int &yres, int &bpp)
{
	xres = screeninfo.xres;
	yres = screeninfo.yres;
	bpp = screeninfo.bits_per_pixel;
}

int fbClass::setOffset(int off)
{
	if (fbFd < 0) return -1;
	screeninfo.xoffset = 0;
	screeninfo.yoffset = off;
	return ioctl(fbFd, FBIOPAN_DISPLAY, &screeninfo);
}

int fbClass::waitVSync()
{
	int c = 0;
	if (fbFd < 0) return -1;
	return ioctl(fbFd, FBIO_WAITFORVSYNC, &c);
}

void fbClass::blit()
{
	if (fbFd < 0) return;
	if (m_manual_blit == 1) {
		if (ioctl(fbFd, FBIO_BLIT) < 0)
			eDebug("[fb] FBIO_BLIT: %m");
	}
}

fbClass::~fbClass()
{
	if (lfb)
	{
		msync(lfb, available, MS_SYNC);
		munmap(lfb, available);
	}
	showConsole(1);
	disableManualBlit();
	if (fbFd >= 0)
	{
		::close(fbFd);
		fbFd = -1;
	}
}

int fbClass::PutCMAP()
{
	if (fbFd < 0) return -1;
	return ioctl(fbFd, FBIOPUTCMAP, &cmap);
}

int fbClass::lock()
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
	return fbFd;
}

void fbClass::unlock()
{
	if (!locked)
		return;
	if (locked == 2)  // re-enable manualBlit
		enableManualBlit();
	locked=0;
	SetMode(xRes, yRes, bpp);
	PutCMAP();
}

void fbClass::enableManualBlit()
{
	unsigned char tmp = 1;
	if (fbFd < 0) return;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		eDebug("[fb] enable FBIO_SET_MANUAL_BLIT: %m");
	else
		m_manual_blit = 1;
}

void fbClass::disableManualBlit()
{
	unsigned char tmp = 0;
	if (fbFd < 0) return;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		eDebug("[fb] disable FBIO_SET_MANUAL_BLIT: %m");
	else
		m_manual_blit = 0;
}

