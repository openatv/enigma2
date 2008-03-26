#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/accel.h>
#include <lib/base/eerror.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>

gAccel *gAccel::instance;

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
}

gAccel::~gAccel()
{
#ifdef ATI_ACCEL
	ati_accel_close();
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

int gAccel::blit(gSurface *dst, const gSurface *src, const ePoint &p, const eRect &area, int flags)
{
#ifdef ATI_ACCEL
	ati_accel_blit(
		src->data_phys, src->x, src->y, src->stride,
		dst->data_phys, dst->x, dst->y, dst->stride, 
		area.left(), area.top(), area.width(), area.height(),
		p.x(), p.y());
	return 0;
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
	return -1;
}

int gAccel::accelAlloc(void *&addr, int &phys_addr, int size)
{
	if ((!size) || (!m_accel_allocation))
	{
		eDebug("size: %d, alloc %p", size, m_accel_allocation);
		addr = 0;
		phys_addr = 0;
		return -1;
	}
	
	size += 4095; size >>= 12;
	int i;

	for (i=0; i < m_accel_size - size; ++i)
	{
		int a;
		for (a=0; a<size; ++a)
			if (m_accel_allocation[i+a])
				break;
		if (a == size)
		{
			m_accel_allocation[i+a] = size;
			for (a=1; a<size; ++a)
				m_accel_allocation[i+a] = -1;
			addr = ((unsigned char*)m_accel_addr) + (i << 12);
			phys_addr = m_accel_phys_addr + (i << 12);
			return 0;
		}
	}
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
