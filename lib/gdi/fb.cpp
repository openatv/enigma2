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
		perror(fb);
		goto nolfb;
	}


#if not defined(__sh__)
	if (ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo)<0)
	{
		perror("FBIOGET_VSCREENINFO");
		goto nolfb;
	}
#endif

	fb_fix_screeninfo fix;
	if (ioctl(fbFd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		perror("FBIOGET_FSCREENINFO");
		goto nolfb;
	}

	available=fix.smem_len;
	m_phys_mem = fix.smem_start;
#if defined(__sh__)
	eDebug("%dk total video mem", available/1024);
	// The first 1920x1080x4 bytes are reserved
	// After that we can take 1280x720x4 bytes for our virtual framebuffer
	available -= 1920*1080*4;
	eDebug("%dk usable video mem", available/1024);
	lfb=(unsigned char*)mmap(0, available, PROT_WRITE|PROT_READ, MAP_SHARED, fbFd, 1920*1080*4);
#else
	eDebug("%dk video mem", available/1024);
	lfb=(unsigned char*)mmap(0, available, PROT_WRITE|PROT_READ, MAP_SHARED, fbFd, 0);
#endif
	if (!lfb)
	{
		perror("mmap");
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
	printf("framebuffer not available.\n");
	return;
}

int fbClass::showConsole(int state)
{
#if not defined(__sh__)
	int fd=open("/dev/tty0", O_RDWR);
	if(fd>=0)
	{
		if(ioctl(fd, KDSETMODE, state?KD_TEXT:KD_GRAPHICS)<0)
		{
			eDebug("setting /dev/tty0 status failed.");
		}
		close(fd);
	}
#endif
	return 0;
}

int fbClass::SetMode(int nxRes, int nyRes, int nbpp)
{
#if defined(__sh__)
	xRes=nxRes;
	yRes=nyRes;
	bpp=32;
	m_number_of_pages = 1;
	topDiff=bottomDiff=leftDiff=rightDiff = 0;
#else
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
			perror("FBIOPUT_VSCREENINFO");
			printf("fb failed\n");
			return -1;
		}
		eDebug(" - double buffering not available.");
	} else
		eDebug(" - double buffering available!");

	m_number_of_pages = screeninfo.yres_virtual / nyRes;

#endif
	ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo);

#if defined(__sh__)
	xResSc=screeninfo.xres;
	yResSc=screeninfo.yres;
	stride=xRes*4;
#else
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
	if (ioctl(fbFd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		perror("FBIOGET_FSCREENINFO");
		printf("fb failed\n");
	}
	stride=fix.line_length;
	memset(lfb, 0, stride*yRes);
#endif
	blit();
	return 0;
}

void fbClass::getMode(int &xres, int &yres, int &bpp)
{
#if defined(__sh__)
	xres = xRes;
	yres = yRes;
	bpp = 32;
#else
	xres = screeninfo.xres;
	yres = screeninfo.yres;
	bpp = screeninfo.bits_per_pixel;
#endif
}

int fbClass::setOffset(int off)
{
	screeninfo.xoffset = 0;
	screeninfo.yoffset = off;
	return ioctl(fbFd, FBIOPAN_DISPLAY, &screeninfo);
}

int fbClass::waitVSync()
{
	int c = 0;
	return ioctl(fbFd, FBIO_WAITFORVSYNC, &c);
}

