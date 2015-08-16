#ifndef __gpixmap_h
#define __gpixmap_h

#include <pthread.h>
#include <string>
#include <lib/base/object.h>
#include <lib/base/smartptr.h>
#include <lib/base/elock.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/fb.h>
#include <byteswap.h>

struct gRGB
{
	union {
#if BYTE_ORDER == LITTLE_ENDIAN
		struct {
			unsigned char b, g, r, a;
		};
#else
		struct {
			unsigned char a, r, g, b;
		};
#endif
		unsigned long value;
	};
	gRGB(int r, int g, int b, int a=0): b(b), g(g), r(r), a(a)
	{
	}
	gRGB(unsigned long val): value(val)
	{
	}
	gRGB(const gRGB& other): value(other.value)
	{
	}
	gRGB(const char *colorstring)
	{
		unsigned long val = 0;
		if (colorstring)
		{
			for (int i = 0; i < 8; i++)
			{
				if (i) val <<= 4;
				if (!colorstring[i]) break;
				val |= (colorstring[i]) & 0x0f;
			}
		}
		value = val;
	}
	gRGB(): value(0)
	{
	}

	unsigned long argb() const
	{
		return value;
	}

	void set(unsigned long val)
	{
		value = val;
	}

	void operator=(unsigned long val)
	{
		value = val;
	}
	bool operator < (const gRGB &c) const
	{
		if (b < c.b)
			return true;
		if (b == c.b)
		{
			if (g < c.g)
				return true;
			if (g == c.g)
			{
				if (r < c.r)
					return true;
				if (r == c.r)
					return a < c.a;
			}
		}
		return false;
	}
	bool operator==(const gRGB &c) const
	{
		return c.value == value;
	}
	bool operator != (const gRGB &c) const
	{
		return c.value != value;
	}
	operator const std::string () const
	{
		unsigned long val = value;
		std::string escapecolor = "\\c";
		escapecolor.resize(10);
		for (int i = 9; i >= 2; i--)
		{
			escapecolor[i] = 0x40 | (val & 0xf);
			val >>= 4;
		}
		return escapecolor;
	}
	void alpha_blend(const gRGB other)
	{
#define BLEND(x, y, a) (y + (((x-y) * a)>>8))
		b = BLEND(other.b, b, other.a);
		g = BLEND(other.g, g, other.a);
		r = BLEND(other.r, r, other.a);
		a = BLEND(0xFF, a, other.a);
#undef BLEND
	}
};

#ifndef SWIG
struct gColor
{
	int color;
	gColor(int color): color(color)
	{
	}
	gColor(): color(0)
	{
	}
	operator int() const { return color; }
	bool operator==(const gColor &o) const { return o.color==color; }
};

struct gPalette
{
	int start, colors;
	gRGB *data;
	unsigned long data_phys;
	gColor findColor(const gRGB rgb) const;
	gPalette():	start(0), colors(0), data(0), data_phys(0) {}
};

struct gLookup
{
	int size;
	gColor *lookup;
	gLookup(int size, const gPalette &pal, const gRGB &start, const gRGB &end);
	gLookup();
	~gLookup() { delete [] lookup; }
	void build(int size, const gPalette &pal, const gRGB &start, const gRGB &end);
};

struct gUnmanagedSurface
{
	int x, y, bpp, bypp, stride;
	gPalette clut;
	void *data;
	int data_phys;

	gUnmanagedSurface();
	gUnmanagedSurface(int width, int height, int bpp);
};

struct gSurface: gUnmanagedSurface
{
	gSurface(): gUnmanagedSurface() {}
	gSurface(int width, int height, int bpp, int accel);
	~gSurface();
private:
	gSurface(const gSurface&); /* Copying managed gSurface is not allowed */
	gSurface& operator =(const gSurface&);
};
#endif

class gRegion;

SWIG_IGNORE(gPixmap);
class gPixmap: public iObject
{
	DECLARE_REF(gPixmap);
public:
#ifdef SWIG
	gPixmap();
#else
	enum
	{
		blitAlphaTest=1,
		blitAlphaBlend=2,
		blitScale=4,
		blitKeepAspectRatio=8
	};

	enum {
		accelNever = -1,
		accelAuto = 0,
		accelAlways = 1,
	};

	gPixmap(gUnmanagedSurface *surface);
	gPixmap(eSize, int bpp, int accel = 0);

	gUnmanagedSurface *surface;

	inline bool needClut() const { return surface && surface->bpp <= 8; }
#endif
	virtual ~gPixmap();
	eSize size() const { return eSize(surface->x, surface->y); }

private:
	bool must_delete_surface;

	friend class gDC;
	void fill(const gRegion &clip, const gColor &color);
	void fill(const gRegion &clip, const gRGB &color);

	void blit(const gPixmap &src, const eRect &pos, const gRegion &clip, int flags=0);

	void mergePalette(const gPixmap &target);
	void line(const gRegion &clip, ePoint start, ePoint end, gColor color);
	void line(const gRegion &clip, ePoint start, ePoint end, gRGB color);
	void line(const gRegion &clip, ePoint start, ePoint end, unsigned int color);
};
SWIG_TEMPLATE_TYPEDEF(ePtr<gPixmap>, gPixmapPtr);

#endif
