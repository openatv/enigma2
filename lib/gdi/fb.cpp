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
#define FBIO_WAITFORVSYNC _IOW('F', 0x20, __u32)
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
	lfb=0;
	fb_fix_screeninfo fix;
	m_manual_blit=-1;
	instance=this;
	locked=0;
	cmap.start=0;
	cmap.len=256;
	cmap.red=red;
	cmap.green=green;
	cmap.blue=blue;
	cmap.transp=trans;

	fd=open(fb, O_RDWR);
	if (fd<0)
		perror(fb);
	else if (ioctl(fd, FBIOGET_VSCREENINFO, &screeninfo)<0)
		perror("FBIOGET_VSCREENINFO");
	else if (ioctl(fd, FBIOGET_FSCREENINFO, &fix)<0)
		perror("FBIOGET_FSCREENINFO");
	else
	{
		memcpy(&oldscreen, &screeninfo, sizeof(screeninfo));
		available=fix.smem_len;
		lfb=(unsigned char*)mmap(0, available, PROT_WRITE|PROT_READ, MAP_SHARED, fd, 0);
		if (!lfb)
			perror("mmap");
		else
		{
			showConsole(0);
			enableManualBlit();
			stride=fix.line_length;
		}
	}
	return;
}

int fbClass::showConsole(int state)
{
	int fd=open("/dev/vc/0", O_RDWR);
	if(fd>=0)
	{
		if(ioctl(fd, KDSETMODE, state?KD_TEXT:KD_GRAPHICS)<0)
		{
			eDebug("setting /dev/vc/0 status failed.");
		}
		close(fd);
	}
	return 0;
}

int fbClass::SetMode(unsigned int nxRes, unsigned int nyRes, unsigned int nbpp)
{
	screeninfo.xres_virtual=screeninfo.xres=nxRes;
	screeninfo.yres_virtual=(screeninfo.yres=nyRes)*2;
	screeninfo.height=0;
	screeninfo.width=0;
	screeninfo.xoffset=screeninfo.yoffset=0;
	screeninfo.bits_per_pixel=nbpp;

	if (lfb) {
		munmap(lfb, available);
		lfb = 0;
	}

	if (ioctl(fd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
	{
		// try single buffering
		screeninfo.yres_virtual=screeninfo.yres=nyRes;
		
		if (ioctl(fd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
		{
			perror("FBIOPUT_VSCREENINFO");
			printf("fb failed\n");
			return -1;
		}
		eDebug(" - double buffering not available.");
	} else
		eDebug(" - double buffering available!");
	
	m_number_of_pages = screeninfo.yres_virtual / nyRes;
	
	ioctl(fd, FBIOGET_VSCREENINFO, &screeninfo);
	
	if ((screeninfo.xres!=nxRes) && (screeninfo.yres!=nyRes) && (screeninfo.bits_per_pixel!=nbpp))
	{
		eDebug("SetMode failed: wanted: %dx%dx%d, got %dx%dx%d",
			nxRes, nyRes, nbpp,
			screeninfo.xres, screeninfo.yres, screeninfo.bits_per_pixel);
	}
	xRes=screeninfo.xres;
	yRes=screeninfo.yres;
	bpp=screeninfo.bits_per_pixel;

	fb_fix_screeninfo fix;
	if (ioctl(fd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		perror("FBIOGET_FSCREENINFO");
		printf("fb failed\n");
		goto nolfb;
	}

	available=fix.smem_len;
	eDebug("%dk video mem", available/1024);
	lfb=(unsigned char*)mmap(0, available, PROT_WRITE|PROT_READ, MAP_SHARED, fd, 0);
	if (!lfb)
	{
		perror("mmap");
		goto nolfb;
	}

	stride=fix.line_length;

	return 0;
nolfb:
	lfb=0;
	eFatal("framebuffer no more ready after SetMode(%d, %d, %d)", nxRes, nyRes, nbpp);
	return -1;
}

int fbClass::setOffset(int off)
{
	screeninfo.xoffset = 0;
	screeninfo.yoffset = off;
	return ioctl(fd, FBIOPAN_DISPLAY, &screeninfo);
}

int fbClass::waitVSync()
{
	int c = 0;
	return ioctl(fd, FBIO_WAITFORVSYNC, &c);
}

void fbClass::blit()
{
	if (m_manual_blit == 1) {
		if (ioctl(fd, FBIO_BLIT) < 0)
			perror("FBIO_BLIT");
	}
}

fbClass::~fbClass()
{
	if (available)
		ioctl(fd, FBIOPUT_VSCREENINFO, &oldscreen);
	if (lfb)
		munmap(lfb, available);
	showConsole(1);
	disableManualBlit();
}

int fbClass::PutCMAP()
{
	return ioctl(fd, FBIOPUTCMAP, &cmap);
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
	return fd;
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
	if (ioctl(fd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		perror("FBIO_SET_MANUAL_BLIT");
	else
		m_manual_blit = 1;
}

void fbClass::disableManualBlit()
{
	unsigned char tmp = 0;
	if (ioctl(fd,FBIO_SET_MANUAL_BLIT, &tmp)<0) 
		perror("FBIO_SET_MANUAL_BLIT");
	else
		m_manual_blit = 0;
}