void fbClass::blit()
{
#if defined(__sh__)
	int modefd=open("/proc/stb/video/3d_mode", O_RDWR);
	char buf[16] = "off";
	if (modefd > 0)
	{
		read(modefd, buf, 15);
		buf[15]='\0';
		close(modefd);
	}

	STMFBIO_BLT_DATA    bltData;
	memset(&bltData, 0, sizeof(STMFBIO_BLT_DATA));
	bltData.operation  = BLT_OP_COPY;
	bltData.srcOffset  = 1920*1080*4;
	bltData.srcPitch   = xRes * 4;
	bltData.dstOffset  = 0;
	bltData.dstPitch   = xResSc*4;
	bltData.src_top    = 0;
	bltData.src_left   = 0;
	bltData.src_right  = xRes;
	bltData.src_bottom = yRes;
	bltData.srcFormat  = SURF_BGRA8888;
	bltData.dstFormat  = SURF_BGRA8888;
	bltData.srcMemBase = STMFBGP_FRAMEBUFFER;
	bltData.dstMemBase = STMFBGP_FRAMEBUFFER;

	if (strncmp(buf,"sbs",3)==0)
	{
		bltData.dst_top    = 0 + topDiff;
		bltData.dst_left   = 0 + leftDiff/2;
		bltData.dst_right  = xResSc/2 + rightDiff/2;
		bltData.dst_bottom = yResSc + bottomDiff;
		if (ioctl(fbFd, STMFBIO_BLT, &bltData ) < 0)
		{
			perror("STMFBIO_BLT");
		}
		bltData.dst_top    = 0 + topDiff;
		bltData.dst_left   = xResSc/2 + leftDiff/2;
		bltData.dst_right  = xResSc + rightDiff/2;
		bltData.dst_bottom = yResSc + bottomDiff;
		if (ioctl(fbFd, STMFBIO_BLT, &bltData ) < 0)
		{
			perror("STMFBIO_BLT");
		}
	}
	else if (strncmp(buf,"tab",3)==0)
	{
		bltData.dst_top    = 0 + topDiff/2;
		bltData.dst_left   = 0 + leftDiff;
		bltData.dst_right  = xResSc + rightDiff;
		bltData.dst_bottom = yResSc/2 + bottomDiff/2;
		if (ioctl(fbFd, STMFBIO_BLT, &bltData ) < 0)
		{
			perror("STMFBIO_BLT");
		}
		bltData.dst_top    = yResSc/2 + topDiff/2;
		bltData.dst_left   = 0 + leftDiff;
		bltData.dst_right  = xResSc + rightDiff;
		bltData.dst_bottom = yResSc + bottomDiff/2;
		if (ioctl(fbFd, STMFBIO_BLT, &bltData ) < 0)
		{
			perror("STMFBIO_BLT");
		}
	}
	else
	{
		bltData.dst_top    = 0 + topDiff;
		bltData.dst_left   = 0 + leftDiff;
		bltData.dst_right  = xResSc + rightDiff;
		bltData.dst_bottom = yResSc + bottomDiff;
		if (ioctl(fbFd, STMFBIO_BLT, &bltData ) < 0)
		{
			perror("STMFBIO_BLT");
		}
	
	}

	if (ioctl(fbFd, STMFBIO_SYNC_BLITTER) < 0)
	{
		perror("STMFBIO_SYNC_BLITTER");
	}
#else
	if (m_manual_blit == 1) {
		if (ioctl(fbFd, FBIO_BLIT) < 0)
			perror("FBIO_BLIT");
	}
#endif
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
#if defined(__sh__)
	outcfg.outputid = STMFBIO_OUTPUTID_MAIN;
	if (ioctl( fbFd, STMFBIO_GET_OUTPUT_CONFIG, &outcfg ) < 0)
		perror("STMFBIO_GET_OUTPUT_CONFIG\n");

	outinfo.outputid = STMFBIO_OUTPUTID_MAIN;
	if (ioctl( fbFd, STMFBIO_GET_OUTPUTINFO, &outinfo ) < 0)
		perror("STMFBIO_GET_OUTPUTINFO\n");

	//if (ioctl( fbFd, STMFBIO_GET_VAR_SCREENINFO_EX, &infoex ) < 0)
	//	printf("ERROR\n");

	planemode.layerid = 0;
	if (ioctl( fbFd, STMFBIO_GET_PLANEMODE, &planemode ) < 0)
		perror("STMFBIO_GET_PLANEMODE\n");

	if (ioctl( fbFd, STMFBIO_GET_VAR_SCREENINFO_EX, &infoex ) < 0)
		perror("STMFBIO_GET_VAR_SCREENINFO_EX\n");
#endif
	return fbFd;
}

void fbClass::unlock()
{
	if (!locked)
		return;
	if (locked == 2)  // re-enable manualBlit
		enableManualBlit();
	locked=0;
#if defined(__sh__)
	if (ioctl( fbFd, STMFBIO_SET_VAR_SCREENINFO_EX, &infoex ) < 0)
		perror("STMFBIO_SET_VAR_SCREENINFO_EX\n");

	if (ioctl( fbFd, STMFBIO_SET_PLANEMODE, &planemode ) < 0)
		perror("STMFBIO_SET_PLANEMODE\n");

	if (ioctl( fbFd, STMFBIO_SET_VAR_SCREENINFO_EX, &infoex ) < 0)
		perror("STMFBIO_SET_VAR_SCREENINFO_EX\n");

	if (ioctl( fbFd, STMFBIO_SET_OUTPUTINFO, &outinfo ) < 0)
		perror("STMFBIO_SET_OUTPUTINFO\n");

	if (ioctl( fbFd, STMFBIO_SET_OUTPUT_CONFIG, &outcfg ) < 0)
		perror("STMFBIO_SET_OUTPUT_CONFIG\n");

	memset(lfb, 0, stride*yRes);
#endif
	SetMode(xRes, yRes, bpp);
	PutCMAP();
}

void fbClass::enableManualBlit()
{
#if not defined(__sh__)
	unsigned char tmp = 1;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		perror("FBIO_SET_MANUAL_BLIT");
	else
		m_manual_blit = 1;
#endif
}

void fbClass::disableManualBlit()
{
#if not defined(__sh__)
	unsigned char tmp = 0;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		perror("FBIO_SET_MANUAL_BLIT");
	else
		m_manual_blit = 0;
#endif
}

#if defined(__sh__)
void fbClass::clearFBblit()
{
	//set real frambuffer transparent
//	memset(lfb, 0x00, xRes * yRes * 4);
	blit();
}

int fbClass::getFBdiff(int ret)
{
	if(ret == 0)
		return topDiff;
	else if(ret == 1)
		return leftDiff;
	else if(ret == 2)
		return rightDiff;
	else if(ret == 3)
		return bottomDiff;
	else
		return -1;
}

void fbClass::setFBdiff(int top, int left, int right, int bottom)
{
	if(top < 0) top = 0;
	if(top > yRes) top = yRes;
	topDiff = top;
	if(left < 0) left = 0;
	if(left > xRes) left = xRes;
	leftDiff = left;
	if(right > 0) right = 0;
	if(-right > xRes) right = -xRes;
	rightDiff = right;
	if(bottom > 0) bottom = 0;
	if(-bottom > yRes) bottom = -yRes;
	bottomDiff = bottom;
}
#endif

