#include <cstring>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/accel.h>
#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>

gAccel *gAccel::instance;
#define BCM_ACCEL

#ifdef ATI_ACCEL
extern int ati_accel_init(void);
extern void ati_accel_close(void);
extern void ati_accel_blit(
		int src_addr, int src_width, int src_height, int src_stride,
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int src_x, int src_y, int width, int height,
		int dst_x, int dst_y);
extern void ati_accel_fill(
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int x, int y, int width, int height,
		unsigned long color);
#endif
#ifdef BCM_ACCEL
extern int bcm_accel_init(void);
extern void bcm_accel_close(void);
extern void bcm_accel_blit(
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
#endif

gAccel::gAccel()
{
	m_accel_addr = 0;
	m_accel_phys_addr = 0;
	m_accel_size = 0;
	m_accel_allocation = 0;
	instance = this;

#ifdef ATI_ACCEL	
	ati_accel_init();
#endif
#ifdef BCM_ACCEL	
	m_bcm_accel_state = bcm_accel_init();
#endif
}

gAccel::~gAccel()
{
#ifdef ATI_ACCEL
	ati_accel_close();
#endif
#ifdef BCM_ACCEL
	bcm_accel_close();
#endif
	instance = 0;
}

#ifdef ACCEL_DEBUG
static void dumpAccel(gUnmanagedSurface **m_accel_allocation, int m_accel_size)
{
	if (m_accel_allocation)
	{
		gUnmanagedSurface *previous = NULL;
		for (int i=0; i < m_accel_size; ++i)
		{
			gUnmanagedSurface *surface = m_accel_allocation[i];
			if ((surface != NULL) && (surface != previous))
			{
				eDebug("accel surface: %p ->%x(%p) %dx%d:%d",
					surface, surface->data_phys, surface->data,
					surface->stride, surface->y, surface->bpp);
				previous = surface;
			}
		}
	}
}
#else
static inline void dumpAccel(gUnmanagedSurface **m_accel_allocation, int m_accel_size) {}
#endif

void gAccel::releaseAccelMemorySpace()
{
	eSingleLocker lock(m_allocation_lock);
	dumpAccel(m_accel_allocation, m_accel_size);

	if (m_accel_allocation)
	{
		gUnmanagedSurface *previous = NULL;
		for (int i=0; i < m_accel_size; ++i)
		{
			gUnmanagedSurface *surface = m_accel_allocation[i];
			if ((surface != NULL) && (surface != previous))
			{
				int size = surface->y * surface->stride;
#ifdef ACCEL_DEBUG
				eDebug("%s: Re-locating %p->%x(%p) %dx%d:%d", __func__, surface, surface->data_phys, surface->data, surface->x, surface->y, surface->bpp);
#endif
				unsigned char *new_data = new unsigned char [size];
				memcpy(new_data, surface->data, size);
				surface->data = new_data;
				surface->data_phys = 0;
				previous = surface;
			}
		}
		delete[] m_accel_allocation;
		m_accel_allocation = NULL;
		m_accel_size = 0;
	}
}

void gAccel::setAccelMemorySpace(void *addr, int phys_addr, int size)
{
	if (size > 0)
	{
		eSingleLocker lock(m_allocation_lock);
		m_accel_size = size >> 12;
		m_accel_allocation = new gUnmanagedSurface*[m_accel_size];
		memset(m_accel_allocation, 0, m_accel_size * sizeof(gUnmanagedSurface*));
		m_accel_addr = addr;
		m_accel_phys_addr = phys_addr;
	}
}

bool gAccel::hasAlphaBlendingSupport()
{
#ifdef BCM_ACCEL
	return bcm_accel_has_alphablending();
#else
	return false;
#endif
}

int gAccel::blit(gUnmanagedSurface *dst, const gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags)
{
#ifdef ATI_ACCEL
	ati_accel_blit(
		src->data_phys, src->x, src->y, src->stride,
		dst->data_phys, dst->x, dst->y, dst->stride, 
		area.left(), area.top(), area.width(), area.height(),
		p.x(), p.y());
	return 0;
#endif
#ifdef BCM_ACCEL
	if (!m_bcm_accel_state)
	{
		unsigned long pal_addr = 0;
		int src_format = 0;
		if (src->bpp == 32)
			src_format = 0;
		else if ((src->bpp == 8) && src->clut.data)
		{
			src_format = 1;
			/* sync pal */
			int i;
			pal_addr = src->stride * src->y;
			unsigned long *pal = (unsigned long*)(((unsigned char*)src->data) + pal_addr);
			pal_addr += src->data_phys;
			for (i = 0; i < src->clut.colors; ++i)
				*pal++ = src->clut.data[i].argb() ^ 0xFF000000;
		} else
			return -1; /* unsupported source format */

		bcm_accel_blit(
			src->data_phys, src->x, src->y, src->stride, src_format,
			dst->data_phys, dst->x, dst->y, dst->stride, 
			area.left(), area.top(), area.width(), area.height(),
			p.x(), p.y(), p.width(), p.height(),
			pal_addr, flags);
		return 0;
	}
#endif
	return -1;
}

int gAccel::fill(gUnmanagedSurface *dst, const eRect &area, unsigned long col)
{
#ifdef FORCE_NO_FILL_ACCELERATION
	return -1;
#endif
#ifdef ATI_ACCEL
	ati_accel_fill(
		dst->data_phys, dst->x, dst->y, dst->stride, 
		area.left(), area.top(), area.width(), area.height(),
		col);
	return 0;
#endif
#ifdef BCM_ACCEL
	if (!m_bcm_accel_state) {
		bcm_accel_fill(
			dst->data_phys, dst->x, dst->y, dst->stride,
			area.left(), area.top(), area.width(), area.height(),
			col);
		return 0;
	}
#endif
	return -1;
}

int gAccel::accelAlloc(gUnmanagedSurface* surface)
{
	eSingleLocker lock(m_allocation_lock);
	if (!m_accel_allocation)
	{
		eDebug("m_accel_allocation not set");
		return -1;
	}
	int stride = (surface->stride + 63) & ~63;
	int size = stride * surface->y;
	if (!size)
	{
		eDebug("accelAlloc called with size 0");
		return -2;
	}
	if (surface->bpp == 8)
		size += 256 * 4;

#ifdef ACCEL_DEBUG
	eDebug("[%s] %p size=%d %dx%d:%d", __func__, surface, size, surface->x, surface->y, surface->bpp);
#endif

	size += 4095;
	size >>= 12;
	for (int i = m_accel_size - size; i >= 0 ; --i)
	{
		int a;
		for (a=0; a<size; ++a)
			if (m_accel_allocation[i+a])
				break;
		if (a == size)
		{
			m_accel_allocation[i] = surface;
			for (a=1; a<size; ++a)
				m_accel_allocation[i+a] = surface;
			surface->data = ((unsigned char*)m_accel_addr) + (i << 12);
			surface->data_phys = m_accel_phys_addr + (i << 12);
			surface->stride = stride;
			dumpAccel(m_accel_allocation, m_accel_size);
			return 0;
		}
	}
	eDebug("accel alloc failed\n");
	return -3;
}

void gAccel::accelFree(gUnmanagedSurface* surface)
{
	int phys_addr = surface->data_phys;
	if (phys_addr != 0)
	{
		/* The lock scope is "good enough", the only other method that
		 * might alter data_phys is the global release, and that will
		 * be called in a safe context. So don't obtain the lock. */
		eSingleLocker lock(m_allocation_lock);
		
		phys_addr -= m_accel_phys_addr;
		phys_addr >>= 12;

		ASSERT(m_accel_allocation[phys_addr] == surface);

		int count = 0;
		while (m_accel_allocation[phys_addr] == surface)
		{
			++count;
			m_accel_allocation[phys_addr++] = NULL;
		}
#ifdef ACCEL_DEBUG
		eDebug("[%s] %p->%x (%d) %dx%d:%d", __func__, surface, surface->data_phys, count, surface->x, surface->y, surface->bpp);
#endif
		surface->data = 0;
		surface->data_phys = 0;

		dumpAccel(m_accel_allocation, m_accel_size);
	}
}

eAutoInitP0<gAccel> init_gAccel(eAutoInitNumbers::graphic-2, "graphics acceleration manager");
