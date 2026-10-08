#include <cstring>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/accel.h>
#include <lib/base/eerror.h>
#ifdef DREAMNEXTGEN
#include <lib/gdi/dreamge2d.h>
#endif
#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>

#ifdef DREAMBCM_ION_ACCEL
#include <cerrno>
#include <cstdlib>
#include <map>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <interfaces/ion.h>
#include <time.h>
#endif

/* Apparently, surfaces must be 64-byte aligned */
#define ACCEL_ALIGNMENT_SHIFT	6
#define ACCEL_ALIGNMENT_MASK	((1<<ACCEL_ALIGNMENT_SHIFT)-1)

gAccel *gAccel::instance;

#if not defined(HAVE_HISILICON_ACCEL)
#define BCM_ACCEL
#endif

#ifdef HAVE_HISILICON_ACCEL 
extern int  dinobot_accel_init(void);
extern void dinobot_accel_close(void);
extern void dinobot_accel_blit(
		int src_addr, int src_width, int src_height, int src_stride, int src_format,
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int src_x, int src_y, int width, int height,
		int dst_x, int dst_y, int dwidth, int dheight,
		int pal_addr,int pal_size, int flags);
extern void dinobot_accel_fill(
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int x, int y, int width, int height,
		unsigned long color);
extern bool dinobot_accel_has_alphablending();
#endif

#ifdef BCM_ACCEL
extern int bcm_accel_init(void);
extern void bcm_accel_close(void);
extern int bcm_accel_blit(
		int src_addr, int src_width, int src_height, int src_stride, int src_format,
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int src_x, int src_y, int width, int height,
		int dst_x, int dst_y, int dwidth, int dheight,
		int pal_addr, int flags);
extern void bcm_accel_fill(
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int x, int y, int width, int height,
		unsigned long color);
extern bool bcm_accel_has_alphablending();
extern int bcm_accel_accumulate();
extern int bcm_accel_sync();
#endif

#ifdef DREAMBCM_ION_ACCEL

#define DREAMBCM_ION_HEAP_MASK 0x40
#define DREAMBCM_ION_ALIGN     0x1000

/*
 * Define DREAMBCM_RUNTIME_DEBUG for development builds. Production/beta builds
 * leave it undefined so ION stats and runtime test env switches compile to
 * fixed defaults.
 */

struct DreamBcmIonSurface
{
	void *addr;
	size_t size;
	int fd;
	unsigned long phys;
};

static std::map<gUnmanagedSurface*, DreamBcmIonSurface> s_dreambcm_ion_surfaces;
static int s_dreambcm_ion_fd = -1;
static bool s_dreambcm_ion_open_failed = false;
static bool s_dreambcm_ion_logged = false;

static unsigned int s_dreambcm_alloc_ok = 0;
static unsigned int s_dreambcm_alloc_fail = 0;
static unsigned int s_dreambcm_free_ok = 0;
static unsigned long long s_dreambcm_alloc_bytes = 0;
static unsigned int s_dreambcm_fill_ok = 0;
static unsigned int s_dreambcm_blit_ok = 0;
static unsigned int s_dreambcm_pagecopy_ok = 0;
static unsigned int s_dreambcm_sync_ok = 0;
static unsigned int s_dreambcm_sync_fail = 0;
static long long s_dreambcm_last_stats_ms = 0;

#ifdef DREAMBCM_RUNTIME_DEBUG
#define DREAMBCM_ACCEL_STAT_INC(x) do { ++(x); } while (0)
#define DREAMBCM_ACCEL_STAT_ADD(x, v) do { (x) += (v); } while (0)
#else
#define DREAMBCM_ACCEL_STAT_INC(x) do { } while (0)
#define DREAMBCM_ACCEL_STAT_ADD(x, v) do { } while (0)
#endif

static bool dreambcm_ion_disabled()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = std::getenv("DREAMBCM_ION_ACCEL");
	return value && value[0] == '0' && value[1] == 0;
#else
	return false;
#endif
}

static bool dreambcm_fill_disabled()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = std::getenv("DREAMBCM_FILL");
	return value && value[0] == '0' && value[1] == 0;
#else
	return false;
#endif
}

