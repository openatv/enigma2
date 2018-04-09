#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <memory.h>
#include <linux/kd.h>

#include <lib/gdi/fb.h>
#ifdef __sh__
#include <linux/stmfb.h>
#endif

#ifndef FBIO_WAITFORVSYNC
#define FBIO_WAITFORVSYNC _IOW('F', 0x20, uint32_t)
#endif

#ifdef CONFIG_ION

#include <lib/gdi/accel.h>
#include <interfaces/ion.h>
#define ION_HEAP_TYPE_BMEM      (ION_HEAP_TYPE_CUSTOM + 1)
#define ION_HEAP_ID_MASK        (1 << ION_HEAP_TYPE_BMEM)
#define ACCEL_MEM_SIZE          (32*1024*1024)

#elif !defined(FBIO_BLIT)

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
	
#ifdef CONFIG_ION
	int ion;
#endif

	fbFd=open(fb, O_RDWR);
	if (fbFd<0)
	{
		eDebug("[fb] %s %m", fb);
		goto nolfb;
	}

#if not defined(__sh__)
	if (ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo)<0)
	{
		eDebug("[fb] FBIOGET_VSCREENINFO: %m");
		goto nolfb;
	}
#endif

	fb_fix_screeninfo fix;
	if (ioctl(fbFd, FBIOGET_FSCREENINFO, &fix)<0)
	{
		eDebug("[fb] FBIOGET_FSCREENINFO: %m");
		goto nolfb;
	}

	available = fix.smem_len;
	m_phys_mem = fix.smem_start;
	eDebug("[fb] %s: %dk video mem", fb, available/1024);
#if defined(__sh__)
	// The first 1920x1080x4 bytes are reserved
	// After that we can take 1280x720x4 bytes for our virtual framebuffer
	available -= 1920*1080*4;
	eDebug("[fb] %s: %dk video mem", fb, available/1024);
	lfb=(unsigned char*)mmap(0, available, PROT_WRITE|PROT_READ, MAP_SHARED, fbFd, 1920*1080*4);
#elif defined(CONFIG_ION)
	/* allocate accel memory here... its independent from the framebuffer */
	ion = open("/dev/ion", O_RDWR | O_CLOEXEC);
	if (ion >= 0)
	{
		struct ion_allocation_data alloc_data;
		struct ion_fd_data share_data;
		struct ion_handle_data free_data;
		struct ion_phys_data phys_data;
		int ret;
		unsigned char *lion;

		eDebug("[fb] Using ION allocator");

		memset(&alloc_data, 0, sizeof(alloc_data));
		alloc_data.len = ACCEL_MEM_SIZE;
		alloc_data.align = 4096; // 4k aligned
		alloc_data.heap_id_mask = ION_HEAP_ID_MASK;
		ret = ioctl(ion, ION_IOC_ALLOC, &alloc_data);
		if (ret < 0)
		{
			eDebug("[fb] ION_IOC_ALLOC failed");
			eFatal("[fb] failed to allocate accel memory!!!");
			return;
		}

		memset(&phys_data, 0, sizeof(phys_data));
		phys_data.handle = alloc_data.handle;
		ret = ioctl(ion, ION_IOC_PHYS, &phys_data);
		if (ret < 0)
		{
			eDebug("[fb] ION_IOC_PHYS failed");
			goto err_ioc_free;
		}

		memset(&share_data, 0, sizeof(share_data));
		share_data.handle = alloc_data.handle;
		ret = ioctl(ion, ION_IOC_SHARE, &share_data);
		if (ret < 0)
		{
			eDebug("[fb] ION_IOC_SHARE failed");
			goto err_ioc_free;
		}

		memset(&free_data, 0, sizeof(free_data));
		free_data.handle = alloc_data.handle;
		if (ioctl(ion, ION_IOC_FREE, &free_data) < 0)
			eDebug("[fb] ION_IOC_FREE failed");

		m_accel_fd = share_data.fd;
		lion=(unsigned char*)mmap(0, ACCEL_MEM_SIZE, PROT_WRITE|PROT_READ, MAP_SHARED, share_data.fd, 0);

		if (lion)
		{
			eDebug("[fb] %dkB available for acceleration surfaces (via ION).", ACCEL_MEM_SIZE / 1024);
			gAccel::getInstance()->setAccelMemorySpace(lion, phys_data.addr, ACCEL_MEM_SIZE);
		}
		else
		{
			close(m_accel_fd);
			eDebug("[fb] mmap lion failed");
err_ioc_free:
			eFatal("[fb] failed to allocate accel memory via ION!!!");
			m_accel_fd = -1;
			memset(&free_data, 0, sizeof(free_data));
			free_data.handle = alloc_data.handle;
			if (ioctl(ion, ION_IOC_FREE, &free_data) < 0)
				eDebug("[fb] ION_IOC_FREE %m");
		}
		close(ion);
	}
	else
	{
		eFatal("[fb] failed to open ION device node! no allocate accel memory available !!");
		m_accel_fd = -1;
	}
