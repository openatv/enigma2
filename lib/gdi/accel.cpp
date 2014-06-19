#include <cstring>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/accel.h>
#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>

/* Apparently, surfaces must be 64-byte aligned */
#define ACCEL_ALIGNMENT_SHIFT	6
#define ACCEL_ALIGNMENT_MASK	((1<<ACCEL_ALIGNMENT_SHIFT)-1)

// #define ACCEL_DEBUG

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

gAccel::gAccel():
	m_accel_addr(0),
	m_accel_phys_addr(0),
	m_accel_size(0)
{
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
void gAccel::dumpDebug()
{
	eDebug("-- gAccel info --");
	for (MemoryBlockList::const_iterator it = m_accel_allocation.begin();
		 it != m_accel_allocation.end();
		 ++it)
	 {
		 gUnmanagedSurface *surface = it->surface;
		 if (surface)
			eDebug("surface: (%d (%dk), %d (%dk)) %p %dx%d:%d",
					it->index, it->index >> (10 - ACCEL_ALIGNMENT_SHIFT),
					it->size, it->size >> (10 - ACCEL_ALIGNMENT_SHIFT),
					surface, surface->stride, surface->y, surface->bpp);
		else
			eDebug("   free: (%d (%dk), %d (%dk))",
					it->index, it->index >> (10 - ACCEL_ALIGNMENT_SHIFT),
					it->size, it->size >> (10 - ACCEL_ALIGNMENT_SHIFT));
	 }
	eDebug("--");
}
#else
void gAccel::dumpDebug() {}
#endif

void gAccel::releaseAccelMemorySpace()
{
	eSingleLocker lock(m_allocation_lock);
	dumpDebug();
	for (MemoryBlockList::const_iterator it = m_accel_allocation.begin();
		 it != m_accel_allocation.end();
		 ++it)
	{
		gUnmanagedSurface *surface = it->surface;
		if (surface != NULL)
		{
			int size = surface->y * surface->stride;
#ifdef ACCEL_DEBUG
			eDebug("%s: Re-locating %p->%x(%p) %dx%d:%d", __func__, surface, surface->data_phys, surface->data, surface->x, surface->y, surface->bpp);
#endif
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

bool gAccel::hasAlphaBlendingSupport()
{
#ifdef BCM_ACCEL
	return bcm_accel_has_alphablending();
#else
	return false;
#endif
}

int gAccel::blit(gUnmanagedSurface *dst, gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags)
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
			if (src->clut.data_phys == 0)
			{
				/* sync pal */
				pal_addr = src->stride * src->y;
				unsigned long *pal = (unsigned long*)(((unsigned char*)src->data) + pal_addr);
				pal_addr += src->data_phys;
				for (int i = 0; i < src->clut.colors; ++i)
					*pal++ = src->clut.data[i].argb() ^ 0xFF000000;
				src->clut.data_phys = pal_addr;
			}
			else
			{
				pal_addr = src->clut.data_phys;
			}
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
	int stride = (surface->stride + ACCEL_ALIGNMENT_MASK) & ~ACCEL_ALIGNMENT_MASK;
	int size = stride * surface->y;
	if (!size)
	{
		eDebug("accelAlloc called with size 0");
		return -2;
	}
	if (surface->bpp == 8)
		size += 256 * 4;
	else if (surface->bpp != 32)
	{
		eDebug("Accel does not support bpp=%d", surface->bpp);
		return -4;
	}

#ifdef ACCEL_DEBUG
	eDebug("[%s] %p size=%d %dx%d:%d", __func__, surface, size, surface->x, surface->y, surface->bpp);
#endif

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

	eDebug("accel alloc failed\n");
	return -3;
}

void gAccel::accelFree(gUnmanagedSurface* surface)
{
	int phys_addr = surface->data_phys;
	if (phys_addr != 0)
	{
#ifdef ACCEL_DEBUG
		eDebug("[%s] %p->%x %dx%d:%d", __func__, surface, surface->data_phys, surface->x, surface->y, surface->bpp);
#endif
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