static bool dreambcm_stats_enabled()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = std::getenv("DREAMBCM_STATS");
	return value && !(value[0] == '0' && value[1] == 0);
#else
	return false;
#endif
}

static int dreambcm_stats_interval()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = std::getenv("DREAMBCM_STATS_INTERVAL");
	if (!value || !value[0])
		return 500;
	int interval = std::atoi(value);
	return interval > 0 ? interval : 500;
#else
	return 500;
#endif
}

static long long dreambcm_now_ms()
{
	struct timespec ts;
	if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0)
		return 0;
	return ((long long)ts.tv_sec * 1000LL) + ((long long)ts.tv_nsec / 1000000LL);
}

static void dreambcm_maybe_dump_stats(const char *reason)
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	if (!dreambcm_stats_enabled())
		return;

	long long now = dreambcm_now_ms();
	int interval = dreambcm_stats_interval();
	if (now && s_dreambcm_last_stats_ms && ((now - s_dreambcm_last_stats_ms) < interval))
		return;
	s_dreambcm_last_stats_ms = now;

	eDebug("[dreamBCM] stats reason=%s alloc=%u/%u free=%u live=%u bytes=%llu fill=%u blit=%u pagecopy=%u sync=%u/%u",
		reason ? reason : "-",
		s_dreambcm_alloc_ok, s_dreambcm_alloc_fail, s_dreambcm_free_ok,
		(unsigned int)s_dreambcm_ion_surfaces.size(), s_dreambcm_alloc_bytes,
		s_dreambcm_fill_ok, s_dreambcm_blit_ok, s_dreambcm_pagecopy_ok, s_dreambcm_sync_ok, s_dreambcm_sync_fail);
#else
	(void)reason;
#endif
}

static size_t dreambcm_page_align(size_t size)
{
	return (size + (DREAMBCM_ION_ALIGN - 1)) & ~(size_t)(DREAMBCM_ION_ALIGN - 1);
}

static int dreambcm_ion_get_fd()
{
	if (s_dreambcm_ion_fd >= 0)
		return s_dreambcm_ion_fd;
	if (s_dreambcm_ion_open_failed)
		return -1;

	s_dreambcm_ion_fd = open("/dev/ion", O_RDWR | O_CLOEXEC);
	if (s_dreambcm_ion_fd < 0)
	{
		s_dreambcm_ion_open_failed = true;
		eDebug("[dreamBCM] failed to open /dev/ion: %m");
	}
#ifdef DREAMBCM_RUNTIME_DEBUG
	else
	{
		eDebug("[dreamBCM] /dev/ion opened, per-surface allocator heap=0x%x align=0x%x", DREAMBCM_ION_HEAP_MASK, DREAMBCM_ION_ALIGN);
	}
#endif
	return s_dreambcm_ion_fd;
}