#else
	eDebug("[fb] %dk video mem", available/1024);
	lfb=(unsigned char*)mmap(0, available, PROT_WRITE|PROT_READ, MAP_SHARED, fbFd, 0);
#endif
#ifndef CONFIG_ION
	if (!lfb)
	{
		eDebug("[fb] mmap %m");
		goto nolfb;
	}
#endif

#if not defined(__sh__)
	showConsole(0);

	enableManualBlit();
#endif
	return;
nolfb:
	if (fbFd >= 0)
	{
		::close(fbFd);
		fbFd = -1;
	}
	eDebug("[fb] framebuffer not available");
	return;
}

#if not defined(__sh__)
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
#endif

int fbClass::SetMode(int nxRes, int nyRes, int nbpp)
{
#if defined(__sh__)
	xRes=nxRes;
	yRes=nyRes;
	bpp=32;
	m_number_of_pages = 1;
	topDiff=bottomDiff=leftDiff=rightDiff = 0;
#else
#ifdef CONFIG_ION
	/* unmap old framebuffer with old size */
	if (lfb)
		munmap(lfb, stride * screeninfo.yres_virtual);
#endif
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
			eDebug("[fb] FBIOPUT_VSCREENINFO %m");
			return -1;
		}
		eDebug("[fb] double buffering not available.");
	} else
		eDebug("[fb] double buffering available!");

	m_number_of_pages = screeninfo.yres_virtual / nyRes;
	eDebug("[fb] %d page(s) available!", m_number_of_pages);

#endif
	ioctl(fbFd, FBIOGET_VSCREENINFO, &screeninfo);

#if defined(__sh__)
	xResSc=screeninfo.xres;
	yResSc=screeninfo.yres;
	stride=xRes*4;
#else
	if ((screeninfo.xres!=nxRes) || (screeninfo.yres!=nyRes) || (screeninfo.bits_per_pixel!=nbpp))
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
		eDebug("[fb] FBIOGET_FSCREENINFO %m");
	}
	stride=fix.line_length;

#ifdef CONFIG_ION
    m_phys_mem = fix.smem_start;
    available = fix.smem_len;
	/* map new framebuffer */
	lfb=(unsigned char*)mmap(0, stride * screeninfo.yres_virtual, PROT_WRITE|PROT_READ, MAP_SHARED, fbFd, 0);
#endif

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
			eDebug("[fb] STMFBIO_BLT %m");
		}
		bltData.dst_top    = 0 + topDiff;
		bltData.dst_left   = xResSc/2 + leftDiff/2;
		bltData.dst_right  = xResSc + rightDiff/2;
		bltData.dst_bottom = yResSc + bottomDiff;
		if (ioctl(fbFd, STMFBIO_BLT, &bltData ) < 0)
		{
			eDebug("[fb] STMFBIO_BLT %m");
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
			eDebug("[fb] STMFBIO_BLT %m");
		}
		bltData.dst_top    = yResSc/2 + topDiff/2;
		bltData.dst_left   = 0 + leftDiff;
		bltData.dst_right  = xResSc + rightDiff;
		bltData.dst_bottom = yResSc + bottomDiff/2;
		if (ioctl(fbFd, STMFBIO_BLT, &bltData ) < 0)
		{
			eDebug("[fb] STMFBIO_BLT %m");
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
			eDebug("[fb] STMFBIO_BLT %m");
		}
	
	}

	if (ioctl(fbFd, STMFBIO_SYNC_BLITTER) < 0)
	{
		eDebug("[fb] STMFBIO_SYNC_BLITTER %m");
	}
