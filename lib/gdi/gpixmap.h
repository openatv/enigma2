#ifndef __gpixmap_h
#define __gpixmap_h

#include <pthread.h>
#include <string>
#include <lib/base/object.h>
#include <lib/base/smartptr.h>
#include <lib/base/elock.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/fb.h>

struct gRGB
{
	unsigned char b, g, r, a;
	gRGB(int r, int g, int b, int a=0): b(b), g(g), r(r), a(a)
	{
	}
	gRGB(unsigned long val)
	{
		if (val)
		{
			set(val);
		}
		else
		{
			b = g = r = a = 0;
		}
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
		set(val);
	}
	gRGB(): b(0), g(0), r(0), a(0)
	{
	}

	unsigned long argb() const
	{
		return (a<<24)|(r<<16)|(g<<8)|b;
	}

	void set(unsigned long val)
	{
		b = val&0xFF;
		g = (val>>8)&0xFF;
		r = (val>>16)&0xFF;
		a = (val>>24)&0xFF;
	}

	void operator=(unsigned long val)
	{
		set(val);
	}
	bool operator < (const gRGB &c) const
	{
		if (b < c.b)
			return 1;
		if (b == c.b)
		{
			if (g < c.g)
				return 1;
			if (g == c.g)
			{
				if (r < c.r)
					return 1;
				if (r == c.r)
					return a < c.a;
			}
		}
		return 0;
	}
	bool operator==(const gRGB &c) const
	{
		return (b == c.b) && (g == c.g) && (r == c.r) && (a == c.a);
	}
	bool operator != (const gRGB &c) const
	{
		return (b != c.b) || (g != c.g) || (r != c.r) || (a != c.a);
	}
	operator const std::string () const
	{
		unsigned long val = argb();
		std::string escapecolor = "\\c";
		escapecolor.resize(10);
		for (int i = 9; i >= 2; i--)
		{
			escapecolor[i] = 0x40 | (val & 0xf);
			val >>= 4;
		}
		return escapecolor;
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
	gColor findColor(const gRGB &rgb) const;
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

struct gSurface
{
	int type;
	int x, y, bpp, bypp, stride;
	gPalette clut;
	
	void *data;
	int data_phys;
	int offset; // only for backbuffers

	gSurface();
	gSurface(eSize size, int bpp, int accel);
	~gSurface();
};
#endif

class gRegion;

SWIG_IGNORE(gPixmap);
class gPixmap: public iObject
{
	DECLARE_REF(gPixmap);
public:
#ifndef SWIG
	enum
	{
		blitAlphaTest=1,
		blitAlphaBlend=2,
		blitScale=4
	};

	gPixmap(gSurface *surface);
	gPixmap(eSize, int bpp, int accel = 0);

	gSurface *surface;
	
	eLock contentlock;
	int final;
	
	gPixmap *lock();
	void unlock();
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
#ifdef SWIG
	gPixmap();
#endif
};
SWIG_TEMPLATE_TYPEDEF(ePtr<gPixmap>, gPixmapPtr);

#endif
