#include <lib/gdi/gpixmap.h>

gLookup::gLookup()
{
	size=0;
	lookup=0;
}

gLookup::gLookup(int size, const gPalette &pal, const gRGB &start, const gRGB &end)
{
	size=0;
	lookup=0;
	build(size, pal, start, end);
}

void gLookup::build(int _size, const gPalette &pal, const gRGB &start, const gRGB &end)
{
	if (lookup)
	{
		delete lookup;
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

DEFINE_REF(gPixmap);

void gPixmap::fill(const eRect &area, const gColor &color)
{
	if ((area.height()<=0) || (area.width()<=0))
		return;
	if (bpp == 8)
		for (int y=area.top(); y<area.bottom(); y++)
			memset(((__u8*)data)+y*stride+area.left(), color.color, area.width());
	else if (bpp == 32)
		for (int y=area.top(); y<area.bottom(); y++)
		{
			__u32 *dst=(__u32*)(((__u8*)data)+y*stride+area.left()*bypp);
			int x=area.width();
			__u32 col;

			if (clut.data && color < clut.colors)
				col=(clut.data[color].a<<24)|(clut.data[color].r<<16)|(clut.data[color].g<<8)|(clut.data[color].b);
			else
				col=0x10101*color;
			col^=0xFF000000;			
			while (x--)
				*dst++=col;
		}
	else
		eWarning("couldn't fill %d bpp", bpp);
}

void gPixmap::blit(const gPixmap &src, ePoint pos, const eRect &clip, int flag)
{
	
	eRect area=eRect(pos, src.getSize());
	if (!clip.isNull())
		area&=clip;
	area&=eRect(ePoint(0, 0), getSize());
	if ((area.width()<0) || (area.height()<0))
		return;
	
	eRect srcarea=area;
	srcarea.moveBy(-pos.x(), -pos.y());

	if ((bpp == 8) && (src.bpp==8))
	{
		__u8 *srcptr=(__u8*)src.data;
		__u8 *dstptr=(__u8*)data;
	
		srcptr+=srcarea.left()*bypp+srcarea.top()*src.stride;
		dstptr+=area.left()*bypp+area.top()*stride;
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
				memcpy(dstptr, srcptr, area.width()*bypp);
			srcptr+=src.stride;
			dstptr+=stride;
		}
	} else if ((bpp == 32) && (src.bpp==8))
	{
		__u8 *srcptr=(__u8*)src.data;
		__u8 *dstptr=(__u8*)data; // !!
		__u32 pal[256];
		
		for (int i=0; i<256; ++i)
		{
			if (src.clut.data && (i<src.clut.colors))
				pal[i]=(src.clut.data[i].a<<24)|(src.clut.data[i].r<<16)|(src.clut.data[i].g<<8)|(src.clut.data[i].b);
			else
				pal[i]=0x010101*i;
			pal[i]^=0xFF000000;
		}
	
		srcptr+=srcarea.left()*bypp+srcarea.top()*src.stride;
		dstptr+=area.left()*bypp+area.top()*stride;
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
			srcptr+=src.stride;
			dstptr+=stride;
		}
	} else
		eFatal("cannot blit %dbpp from %dbpp", bpp, src.bpp);
}

void gPixmap::mergePalette(const gPixmap &target)
{
	if ((!clut.colors) || (!target.clut.colors))
		return;
	gColor *lookup=new gColor[clut.colors];

	for (int i=0; i<clut.colors; i++)
		lookup[i].color=target.clut.findColor(clut.data[i]);
	
	delete clut.data;
	clut.colors=target.clut.colors;
	clut.data=new gRGB[clut.colors];
	memcpy(clut.data, target.clut.data, sizeof(gRGB)*clut.colors);

	__u8 *dstptr=(__u8*)data;

	for (int ay=0; ay<y; ay++)
	{
		for (int ax=0; ax<x; ax++)
			dstptr[ax]=lookup[dstptr[ax]];
		dstptr+=stride;
	}
	
	delete lookup;	
}

void gPixmap::line(ePoint start, ePoint dst, gColor color)
{
int Ax=start.x(), // dieser code rult ganz ganz doll weil er ganz ganz fast ist und auch sehr gut dokumentiert is
Ay=start.y(), Bx=dst.x(), // t. es handelt sich immerhin um den weltbekannten bresenham algorithmus der nicht nur
By=dst.y(); int dX, dY, fbXincr, // sehr schnell ist sondern auch sehr gut dokumentiert und getestet wurde. nicht
fbYincr, fbXYincr, dPr, dPru, P; __u8 // nur auf dem LCD der dbox, sondern auch ueberall anders. und auch auf der
*AfbAddr = &((__u8*)data)[Ay*stride+Ax*bypp]; __u8 // dbox mit LCD soll das teil nun tun, und ich denke das tut es. ausse
*BfbAddr = &((__u8*)data)[By*stride+Bx*bypp]; fbXincr= // rdem hat dieser algo den vorteil dass man fehler sehr leicht fi
bypp; if ( (dX=Bx-Ax) >= 0) goto AFTERNEGX; dX=-dX; // ndet und beheben kann. das liegt nicht zuletzt an den komment
fbXincr=-1; AFTERNEGX: fbYincr=stride; if ( (dY=By // aren. und ausserdem, je kuerzer der code, desto weniger k
-Ay) >= 0) goto AFTERNEGY; fbYincr=-stride; dY=-dY;AFTERNEGY: // ann daran falsch sein. erwaehnte ich schon, da
fbXYincr = fbXincr+fbYincr; if (dY > dX) goto YisIndependent; dPr = dY+ // s dieser tolle code wahnsinnig schnell
dY; P = -dX; dPru = P+P; dY = dX>>1; XLOOP: *AfbAddr=color; *BfbAddr=color; if ((P+=dPr) > 0) // ist? bye, tmbinc
goto RightAndUp;  AfbAddr+=fbXincr; BfbAddr-=fbXincr; if ((dY=dY-1) > 0) goto XLOOP; *AfbAddr=color; if ((dX & 1)
== 0) return;  *BfbAddr=color; return; RightAndUp: AfbAddr+=fbXYincr; BfbAddr-=fbXYincr; P+=dPru; if ((dY=dY-1) >
0) goto XLOOP;  *AfbAddr=color; if ((dX & 1) == 0) return; *BfbAddr=color; return; YisIndependent: dPr = dX+dX; P
= -dY; dPru = P+P; dX = dY>>1; YLOOP: *AfbAddr=color; *BfbAddr=color; if ((P+=dPr) > 0) goto RightAndUp2; AfbAddr
+=fbYincr;  BfbAddr-=fbYincr; if ((dX=dX-1) > 0) goto YLOOP; *AfbAddr=color; if ((dY & 1) == 0) return; *BfbAddr=
color;return; RightAndUp2: AfbAddr+=fbXYincr; BfbAddr-=fbXYincr; P+=dPru; if ((dX=dX-1) > 0) goto YLOOP; *AfbAddr
=color; if((dY & 1) == 0) return; *BfbAddr=color; return; // nun ist der tolle code leider zu ende. tut mir leid.
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

gPixmap::gPixmap()
{
}

gPixmap::~gPixmap()
{
}

gImage::gImage(eSize size, int _bpp)
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
	data=new char[x*y*bypp];
}

gImage::~gImage()
{
	delete[] clut.data;
	delete[] (char*)data;
}
