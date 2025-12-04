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

	available = fix.smem_len;
	m_phys_mem = fix.smem_start;
	eDebug("[fb] %s: %dk video mem", fb, available/1024);
#if defined(CONFIG_ION)
	/* allocate accel memory here... its independent from the framebuffer */
	ion = open("/dev/ion", O_RDWR | O_CLOEXEC);
	if (ion >= 0)
	{
		struct ion_allocation_data alloc_data = {};
		struct ion_fd_data share_data = {};
		struct ion_handle_data free_data = {};
		struct ion_phys_data phys_data = {};
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

	showConsole(0);

	enableManualBlit();
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
#ifdef CONFIG_ION
	/* unmap old framebuffer with old size */
	if (lfb)
		munmap(lfb, stride * screeninfo.yres_virtual);
#endif

	screeninfo.xres_virtual=screeninfo.xres=nxRes;
#if defined(CONFIG_ION) || defined(DREAMNEXTGEN)
	screeninfo.yres = nyRes;
	screeninfo.yres_virtual = nyRes * 3;
#else
	screeninfo.yres_virtual=(screeninfo.yres=nyRes)*2;
#endif
	screeninfo.activate = FB_ACTIVATE_ALL;
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

#if defined(CONFIG_ION) || defined(DREAMNEXTGEN)
	if (ioctl(fbFd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
	{
		screeninfo.yres_virtual = nyRes * 2;

		if (ioctl(fbFd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
		{
			// try single buffering
			screeninfo.yres_virtual = nyRes;

			if (ioctl(fbFd, FBIOPUT_VSCREENINFO, &screeninfo)<0)
			{
				eDebug("[fb] FBIOPUT_VSCREENINFO %m");
				return -1;
			}
			eDebug("[fb] double buffering not available.");
		}
	}

	m_number_of_pages = screeninfo.yres_virtual / nyRes;
	if (m_number_of_pages >= 3)
		eDebug("[fb] triple buffering available!");
	else if (m_number_of_pages == 2)
		eDebug("[fb] double buffering available!");
	else
		eDebug("[fb] using single buffer");
	eDebug("[fb] %d page(s) available!", m_number_of_pages);
#else
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
	}
	else
		eDebug("[fb] double buffering available!");

	m_number_of_pages = screeninfo.yres_virtual / nyRes;
	eDebug("[fb] %d page(s) available!", m_number_of_pages);
#endif

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
#if !defined(CONFIG_ION)
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
	if (fbFd < 0) return;
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
	if (fbFd < 0) return;
	if (ioctl(fbFd,FBIO_SET_MANUAL_BLIT, &tmp)<0)
		eDebug("[fb] FBIO_SET_MANUAL_BLIT %m");
	else
		m_manual_blit = 0;
#endif
}


