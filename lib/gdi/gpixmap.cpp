#include <lib/gdi/gpixmap.h>
#include <lib/gdi/region.h>

gLookup::gLookup()
	:size(0), lookup(0)
{
}

gLookup::gLookup(int size, const gPalette &pal, const gRGB &start, const gRGB &end)
	:size(0), lookup(0)
{
	build(size, pal, start, end);
}

void gLookup::build(int _size, const gPalette &pal, const gRGB &start, const gRGB &end)
{
	if (lookup)
	{
		delete [] lookup;
		lookup=0;
		size=0;
	}
	size=_size;
	if (!size)
		return;
	lookup=new gColor[size];
	
	for (int i=0; i<size; i++)
	{
		gRGB col;
		if (i)
		{
			int rdiff=-start.r+end.r;
			int gdiff=-start.g+end.g;
			int bdiff=-start.b+end.b;
			int adiff=-start.a+end.a;
			rdiff*=i; rdiff/=(size-1);
			gdiff*=i; gdiff/=(size-1);
			bdiff*=i; bdiff/=(size-1);
			adiff*=i; adiff/=(size-1);
			col.r=start.r+rdiff;
			col.g=start.g+gdiff;
			col.b=start.b+bdiff;
			col.a=start.a+adiff;
		} else
			col=start;
		lookup[i]=pal.findColor(col);
	}
}

gSurface::~gSurface()
{
}

gSurfaceSystem::gSurfaceSystem(eSize size, int _bpp)
{
	x=size.width();
	y=size.height();
	bpp=_bpp;
	switch (bpp)
	{
	case 8:
		bypp=1;
		break;
	case 15:
	case 16:
		bypp=2;
		break;
	case 24:		// never use 24bit mode
	case 32:
		bypp=4;
		break;
	default:
		bypp=(bpp+7)/8;
	}
	stride=x*bypp;
	if (bpp==8)
	{
		clut.colors=256;
		clut.data=new gRGB[clut.colors];
	} else
	{
		clut.colors=0;
		clut.data=0;
	}
	data=malloc(x*y*bypp);
}

gSurfaceSystem::~gSurfaceSystem()
{
	free(data);
	delete[] clut.data;
}

gPixmap *gPixmap::lock()
{
	contentlock.lock(1);
	return this;
}

void gPixmap::unlock()
{
	contentlock.unlock(1);
}

void gPixmap::fill(const gRegion &region, const gColor &color)
{
	int i;
	for (i=0; i<region.rects.size(); ++i)
	{
		const eRect &area = region.rects[i];
		if ((area.height()<=0) || (area.width()<=0))
			continue;
		if (surface->bpp == 8)
		{
			for (int y=area.top(); y<area.bottom(); y++)
		 		memset(((__u8*)surface->data)+y*surface->stride+area.left(), color.color, area.width());
		} else if (surface->bpp == 32)
			for (int y=area.top(); y<area.bottom(); y++)
			{
				__u32 *dst=(__u32*)(((__u8*)surface->data)+y*surface->stride+area.left()*surface->bypp);
				int x=area.width();
				__u32 col;

				if (surface->clut.data && color < surface->clut.colors)
					col=(surface->clut.data[color].a<<24)|(surface->clut.data[color].r<<16)|(surface->clut.data[color].g<<8)|(surface->clut.data[color].b);
				else
					col=0x10101*color;
				col^=0xFF000000;			
				while (x--)
					*dst++=col;
			}
		else
			eWarning("couldn't fill %d bpp", surface->bpp);
	}
}

void gPixmap::blit(const gPixmap &src, ePoint pos, const gRegion &clip, int flag)
{
	for (int i=0; i<clip.rects.size(); ++i)
	{
		eRect area=eRect(pos, src.getSize());
		area&=clip.rects[i];
		area&=eRect(ePoint(0, 0), getSize());
		if ((area.width()<0) || (area.height()<0))
			continue;

		eRect srcarea=area;
		srcarea.moveBy(-pos.x(), -pos.y());

		if ((surface->bpp == 8) && (src.surface->bpp==8))
		{
			__u8 *srcptr=(__u8*)src.surface->data;
			__u8 *dstptr=(__u8*)surface->data;
	
			srcptr+=srcarea.left()*surface->bypp+srcarea.top()*src.surface->stride;
			dstptr+=area.left()*surface->bypp+area.top()*surface->stride;
			for (int y=0; y<area.height(); y++)
			{
				if (flag & blitAlphaTest)
				{
  		      // no real alphatest yet
					int width=area.width();
					unsigned char *src=(unsigned char*)srcptr;
					unsigned char *dst=(unsigned char*)dstptr;
						// use duff's device here!
					while (width--)
					{
						if (!*src)
						{
							src++;
							dst++;
						} else
							*dst++=*src++;
					}
				} else
					memcpy(dstptr, srcptr, area.width()*surface->bypp);
				srcptr+=src.surface->stride;
				dstptr+=surface->stride;
			}
		} else if ((surface->bpp == 32) && (src.surface->bpp==8))
		{	
			__u8 *srcptr=(__u8*)src.surface->data;
			__u8 *dstptr=(__u8*)surface->data; // !!
			__u32 pal[256];

			for (int i=0; i<256; ++i)
			{
				if (src.surface->clut.data && (i<src.surface->clut.colors))
					pal[i]=(src.surface->clut.data[i].a<<24)|(src.surface->clut.data[i].r<<16)|(src.surface->clut.data[i].g<<8)|(src.surface->clut.data[i].b);
				else
					pal[i]=0x010101*i;
				pal[i]^=0xFF000000;
			}
	
			srcptr+=srcarea.left()*surface->bypp+srcarea.top()*src.surface->stride;
			dstptr+=area.left()*surface->bypp+area.top()*surface->stride;
			for (int y=0; y<area.height(); y++)
			{
				if (flag & blitAlphaTest)
				{
	  	      // no real alphatest yet
					int width=area.width();
					unsigned char *src=(unsigned char*)srcptr;
					__u32 *dst=(__u32*)dstptr;
						// use duff's device here!
					while (width--)
					{
						if (!*src)
						{
							src++;
							dst++;
						} else
							*dst++=pal[*src++];
					}
				} else
				{
					int width=area.width();
					unsigned char *src=(unsigned char*)srcptr;
					__u32 *dst=(__u32*)dstptr;
					while (width--)
						*dst++=pal[*src++];
				}
				srcptr+=src.surface->stride;
				dstptr+=surface->stride;
			}
		} else
			eFatal("cannot blit %dbpp from %dbpp", surface->bpp, src.surface->bpp);
	}
}