static int dreambcm_ion_alloc_surface(gUnmanagedSurface *surface, int stride, int size, bool debug)
{
	if (dreambcm_ion_disabled())
		return -1;

	int ion_fd = dreambcm_ion_get_fd();
	if (ion_fd < 0)
	{
		DREAMBCM_ACCEL_STAT_INC(s_dreambcm_alloc_fail);
		return -1;
	}

	struct ion_allocation_data alloc_data = {};
	struct ion_fd_data share_data = {};
	struct ion_phys_data phys_data = {};
	struct ion_handle_data free_data = {};
	bool have_handle = false;
	size_t map_size = 0;
	void *addr = MAP_FAILED;
	DreamBcmIonSurface ion_surface = {};

	alloc_data.len = size;
	alloc_data.align = DREAMBCM_ION_ALIGN;
	alloc_data.heap_id_mask = DREAMBCM_ION_HEAP_MASK;
	alloc_data.flags = 0;

	if (ioctl(ion_fd, ION_IOC_ALLOC, &alloc_data) < 0)
	{
		eDebug("[dreamBCM] ION_IOC_ALLOC failed len=%d heap=0x%x: %m", size, DREAMBCM_ION_HEAP_MASK);
		DREAMBCM_ACCEL_STAT_INC(s_dreambcm_alloc_fail);
		return -1;
	}
	have_handle = true;

	share_data.handle = alloc_data.handle;
	share_data.fd = -1;
	if (ioctl(ion_fd, ION_IOC_SHARE, &share_data) < 0)
	{
		eDebug("[dreamBCM] ION_IOC_SHARE failed handle=0x%x: %m", alloc_data.handle);
		goto fail;
	}

	phys_data.handle = alloc_data.handle;
	if (ioctl(ion_fd, ION_IOC_PHYS, &phys_data) < 0)
	{
		eDebug("[dreamBCM] ION_IOC_PHYS failed handle=0x%x: %m", alloc_data.handle);
		goto fail;
	}

	free_data.handle = alloc_data.handle;
	if (ioctl(ion_fd, ION_IOC_FREE, &free_data) < 0)
		eDebug("[dreamBCM] ION_IOC_FREE failed handle=0x%x: %m", alloc_data.handle);
	have_handle = false;

	map_size = phys_data.len ? phys_data.len : dreambcm_page_align(size);
	addr = mmap(0, map_size, PROT_WRITE | PROT_READ, MAP_SHARED, share_data.fd, 0);
	if (addr == MAP_FAILED)
	{
		eDebug("[dreamBCM] mmap failed fd=%d size=%zu: %m", share_data.fd, map_size);
		goto fail;
	}

	surface->data = static_cast<unsigned char*>(addr);
	surface->data_phys = static_cast<int>(phys_data.addr);
	surface->stride = stride;
	ion_surface.addr = addr;
	ion_surface.size = map_size;
	ion_surface.fd = share_data.fd;
	ion_surface.phys = phys_data.addr;
	s_dreambcm_ion_surfaces[surface] = ion_surface;
	DREAMBCM_ACCEL_STAT_INC(s_dreambcm_alloc_ok);
	DREAMBCM_ACCEL_STAT_ADD(s_dreambcm_alloc_bytes, map_size);

#ifdef DREAMBCM_RUNTIME_DEBUG
	if (!s_dreambcm_ion_logged || debug)
	{
		eDebug("[dreamBCM] ion surface allocator active heap=0x%x align=0x%x", DREAMBCM_ION_HEAP_MASK, DREAMBCM_ION_ALIGN);
		s_dreambcm_ion_logged = true;
	}
#endif
	if (debug)
		eDebug("[dreamBCM] surface alloc %p size=%d map=%zu phys=0x%lx fd=%d", surface, size, map_size, phys_data.addr, share_data.fd);
	dreambcm_maybe_dump_stats("alloc");
	return 0;

fail:
	if (share_data.fd >= 0)
		close(share_data.fd);
	if (have_handle)
	{
		free_data.handle = alloc_data.handle;
		ioctl(ion_fd, ION_IOC_FREE, &free_data);
	}
	DREAMBCM_ACCEL_STAT_INC(s_dreambcm_alloc_fail);
	dreambcm_maybe_dump_stats("alloc-fail");
	return -1;
}

static bool dreambcm_ion_free_surface(gUnmanagedSurface *surface, bool debug)
{
	std::map<gUnmanagedSurface*, DreamBcmIonSurface>::iterator it = s_dreambcm_ion_surfaces.find(surface);
	if (it == s_dreambcm_ion_surfaces.end())
		return false;

	DreamBcmIonSurface ion = it->second;
	if (debug)
		eDebug("[dreamBCM] surface free %p phys=0x%lx fd=%d", surface, ion.phys, ion.fd);
	munmap(ion.addr, ion.size);
	close(ion.fd);
	s_dreambcm_ion_surfaces.erase(it);
	DREAMBCM_ACCEL_STAT_INC(s_dreambcm_free_ok);
	dreambcm_maybe_dump_stats("free");
	surface->data = 0;
	surface->data_phys = 0;
	return true;
}

