#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <memory.h>
#include <linux/kd.h>

#include <lib/base/econfig.h>
#include <lib/gdi/fb.h>

fbClass *fbClass::instance;

fbClass *fbClass::getInstance()
{
	return instance;
}

fbClass::fbClass(const char *fb)
{
	instance=this;
	locked=0;
	available=0;
	cmap.start=0;
	cmap.len=256;
	cmap.red=red;
	cmap.green=green;
	cmap.blue=blue;
	cmap.transp=trans;

	int state=0;
	eConfig::getInstance()->getKey("/ezap/osd/showConsoleOnFB", state);

	fd=open(fb, O_RDWR);
	if (fd<0)
	{
		perror(fb);
		goto nolfb;
	}
	if (ioctl(fd, FBIOGET_VSCREENINFO, &screeninfo)<0)
	{
		perror("FBIOGET_VSCREENINFO");
		goto nolfb;
	}
	
	memcpy(&oldscreen, &screeninfo, sizeof(screeninfo));

	fb_fix_screeninfo fix;
	if (ioctl(fd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		perror("FBIOGET_FSCREENINFO");
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

	showConsole(state);
	return;
nolfb:
	lfb=0;
	printf("framebuffer not available.\n");
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
	screeninfo.yres_virtual=screeninfo.yres=nyRes;
	screeninfo.height=0;
	screeninfo.width=0;
	screeninfo.xoffset=screeninfo.yoffset=0;
	screeninfo.bits_per_pixel=nbpp;
	if (ioctl(fd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
	{
		perror("FBIOPUT_VSCREENINFO");
		printf("fb failed\n");
		return -1;
	}
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
	}
	stride=fix.line_length;
	memset(lfb, 0, stride*yRes);
	return 0;
}

fbClass::~fbClass()
{
	if (available)
		ioctl(fd, FBIOPUT_VSCREENINFO, &oldscreen);
	if (lfb)
		munmap(lfb, available);
}

int fbClass::PutCMAP()
{
	return ioctl(fd, FBIOPUTCMAP, &cmap);
}

void fbClass::Box(int x, int y, int width, int height, int color, int backcolor)
{
	if (width<=2 || locked)
		return;
	int offset=y*stride+x/2;
	int first=0xF0|((color&0xF0)>>4);
	int last= 0xF0|((backcolor&0xF0)>>4);
	color=(color&0xF)*0x11;
	int halfwidth=width/2;
	for (int ay=y; ay<(y+height); ay++)
	{
		lfb[offset]=first;
		memset(lfb+offset+1, color, halfwidth-2);
		lfb[offset+halfwidth-1]=last;
		offset+=stride;
	}
}

void fbClass::NBox(int x, int y, int width, int height, int color)
{
	if (locked)
		return;
	int offset=y*stride+x/2;
	int halfwidth=width/2;
	for (int ay=y; ay<(y+height); ay++)
	{
		memset(lfb+offset, color, halfwidth);
		offset+=stride;
	}
}

void fbClass::VLine(int x, int y, int sy, int color)
{
	if (locked)
		return;
	int offset=y*stride+x/2;
	while (sy--)
	{
		lfb[offset]=color;
		offset+=stride;
	}
}

int fbClass::lock()
{
	if (locked)
		return -1;
	locked=1;
	return fd;
}

void fbClass::unlock()
{
	if (!locked)
		return;
	locked=0;
	SetMode(xRes, yRes, bpp);
	PutCMAP();
}
