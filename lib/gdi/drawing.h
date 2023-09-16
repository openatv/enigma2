#ifndef __drawing__
#define __drawing__

#include "gpixmap.h"

void duplicate_32fc(uint32_t *out, const uint32_t in, size_t size);
uint32_t* createGradientBuffer(int graSize, const gRGB &startColor, const gRGB &endColor);
void drawAngleTl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData);
void drawAngleTr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData);
void drawAngleBl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData);
void drawAngleBr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, int direction, const eRect &cornerRect, const CornerData &cornerData);
#endif