void gPixmap::mergePalette(const gPixmap &target)
{
	if ((!surface->clut.colors) || (!target.surface->clut.colors))
		return;
	gColor *lookup=new gColor[surface->clut.colors];

	for (int i=0; i<surface->clut.colors; i++)
		lookup[i].color=target.surface->clut.findColor(surface->clut.data[i]);
	
	delete [] surface->clut.data;
	surface->clut.colors=target.surface->clut.colors;
	surface->clut.data=new gRGB[surface->clut.colors];
	memcpy(surface->clut.data, target.surface->clut.data, sizeof(gRGB)*surface->clut.colors);

	__u8 *dstptr=(__u8*)surface->data;

	for (int ay=0; ay<surface->y; ay++)
	{
		for (int ax=0; ax<surface->x; ax++)
			dstptr[ax]=lookup[dstptr[ax]];
		dstptr+=surface->stride;
	}
	
	delete [] lookup;
}

static inline int sgn(int a)
{
	if (a < 0)
		return -1;
	else if (!a)
		return 0;
	else
		return 1;
}

void gPixmap::line(const gRegion &clip, ePoint start, ePoint dst, gColor color)
{
	__u8 *srf = (__u8*)surface->data;
	int stride = surface->stride;
	
	if (clip.rects.empty())
		return;
	
	int xa = start.x(), ya = start.y(), xb = dst.x(), yb = dst.y();
	int dx, dy, x, y, s1, s2, e, temp, swap, i;
	dy=abs(yb-ya);
	dx=abs(xb-xa);
	s1=sgn(xb-xa);
	s2=sgn(yb-ya);
	x=xa;
	y=ya;
	if (dy>dx)
	{
		temp=dx;
		dx=dy;
		dy=temp;
		swap=1;
	} else
		swap=0;
	e = 2*dy-dx;
	int lasthit = 0;
	for(i=1; i<=dx; i++)
	{
				/* i don't like this clipping loop, but the only */
				/* other choice i see is to calculate the intersections */
				/* before iterating through the pixels. */
				
				/* one could optimize this because of the ordering */
				/* of the bands. */
				
		lasthit = 0;
		int a = lasthit;
		
			/* if last pixel was invisble, first check bounding box */
		if (a == -1)
		{
				/* check if we just got into the bbox again */
			if (clip.extends.contains(x, y))
				lasthit = a = 0;
			else
				goto fail;
		} else if (!clip.rects[a].contains(x, y))
		{
			do
			{
				++a;
				if (a == clip.rects.size())
					a = 0;
				if (a == lasthit)
				{
					goto fail;
					lasthit = -1;
				}
			} while (!clip.rects[a].contains(x, y));
			lasthit = a;
		}
		srf[y * stride + x] = color;
fail:
		while (e>=0)
		{
			if (swap==1) x+=s1;
			else y+=s2;
			e-=2*dx;
		}
    if (swap==1)
    	y+=s2;
		else
			x+=s1;
		e+=2*dy;
	}
}

gColor gPalette::findColor(const gRGB &rgb) const
{
	int difference=1<<30, best_choice=0;
	for (int t=0; t<colors; t++)
	{
		int ttd;
		int td=(signed)(rgb.r-data[t].r); td*=td; td*=(255-data[t].a);
		ttd=td;
		if (ttd>=difference)
			continue;
		td=(signed)(rgb.g-data[t].g); td*=td; td*=(255-data[t].a);
		ttd+=td;
		if (ttd>=difference)
			continue;
		td=(signed)(rgb.b-data[t].b); td*=td; td*=(255-data[t].a);
		ttd+=td;
		if (ttd>=difference)
			continue;
		td=(signed)(rgb.a-data[t].a); td*=td; td*=255;
		ttd+=td;
		if (ttd>=difference)
			continue;
		difference=ttd;
		best_choice=t;
	}
	return best_choice;
}

DEFINE_REF(gPixmap);

gPixmap::~gPixmap()
{
}

gPixmap::gPixmap(gSurface *surface): surface(surface)
{
}

gPixmap::gPixmap(eSize size, int bpp)
{
	surface = new gSurfaceSystem(size, bpp);
}

