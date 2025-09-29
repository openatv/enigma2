/*
Copyright (c) 2023-2025 zKhadiri, jbleyel, OpenATV

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.
*/

#ifndef __drawing__
#define __drawing__

#include "gpixmap.h"
#include <vector>

void duplicate_32fc(uint32_t *out, const uint32_t in, size_t size);
uint32_t *createGradientBuffer2(int graSize, const gRGB &startColor, const gRGB &endColor);
uint32_t *createGradientBuffer3(int graSize, const std::vector<gRGB> &colors);
void drawAngleTl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData);
void drawAngleTr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData);
void drawAngleBl(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData);
void drawAngleBr(gUnmanagedSurface *surface, const uint32_t *src, const eRect &area, uint8_t direction, const eRect &cornerRect, const CornerData &cornerData);

void drawAngle32Tl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle32Tr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle32Bl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle32Br(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);

void drawAngle32ScaledTl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle32ScaledTr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle32ScaledBl(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle32ScaledBr(gUnmanagedSurface *surface, const gPixmap &pixmap, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);

void drawAngle8Tl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle8Tr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle8Bl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle8Br(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);

void drawAngle8ScaledTl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle8ScaledTr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle8ScaledBl(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);
void drawAngle8ScaledBr(gUnmanagedSurface *surface, const gPixmap &pixmap, const uint32_t *pal, const eRect &area, const eRect &cornerRect, const CornerData &cornerData, int flag);

#endif