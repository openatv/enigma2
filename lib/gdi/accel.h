#ifndef __lib_gdi_accel_h
#define __lib_gdi_accel_h

#include <base/elock.h>
#include <list>

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
	int blit(gUnmanagedSurface *dst, gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags);
	int fill(gUnmanagedSurface *dst, const eRect &area, unsigned long col);
	int accumulate();
	int sync();

	int accelAlloc(gUnmanagedSurface* surface);
	void accelFree(gUnmanagedSurface* surface);

	void dumpDebug();
private:
	struct MemoryBlock {
		gUnmanagedSurface *surface;
		int index;
		int size;

		MemoryBlock(gUnmanagedSurface *o, int i, int s):
			surface(o), index(i), size(s)
		{}
		MemoryBlock():
			surface(0), index(0), size(0)
		{}
	};
	typedef std::list<MemoryBlock> MemoryBlockList;

	eSingleLock m_allocation_lock;
	void *m_accel_addr;
	int m_accel_phys_addr;
	int m_accel_size; // in blocks
	MemoryBlockList m_accel_allocation;
	int m_bcm_accel_state;

	static gAccel *instance;
};

#endif