static void dreambcm_ion_release_all(bool relocate)
{
	unsigned int released = 0;
	while (!s_dreambcm_ion_surfaces.empty())
	{
		std::map<gUnmanagedSurface*, DreamBcmIonSurface>::iterator it = s_dreambcm_ion_surfaces.begin();
		gUnmanagedSurface *surface = it->first;
		DreamBcmIonSurface ion = it->second;
		unsigned char *new_data = 0;

		if (relocate && surface && surface->data)
		{
			int size = surface->y * surface->stride;
			new_data = new unsigned char[size];
			memcpy(new_data, surface->data, size);
		}
		munmap(ion.addr, ion.size);
		close(ion.fd);
		++released;
		if (surface)
		{
			surface->data = new_data;
			surface->data_phys = 0;
		}
		s_dreambcm_ion_surfaces.erase(it);
	}
	s_dreambcm_free_ok += released;
	dreambcm_maybe_dump_stats("release-all");
}

#endif

gAccel::gAccel():
	m_accel_addr(0),
	m_accel_phys_addr(0),
	m_accel_size(0)
{
	instance = this;

#ifdef BCM_ACCEL
	m_bcm_accel_state = bcm_accel_init();
#endif
#ifdef HAVE_HISILICON_ACCEL
	dinobot_accel_init();
#endif
}

gAccel::~gAccel()
{
#ifdef BCM_ACCEL
	bcm_accel_close();
#endif
#ifdef DREAMBCM_ION_ACCEL
	dreambcm_ion_release_all(false);
	if (s_dreambcm_ion_fd >= 0)
		close(s_dreambcm_ion_fd);
#endif
#ifdef HAVE_HISILICON_ACCEL
	dinobot_accel_close();
#endif
#ifdef DREAMNEXTGEN
	dreamGE2DReset();
#endif
	instance = 0;
}

void gAccel::dumpDebug()
{
	if(!m_accel_debug)
		return;
	eDebug("[gAccel] info --");
#ifdef DREAMNEXTGEN
	dreamGE2DReleaseAccelMemory();
#endif
	for (MemoryBlockList::const_iterator it = m_accel_allocation.begin();
		 it != m_accel_allocation.end();
		 ++it)
	 {
		 gUnmanagedSurface *surface = it->surface;
		 if (surface)
			eDebug("[gAccel] surface: (%d (%dk), %d (%dk)) %p %dx%d:%d",
					it->index, it->index >> (10 - ACCEL_ALIGNMENT_SHIFT),
					it->size, it->size >> (10 - ACCEL_ALIGNMENT_SHIFT),
					surface, surface->stride, surface->y, surface->bpp);
		else
			eDebug("[gAccel]    free: (%d (%dk), %d (%dk))",
					it->index, it->index >> (10 - ACCEL_ALIGNMENT_SHIFT),
					it->size, it->size >> (10 - ACCEL_ALIGNMENT_SHIFT));
	 }
	eDebug("--");
}

void gAccel::releaseAccelMemorySpace()
{
	eSingleLocker lock(m_allocation_lock);
	dumpDebug();
#ifdef DREAMBCM_ION_ACCEL
	dreambcm_ion_release_all(true);
#endif
	for (MemoryBlockList::const_iterator it = m_accel_allocation.begin();
		 it != m_accel_allocation.end();
		 ++it)
	{
		gUnmanagedSurface *surface = it->surface;
		if (surface != NULL)
		{
			int size = surface->y * surface->stride;
			if(m_accel_debug)
				eDebug("[gAccel] %s: Re-locating %p->%x(%p) %dx%d:%d", __func__, surface, surface->data_phys, surface->data, surface->x, surface->y, surface->bpp);
			unsigned char *new_data = new unsigned char [size];
			memcpy(new_data, surface->data, size);
			surface->data = new_data;
			surface->data_phys = 0;
		}
	}
	m_accel_allocation.clear();
	m_accel_size = 0;
}

void gAccel::setAccelMemorySpace(void *addr, int phys_addr, int size)
{
	if (size > 0)
	{
		eSingleLocker lock(m_allocation_lock);
		m_accel_size = size >> ACCEL_ALIGNMENT_SHIFT;
		m_accel_addr = addr;
		m_accel_phys_addr = phys_addr;
		m_accel_allocation.push_back(MemoryBlock(NULL, 0, m_accel_size));
		dumpDebug();
	}
}


