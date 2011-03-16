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

gAccel *gAccel::getInstance()
{
	return instance;
}
 
void gAccel::setAccelMemorySpace(void *addr, int phys_addr, int size)
{
	if (m_accel_allocation)
		delete[] m_accel_allocation;
	
	m_accel_size = size >> 12;
	
	m_accel_allocation = new int[m_accel_size];
	memset(m_accel_allocation, 0, sizeof(int)*m_accel_size);
	
	m_accel_addr = addr;
	m_accel_phys_addr = phys_addr;
}

int gAccel::blit(gSurface *dst, const gSurface *src, const eRect &p, const eRect &area, int flags)
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
		if (flags & (gPixmap::blitAlphaTest|gPixmap::blitAlphaBlend)) /* unsupported flags */
			return -1;
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

int gAccel::fill(gSurface *dst, const eRect &area, unsigned long col)
{
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

int gAccel::accelAlloc(void *&addr, int &phys_addr, int size)
{
	eDebug("accel %d bytes", size);
	if ((!size) || (!m_accel_allocation))
	{
		eDebug("size: %d, alloc %p", size, m_accel_allocation);
		addr = 0;
		phys_addr = 0;
		return -1;
	}
	
	size += 4095; size >>= 12;
	int i;
	
	int used = 0, free = 0, s = 0;
	for (i=0; i < m_accel_size; ++i)
	{
		if (m_accel_allocation[i] == 0)
			free++;
		else if (m_accel_allocation[i] == -1)
			used++;
		else
		{
			used++;
			s += m_accel_allocation[i];
		}
	}
	eDebug("accel memstat: used=%d kB, free %d kB, s %d kB", used * 4, free * 4, s * 4);

	for (i=0; i < m_accel_size - size; ++i)
	{
		int a;
		for (a=0; a<size; ++a)
			if (m_accel_allocation[i+a])
				break;
		if (a == size)
		{
			m_accel_allocation[i] = size;
			for (a=1; a<size; ++a)
				m_accel_allocation[i+a] = -1;
			addr = ((unsigned char*)m_accel_addr) + (i << 12);
			phys_addr = m_accel_phys_addr + (i << 12);
			return 0;
		}
	}
	eDebug("accel alloc failed\n");
	return -1;
}

void gAccel::accelFree(int phys_addr)
{
	phys_addr -= m_accel_phys_addr;
	phys_addr >>= 12;
	
	int size = m_accel_allocation[phys_addr];
	
	ASSERT(size > 0);
	
	while (size--)
		m_accel_allocation[phys_addr++] = 0;
}

eAutoInitP0<gAccel> init_gAccel(eAutoInitNumbers::graphic-2, "graphics acceleration manager");
