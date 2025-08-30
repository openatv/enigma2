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
#include <unordered_map>
#include <vector>

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
		uint32_t value;
	};
	gRGB(int r, int g, int b, int a=0): b(b), g(g), r(r), a(a)
	{
	}
	gRGB(uint32_t val): value(val)
	{
	}
	gRGB(const gRGB& other): value(other.value)
	{
	}
	gRGB(const char *colorstring)
	{
		uint32_t val = 0;

		if (colorstring)
		{
			for (int i = 0; i < 8; i++)
			{
				char c = colorstring[i];
				if (!c) break;
				val <<= 4;
				if (c >= '0' && c <= '9')
					val |= c - '0';
				else if(c >= 'a' && c <= 'f')
					val |= c - 'a' + 10;
				else if(c >= 'A' && c <= 'F')
					val |= c - 'A' + 10;
				else if(c >= ':' && c <= '?') // Backwards compatibility for old style color strings
					val |= c & 0x0f;
			}
		}
		value = val;
	}
	gRGB(): value(0)
	{
	}

	uint32_t argb() const
	{
		return value;
	}

	void set(uint32_t val)
	{
		value = val;
	}

	void operator=(uint32_t val)
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
		uint32_t val = value;
		std::string escapecolor = "\\c";
		escapecolor.resize(10);
		for (int i = 9; i >= 2; i--)
		{
			int hexbits = val & 0xf;
			escapecolor[i] = hexbits < 10	? '0' + hexbits
							: 'a' - 10 + hexbits;
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
	uint32_t data_phys;

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
	bool transparent = true;

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
		blitKeepAspectRatio=8,
		blitHAlignCenter = 16,
		blitHAlignRight = 32,
		blitVAlignCenter = 64,
		blitVAlignBottom = 128
	};

	enum
	{
		RADIUS_TOP_LEFT = 1,
		RADIUS_TOP_RIGHT = 2,
		RADIUS_BOTTOM_LEFT = 4,
		RADIUS_BOTTOM_RIGHT = 8,
	};

	enum {
		accelNever = -1,
		accelAuto = 0,
		accelAlways = 1,
	};

	typedef void (*gPixmapDisposeCallback)(gPixmap* pixmap);

	gPixmap(gUnmanagedSurface *surface);
	gPixmap(eSize, int bpp, int accel = 0);
	gPixmap(int width, int height, int bpp, gPixmapDisposeCallback on_dispose, int accel = accelAuto);

	gUnmanagedSurface *surface;

	inline bool needClut() const { return surface && surface->bpp <= 8; }
#endif
	virtual ~gPixmap();
	eSize size() const { return eSize(surface->x, surface->y); }

private:
	gPixmapDisposeCallback on_dispose;

	friend class gDC;
	void fill(const gRegion &clip, const gColor &color);
	void fill(const gRegion &clip, const gRGB &color);

	void blit(const gPixmap &src, const eRect &pos, const gRegion &clip, int cornerRadius, uint8_t edges, int flags=0);

    void blitRounded32Bit(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag);
    void blitRounded32BitScaled(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag);
    void blitRounded8Bit(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag);
    void blitRounded8BitScaled(const gPixmap &src, const eRect &pos, const eRect &clip, int cornerRadius, uint8_t edges, int flag);

	void mergePalette(const gPixmap &target);
	void line(const gRegion &clip, ePoint start, ePoint end, gColor color);
	void line(const gRegion &clip, ePoint start, ePoint end, gRGB color);
	void line(const gRegion &clip, ePoint start, ePoint end, unsigned int color);

	void drawRectangle(const gRegion &region, const eRect &area, const gRGB &backgroundColor, const gRGB &borderColor, int borderWidth, const std::vector<gRGB> &gradientColors, uint8_t direction, int radius, uint8_t edges, bool alphablend, int gradientFullSize = 0, bool useNew=false);
	void drawRectangleNew(const gRegion& region, const eRect& area, const gRGB& borderColor, int borderWidth, int radius, uint8_t edges, const gRGB& fillColor);
};
SWIG_TEMPLATE_TYPEDEF(ePtr<gPixmap>, gPixmapPtr);