#ifdef DREAMBCM_ION_ACCEL
static bool dreambcm_indexed_palette_color_swap_enabled()
{
#ifdef DREAMBCM_RUNTIME_DEBUG
	const char *value = getenv("DREAMBCM_INDEXED_PALETTE_COLOR_SWAP");
	if (!value || !value[0])
		return true;
	if (value[0] == '0' && value[1] == 0)
		return false;
	if (!strcmp(value, "no") || !strcmp(value, "false") || !strcmp(value, "off"))
		return false;
	return true;
#else
	return true;
#endif
}

static unsigned int dreambcm_indexed_palette_color(unsigned int color)
{
	/*
	 * Enigma2 stores indexed PNG palette entries as ARGB colors. The old
	 * Broadcom indexed path only needed the alpha inversion below. The DM9x0
	 * DreamOS-style indexed composition path uses the same palette format
	 * register but interprets RGB channel order differently for these PNG
	 * palettes. Swap R/B to keep paletted PNG colors correct.
	 */
	color ^= 0xFF000000;

	if (!dreambcm_indexed_palette_color_swap_enabled())
		return color;

	return (color & 0xFF00FF00) |
		((color & 0x00FF0000) >> 16) |
		((color & 0x000000FF) << 16);
}
#endif

bool gAccel::hasAlphaBlendingSupport()
{
#ifdef BCM_ACCEL
	return bcm_accel_has_alphablending();
#endif
#ifdef HAVE_HISILICON_ACCEL
	return dinobot_accel_has_alphablending();
#else
#ifdef DREAMNEXTGEN
	return dreamGE2DHasAlphaBlendingSupport();
#endif
	return false;
#endif
}

int gAccel::blit(gUnmanagedSurface *dst, gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags)
{
#ifdef DREAMNEXTGEN
	if (dreamGE2DBlit(dst, src, p, area, flags))
		return 0;
	if (dreamGE2DIsManagedSurface(dst) || dreamGE2DIsManagedSurface(src))
		return -1;
#endif

#ifdef BCM_ACCEL
	if (!m_bcm_accel_state)
	{
		unsigned int pal_addr = 0;
		int src_format = 0;
		if (src->bpp == 32)
			src_format = 0;
		else if ((src->bpp == 8) && src->clut.data)
		{
			src_format = 1;
			/* sync pal */
			if (src->clut.data_phys == 0)
			{
				/* sync pal */
				pal_addr = src->stride * src->y;
				unsigned int *pal = (unsigned int*)(((unsigned char*)src->data) + pal_addr);
				pal_addr += src->data_phys;
				for (int i = 0; i < src->clut.colors; ++i)
#ifdef DREAMBCM_ION_ACCEL
					*pal++ = dreambcm_indexed_palette_color(src->clut.data[i].argb());
#else
					*pal++ = src->clut.data[i].argb() ^ 0xFF000000;
#endif
				src->clut.data_phys = pal_addr;
			}
			else
			{
				pal_addr = src->clut.data_phys;
			}
		} else
			return -1; /* unsupported source format */

		int ret = bcm_accel_blit(
			src->data_phys, src->x, src->y, src->stride, src_format,
			dst->data_phys, dst->x, dst->y, dst->stride,
			area.left(), area.top(), area.width(), area.height(),
			p.x(), p.y(), p.width(), p.height(),
			pal_addr, flags);
		if (ret)
			return ret;
	#ifdef DREAMBCM_ION_ACCEL
		DREAMBCM_ACCEL_STAT_INC(s_dreambcm_blit_ok);
		dreambcm_maybe_dump_stats("blit");
	#endif
		return 0;
	}
#endif
#ifdef HAVE_HISILICON_ACCEL
		unsigned long pal_addr = 0;
		unsigned int  pal_size = 0;
		int src_format = 0;
		if (src->bpp == 32)
			src_format = 0;
		else if ((src->bpp == 8) && src->clut.data)
		{
			src_format = 1;
			pal_size = src->clut.colors*4*16/16;
			pal_addr = (unsigned long)new unsigned char [pal_size];
			/* sync pal */
			if (src->clut.data_phys == 0)
			{
				/* sync pal */
				unsigned long *pal = (unsigned long*)pal_addr;
				for (int i = 0; i < src->clut.colors; ++i)
				    *pal++ = src->clut.data[i].argb() ^ 0xFF000000;
				src->clut.data_phys = pal_addr;
				eDebug("!!!!!!!!!![gAccel] pal_addr1 %x clors=%d!!!!!!!!!!",pal_addr,src->clut.colors);
			}
			else
			{
				//memcpy((void*)pal_addr ,(void *)src->clut.data_phys,pal_size);
				unsigned long *pal = (unsigned long*)pal_addr;
				for (int i = 0; i < src->clut.colors; ++i)
				    *pal++ = src->clut.data[i].argb() ^ 0xFF000000;
				eDebug("!!!!!!!!!![gAccel] pal_addr2 %x clors=%d!!!!!!!!!!",pal_addr,src->clut.colors);
			}
		} else
			return -1; /* unsupported source format */

		dinobot_accel_blit(
			src->data_phys, src->x, src->y, src->stride, src_format,
			dst->data_phys, dst->x, dst->y, dst->stride,
			area.left(), area.top(), area.width(), area.height(),
			p.x(), p.y(), p.width(), p.height(),
			pal_addr, pal_size,flags);

		if(pal_size && pal_addr)
		{
			delete (unsigned char *)pal_addr;
		}
		return 0;
#endif
	return -1;
}

