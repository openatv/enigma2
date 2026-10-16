#ifndef __DREAMGE2D_H
#define __DREAMGE2D_H

class eRect;
struct gUnmanagedSurface;

bool dreamGE2DCopyOSD(int src_y, int dst_y, int width, int height, int virtual_height);
bool dreamGE2DCopySurface(gUnmanagedSurface *dst, const gUnmanagedSurface *src, int width, int height);
void dreamGE2DRegisterFramebuffer(void *base_data, unsigned long base_phys, int width, int height, int stride, int pages);

bool dreamGE2DAllocSurface(gUnmanagedSurface *surface, int stride, int size);
bool dreamGE2DFreeSurface(gUnmanagedSurface *surface);
bool dreamGE2DIsManagedSurface(const gUnmanagedSurface *surface);
void dreamGE2DReleaseAccelMemory();

bool dreamGE2DFill(gUnmanagedSurface *dst, const eRect &area, unsigned long col);
bool dreamGE2DBlit(gUnmanagedSurface *dst, gUnmanagedSurface *src, const eRect &p, const eRect &area, int flags);
bool dreamGE2DHasAlphaBlendingSupport();

void dreamGE2DReset();

#endif