#ifndef SWIG
struct CornerData
{
	int width;
	int height;
	int topLeftCornerRadius;
	int topLeftCornerSRadius;
	int topLeftCornerDRadius;
	int topRightCornerRadius;
	int topRightCornerSRadius;
	int topRightCornerDRadius;
	int bottomLeftCornerRadius;
	int bottomLeftCornerSRadius;
	int bottomLeftCornerDRadius;
	int bottomRightCornerRadius;
	int bottomRightCornerSRadius;
	int bottomRightCornerDRadius;
	int borderWidth;
	int cornerRadius;
	int w_topRightCornerRadius;
	int h_bottomLeftCornerRadius;
	int w_bottomRightCornerRadius;
	int h_bottomRightCornerRadius;
	uint32_t borderCol;

	bool radiusSet = false;
	bool isCircle = false;

	std::unordered_map<int, double> RadiusData;

	CornerData(int radius, uint8_t edges, int h, int w, int bw, uint32_t borderColor)
	{
		cornerRadius = checkRadiusValue(radius, h, w);
		radiusSet = cornerRadius > 0;
		topLeftCornerRadius = (gPixmap::RADIUS_TOP_LEFT & edges) ? cornerRadius: 0;
		topRightCornerRadius = (gPixmap::RADIUS_TOP_RIGHT & edges) ? cornerRadius: 0;
		bottomLeftCornerRadius = (gPixmap::RADIUS_BOTTOM_LEFT & edges) ? cornerRadius: 0;
		bottomRightCornerRadius = (gPixmap::RADIUS_BOTTOM_RIGHT & edges) ? cornerRadius: 0;
		topLeftCornerSRadius = topLeftCornerRadius * topLeftCornerRadius;
		topLeftCornerDRadius = (topLeftCornerRadius - 1) * (topLeftCornerRadius - 1);
		topRightCornerSRadius = topRightCornerRadius * topRightCornerRadius;
		topRightCornerDRadius = (topRightCornerRadius - 1) * (topRightCornerRadius - 1);
		bottomLeftCornerSRadius = bottomLeftCornerRadius * bottomLeftCornerRadius;
		bottomLeftCornerDRadius = (bottomLeftCornerRadius - 1) * (bottomLeftCornerRadius - 1);
		bottomRightCornerSRadius = bottomRightCornerRadius * bottomRightCornerRadius;
		bottomRightCornerDRadius = (bottomRightCornerRadius - 1) * (bottomRightCornerRadius - 1);
		width = h;
		height = w;
		borderWidth = bw;
		borderCol = borderColor;

		w_topRightCornerRadius = w - topRightCornerRadius;
		if(width > height)
			w_topRightCornerRadius += (width - height);
		else if (height > width)
			w_topRightCornerRadius -= (height - width);

		h_bottomLeftCornerRadius = h - bottomLeftCornerRadius;
		if(width > height)
			h_bottomLeftCornerRadius -= (width - height);
		else if (height > width)
			h_bottomLeftCornerRadius += (height - width);

		w_bottomRightCornerRadius = w - bottomRightCornerRadius;
		if(width > height)
			w_bottomRightCornerRadius += (width - height);
		else if (height > width)
			w_bottomRightCornerRadius -= (height - width);

		h_bottomRightCornerRadius = h - bottomRightCornerRadius;
		if(width > height)
			h_bottomRightCornerRadius -= (width - height);
		else if (height > width)
			h_bottomRightCornerRadius += (height - width);

		isCircle = ((edges == 15) && (width == height) && (cornerRadius == width / 2));
		caclCornerAlpha();
	}

	int checkRadiusValue(int r, const int w, const int h)
	{
		int minDimension = (w < h) ? w : h;
		if (r > minDimension / 2) {
			r = minDimension / 2;
		}
		return r;
	}

	void caclCornerAlpha()
	{
		int dx = 0, dy = 0, squared_dst = 0;
		double alpha = 0.0, distance = 0.0;
		int r = cornerRadius;
		for (int y = 0; y < r; y++)
		{
			for (int x = 0; x < r; x++)
			{
				dx = r - x - 1;
				dy = r - y - 1;
				squared_dst = dx * dx + dy * dy;
				if (squared_dst <= (r - 1) * (r - 1))
					continue;
				else if (squared_dst >= r * r)
					continue;
				else
				{
					if (RadiusData.find(squared_dst) == RadiusData.end())
					{
						distance = sqrt(squared_dst);
						alpha = (r - distance);
						RadiusData[squared_dst] = alpha;
					}
				}
			}
		}
	}
};
#endif

#endif