int gAccel::fill(gUnmanagedSurface *dst, const eRect &area, unsigned long col)
{
#ifdef FORCE_NO_FILL_ACCELERATION
	return -1;
#endif
#ifdef DREAMBCM_ION_ACCEL
	if (dreambcm_fill_disabled())
		return -1;
#endif

#ifdef DREAMNEXTGEN
	if (dreamGE2DFill(dst, area, col))
		return 0;
	if (dreamGE2DIsManagedSurface(dst))
		return -1;
#endif

#ifdef BCM_ACCEL
	if (!m_bcm_accel_state) {
		bcm_accel_fill(
			dst->data_phys, dst->x, dst->y, dst->stride,
			area.left(), area.top(), area.width(), area.height(),
			col);
	#ifdef DREAMBCM_ION_ACCEL
		DREAMBCM_ACCEL_STAT_INC(s_dreambcm_fill_ok);
		dreambcm_maybe_dump_stats("fill");
	#endif
		return 0;
	}
#endif

#ifdef HAVE_HISILICON_ACCEL
	dinobot_accel_fill(
		dst->data_phys, dst->x, dst->y, dst->stride,
		area.left(), area.top(), area.width(), area.height(),
		col);
	return 0;
#endif
	return -1;
}

int gAccel::accumulate()
{
#ifdef BCM_ACCEL
	if (!m_bcm_accel_state)
	{
		return bcm_accel_accumulate();
	}
#endif
	return -1;
}

int gAccel::sync()
{
#ifdef BCM_ACCEL
	if (!m_bcm_accel_state)
	{
		int ret = bcm_accel_sync();
	#ifdef DREAMBCM_ION_ACCEL
		if (ret)
			DREAMBCM_ACCEL_STAT_INC(s_dreambcm_sync_fail);
		else
			DREAMBCM_ACCEL_STAT_INC(s_dreambcm_sync_ok);
		dreambcm_maybe_dump_stats("sync");
	#endif
		return ret;
	}
#endif
	return -1;
}

void gAccel::dreamBCMPagecopyStat()
{
#ifdef DREAMBCM_ION_ACCEL
	DREAMBCM_ACCEL_STAT_INC(s_dreambcm_pagecopy_ok);
	dreambcm_maybe_dump_stats("pagecopy");
#endif
}

