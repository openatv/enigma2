#include <lib/gdi/gpixmap.h>

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

void gPixmap::fill(const eRect &area, const gColor &color)
{
	if ((area.height()<=0) || (area.width()<=0))
		return;
	if (surface->bpp == 8)
		for (int y=area.top(); y<area.bottom(); y++)
			memset(((__u8*)surface->data)+y*surface->stride+area.left(), color.color, area.width());
	else if (surface->bpp == 32)
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

void gPixmap::blit(const gPixmap &src, ePoint pos, const eRect &clip, int flag)
{
	eRect area=eRect(pos, src.getSize());
	area&=clip;
	area&=eRect(ePoint(0, 0), getSize());
	if ((area.width()<0) || (area.height()<0))
		return;

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

void gPixmap::line(ePoint start, ePoint dst, gColor color)
{
int Ax=start.x(),
Ay=start.y(), Bx=dst.x(),
By=dst.y(); int dX, dY, fbXincr,
fbYincr, fbXYincr, dPr, dPru, P; __u8
*AfbAddr = &((__u8*)surface->data)[Ay*surface->stride+Ax*surface->bypp]; __u8
*BfbAddr = &((__u8*)surface->data)[By*surface->stride+Bx*surface->bypp]; fbXincr=
surface->bypp; if ( (dX=Bx-Ax) >= 0) goto AFTERNEGX; dX=-dX;
fbXincr=-1; AFTERNEGX: fbYincr=surface->stride; if ( (dY=By 
-Ay) >= 0) goto AFTERNEGY; fbYincr=-surface->stride; dY=-dY;AFTERNEGY: 
fbXYincr = fbXincr+fbYincr; if (dY > dX) goto YisIndependent; dPr = dY+ 
dY; P = -dX; dPru = P+P; dY = dX>>1; XLOOP: *AfbAddr=color; *BfbAddr=color; if ((P+=dPr) > 0)
goto RightAndUp;  AfbAddr+=fbXincr; BfbAddr-=fbXincr; if ((dY=dY-1) > 0) goto XLOOP; *AfbAddr=color; if ((dX & 1)
== 0) return;  *BfbAddr=color; return; RightAndUp: AfbAddr+=fbXYincr; BfbAddr-=fbXYincr; P+=dPru; if ((dY=dY-1) >
0) goto XLOOP;  *AfbAddr=color; if ((dX & 1) == 0) return; *BfbAddr=color; return; YisIndependent: dPr = dX+dX; P
= -dY; dPru = P+P; dX = dY>>1; YLOOP: *AfbAddr=color; *BfbAddr=color; if ((P+=dPr) > 0) goto RightAndUp2; AfbAddr
+=fbYincr;  BfbAddr-=fbYincr; if ((dX=dX-1) > 0) goto YLOOP; *AfbAddr=color; if ((dY & 1) == 0) return; *BfbAddr=
color;return; RightAndUp2: AfbAddr+=fbXYincr; BfbAddr-=fbXYincr; P+=dPru; if ((dX=dX-1) > 0) goto YLOOP; *AfbAddr
=color; if((dY & 1) == 0) return; *BfbAddr=color; return;
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