#elif !defined(CONFIG_ION)
	if (m_manual_blit == 1) {
		if (ioctl(fbFd, FBIO_BLIT) < 0)
			eDebug("[fb] FBIO_BLIT %m");
	}
#endif
}

fbClass::~fbClass()
{
#ifdef CONFIG_ION
	if (m_accel_fd > -1)
		close(m_accel_fd);
#endif
	if (lfb)
	{
		msync(lfb, available, MS_SYNC);
		munmap(lfb, available);
	}
#if not defined(__sh__)
	showConsole(1);
	disableManualBlit();
#endif
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
#if not defined(__sh__)
	if (m_manual_blit == 1)
	{
		locked = 2;
		disableManualBlit();
	}
	else
#endif
		locked = 1;

#if defined(__sh__)
	outcfg.outputid = STMFBIO_OUTPUTID_MAIN;
	if (ioctl( fbFd, STMFBIO_GET_OUTPUT_CONFIG, &outcfg ) < 0)
		eDebug("[fb] STMFBIO_GET_OUTPUT_CONFIG %m");

	outinfo.outputid = STMFBIO_OUTPUTID_MAIN;
	if (ioctl( fbFd, STMFBIO_GET_OUTPUTINFO, &outinfo ) < 0)
		eDebug("[fb] STMFBIO_GET_OUTPUTINFO %m");

	planemode.layerid = 0;
	if (ioctl( fbFd, STMFBIO_GET_PLANEMODE, &planemode ) < 0)
		eDebug("[fb] STMFBIO_GET_PLANEMODE %m");

	if (ioctl( fbFd, STMFBIO_GET_VAR_SCREENINFO_EX, &infoex ) < 0)
		eDebug("[fb] STMFBIO_GET_VAR_SCREENINFO_EX %m");
#endif
	return fbFd;
}

void fbClass::unlock()
{
	if (!locked)
		return;
#if not defined(__sh__)
	if (locked == 2)  // re-enable manualBlit
		enableManualBlit();
#endif
	locked=0;
#if defined(__sh__)
	if (ioctl( fbFd, STMFBIO_SET_VAR_SCREENINFO_EX, &infoex ) < 0)
		eDebug("[fb] STMFBIO_SET_VAR_SCREENINFO_EX %m");

	if (ioctl( fbFd, STMFBIO_SET_PLANEMODE, &planemode ) < 0)
		eDebug("[fb] STMFBIO_SET_PLANEMODE %m");

	if (ioctl( fbFd, STMFBIO_SET_VAR_SCREENINFO_EX, &infoex ) < 0)
		eDebug("[fb] STMFBIO_SET_VAR_SCREENINFO_EX %m");

	if (ioctl( fbFd, STMFBIO_SET_OUTPUTINFO, &outinfo ) < 0)
		eDebug("[fb] STMFBIO_SET_OUTPUTINFO %m");

	if (ioctl( fbFd, STMFBIO_SET_OUTPUT_CONFIG, &outcfg ) < 0)
		eDebug("[fb] STMFBIO_SET_OUTPUT_CONFIG %m");

	memset(lfb, 0, stride*yRes);
#endif
	SetMode(xRes, yRes, bpp);
	PutCMAP();
}

#if not defined(__sh__)
void fbClass::enableManualBlit()
{
#ifndef CONFIG_ION
	unsigned char tmp = 1;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		eDebug("[fb] FBIO_SET_MANUAL_BLIT %m");
	else
		m_manual_blit = 1;
#endif
}

void fbClass::disableManualBlit()
{
#ifndef CONFIG_ION
	unsigned char tmp = 0;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		eDebug("[fb] FBIO_SET_MANUAL_BLIT %m");
	else
		m_manual_blit = 0;
#endif
}
#endif

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