int gAccel::accelAlloc(gUnmanagedSurface* surface)
{
	int stride = (surface->stride + ACCEL_ALIGNMENT_MASK) & ~ACCEL_ALIGNMENT_MASK;
	int size = stride * surface->y;
	if (!size)
	{
		eDebug("[gAccel] accelAlloc called with size 0");
		return -2;
	}
	if (surface->bpp == 8)
		size += 256 * 4;
	else if (surface->bpp != 32)
	{
		eDebug("[gAccel] Accel does not support bpp=%d", surface->bpp);
		return -4;
	}

	if(m_accel_debug)
		eDebug("[gAccel] [%s] %p size=%d %dx%d:%d", __func__, surface, size, surface->x, surface->y, surface->bpp);

#ifdef DREAMBCM_ION_ACCEL
	if (!m_bcm_accel_state)
		return dreambcm_ion_alloc_surface(surface, stride, size, m_accel_debug);
#endif

#ifndef DREAMNEXTGEN
	size += ACCEL_ALIGNMENT_MASK;
	size >>= ACCEL_ALIGNMENT_SHIFT;

	eSingleLocker lock(m_allocation_lock);

	for (MemoryBlockList::iterator it = m_accel_allocation.begin();
		 it != m_accel_allocation.end();
		 ++it)
	{
		if ((it->surface == NULL) && (it->size >= size))
		{
			int remain = it->size - size;
			if (remain)
			{
				/* Add empty item before this one with the remaining memory */
				m_accel_allocation.insert(it, MemoryBlock(NULL, it->index, remain));
				/* it points behind the new item */
				it->index += remain;
				it->size = size;
			}
			it->surface = surface;
			surface->data = ((unsigned char*)m_accel_addr) + (it->index << ACCEL_ALIGNMENT_SHIFT);
			surface->data_phys = m_accel_phys_addr + (it->index << ACCEL_ALIGNMENT_SHIFT);
			surface->stride = stride;
			dumpDebug();
			return 0;
		}
	}

	eDebug("[gAccel] accel alloc failed\n");
	return -3;
#else
	if (surface->bpp == 32 && dreamGE2DAllocSurface(surface, stride, size))
		return 0;

	/* Fall back to normal heap allocation in gSurface instead of using the tiny
	 * framebuffer tail area. On 1080p triple buffering this area is only a few
	 * hundred KiB and creates avoidable accelAlloc noise. Return success with
	 * surface->data left empty so gSurface allocates its normal CPU buffer without
	 * printing an acceleration error.
	 */
	if(m_accel_debug)
		eDebug("[gAccel] dreamGE2D accelAlloc unavailable, using CPU surface fallback");
	return 0;
#endif
}

void gAccel::accelFree(gUnmanagedSurface* surface)
{
#ifdef DREAMNEXTGEN
	if (dreamGE2DFreeSurface(surface))
		return;
#endif
	int phys_addr = surface->data_phys;
	if (phys_addr != 0)
	{
#ifdef DREAMBCM_ION_ACCEL
		if (dreambcm_ion_free_surface(surface, m_accel_debug))
			return;
#endif
		if(m_accel_debug)
			eDebug("[gAccel] [%s] %p->%x %dx%d:%d", __func__, surface, surface->data_phys, surface->x, surface->y, surface->bpp);
		/* The lock scope is "good enough", the only other method that
		 * might alter data_phys is the global release, and that will
		 * be called in a safe context. So don't obtain the lock. */
		eSingleLocker lock(m_allocation_lock);

		phys_addr -= m_accel_phys_addr;
		phys_addr >>= ACCEL_ALIGNMENT_SHIFT;

		for (MemoryBlockList::iterator it = m_accel_allocation.begin();
			 it != m_accel_allocation.end();
			 ++it)
		{
			if (it->surface == surface)
			{
				ASSERT(it->index == phys_addr);
				/* Mark as free */
				it->surface = NULL;
				MemoryBlockList::iterator current = it;
				/* Merge with previous item if possible */
				if (it != m_accel_allocation.begin())
				{
					MemoryBlockList::iterator previous = it;
					--previous;
					if (previous->surface == NULL)
					{
						current = previous;
						previous->size += it->size;
						m_accel_allocation.erase(it);
					}
				}
				/* Merge with next item if possible */
				if (current != m_accel_allocation.end())
				{
					it = current;
					++it;
					if ((it != m_accel_allocation.end()) && (it->surface == NULL))
					{
						current->size += it->size;
						m_accel_allocation.erase(it);
					}
				}
				break;
			}
		}
		/* Mark as disposed (yes, even if it wasn't in our administration) */
		surface->data = 0;
		surface->data_phys = 0;
		dumpDebug();
	}
}

eAutoInitP0<gAccel> init_gAccel(eAutoInitNumbers::graphic-2, "graphics acceleration manager");
