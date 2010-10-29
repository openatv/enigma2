#include <stdio.h>
#include <libsig_comp.h>
#include <lib/base/ebase.h>
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

	eWidgetDesktop dsk(eSize(720, 576));
	dsk.setDC(my_dc);

	eWidget *bla = new eWidget(0);
	dsk.addRootWidget(bla, 0);
	
	bla->move(ePoint(100, 100));
	bla->resize(eSize(200, 200));
	bla->show();

	eWidget *blablub = new eLabel(bla);
	blablub->move(ePoint(40, 40));
	blablub->resize(eSize(100, 100));
	
	eWidget *bla2 = new eWidget(0);
	dsk.addRootWidget(bla2, 0);
	
	bla2->move(ePoint(160, 160));
	bla2->resize(eSize(200, 200));
	bla2->show();

	dsk.recalcClipRegions();

	dumpRegion(bla->m_visible_region);
//	dumpRegion(bla2->m_visible_region);
//	dumpRegion(blablub->m_visible_region);
	
	eDebug("painting!");
	
	dsk.invalidate(gRegion(eRect(0, 0, 720, 576)));
	dsk.paint();

	sleep(1);
	return 0;
}
