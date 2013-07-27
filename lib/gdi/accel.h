#ifndef __lib_gdi_accel_h
#define __lib_gdi_accel_h

#include <base/elock.h>

struct gUnmanagedSurface;
class eRect;
class ePoint;

class gAccel
{
public:
	static gAccel* getInstance() { return instance; }
	gAccel();
	~gAccel(); 
	
	void releaseAccelMemorySpace();
	void setAccelMemorySpace(void *addr, int phys_addr, int size);

	bool hasAlphaBlendingSupport();
	int blit(gUnmanagedSurface *dst, const gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags);
	int fill(gUnmanagedSurface *dst, const eRect &area, unsigned long col);
	
	int accelAlloc(gUnmanagedSurface* surface);
	void accelFree(gUnmanagedSurface* surface);
private:
	eSingleLock m_allocation_lock;
	void *m_accel_addr;
	int m_accel_phys_addr;
	int m_accel_size; // in blocks
	gUnmanagedSurface **m_accel_allocation;
	int m_bcm_accel_state;
	
	static gAccel *instance;
};

#endif
