#ifndef __lib_gdi_accel_h
#define __lib_gdi_accel_h

struct gUnmanagedSurface;
class eRect;
class ePoint;

class gAccel
{
public:
	static gAccel* getInstance() { return instance; }
	gAccel();
	~gAccel(); 
	
	void setAccelMemorySpace(void *addr, int phys_addr, int size);

	bool hasAlphaBlendingSupport();
	int blit(gUnmanagedSurface *dst, const gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags);
	int fill(gUnmanagedSurface *dst, const eRect &area, unsigned long col);
	
	int accelAlloc(void *&addr, int &phys_addr, int size);
	void accelFree(int phys_addr);
private:
	void *m_accel_addr;
	int m_accel_phys_addr;
	int m_accel_size; // in blocks
	int *m_accel_allocation;
	int m_bcm_accel_state;
	
	static gAccel *instance;
};

#endif
