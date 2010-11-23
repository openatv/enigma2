#include <stdio.h>
#include <libsig_comp.h>
#include <lib/base/ebase.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <unistd.h>

#include <lib/gdi/grc.h>
#include <lib/gdi/gmaindc.h>
#include <lib/gdi/font.h> 

#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/elabel.h>

#ifdef OBJECT_DEBUG
int object_total_remaining;

void object_dump()
{
	printf("%d items left\n", object_total_remaining);
}
#endif

void dumpRegion(const gRegion &region)
{
	fprintf(stderr, "extends: %d %d -> %d %d\n", 
		region.extends.left(), region.extends.top(),
		region.extends.right(), region.extends.bottom());
	for (int y=0; y<region.extends.bottom(); ++y)
	{
		for (int x=0; x<region.extends.right(); ++x)
		{
			unsigned char res = ' ';
			for (unsigned int i=0; i < region.rects.size(); ++i)
				if (region.rects[i].contains(ePoint(x, y)))
					res = '0' + i;
			fprintf(stderr, "%c", res);
		}
		fprintf(stderr, "\n");
	}
}

int main()
{
#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif

	eInit init;

	init.setRunlevel(eAutoInitNumbers::main);
	ePtr<gMainDC> my_dc;
	gMainDC::getInstance(my_dc);

	gPainter p(my_dc);
	
	gRGB pal[256];
	pal[0] = 0;
	pal[1] = 0xff00ff;
	pal[2] = 0xffFFff;
	pal[3] = 0x00ff00;
	
	for (int a=0; a<0x10; ++a)
		pal[a | 0x10] = (0x111111 * a) | 0xFF;
	p.setPalette(pal, 0, 256);

	fontRenderClass::getInstance()->AddFont(eEnv::resolve("${datadir}/fonts/arial.ttf"), "Regular", 100);

	p.resetClip(gRegion(eRect(0, 0, 720, 576)));
	
	 
	gRegion c;
	eDebug("0");
	int i;
	
	c |= eRect(0, 20, 100, 10);
	c |= eRect(0, 50, 100, 10);
	c |= eRect(10, 10, 80, 100);
	
	c -= eRect(20, 20, 40, 40);
	
	p.setForegroundColor(gColor(3));
	p.fill(eRect(0, 0, 100, 100));
	p.fill(eRect(200, 0, 100, 100));
	
	for (int a=0; a<c.rects.size(); ++a)
		eDebug("%d %d -> %d %d", c.rects[a].left(), c.rects[a].top(), c.rects[a].right(), c.rects[a].bottom());
	eDebug("extends: %d %d %d %d", c.extends.left(), c.extends.top(), c.extends.right(), c.extends.bottom());
	p.setOffset(ePoint(100, 100));
	p.clip(c);

	p.setBackgroundColor(gColor(1));
	p.clear();
	p.setForegroundColor(gColor(2));
	p.line(ePoint(0, 0), ePoint(220, 190));
	p.clippop();

	p.setBackgroundColor(gColor(0x1f));
	p.setForegroundColor(gColor(0x10));

	ePtr<gFont> fnt = new gFont("Regular", 70);
	p.setFont(fnt);
	p.renderText(eRect(100, 100, 500, 200), "Hello welt!");
	
	sleep(1);
	return 0;
}
