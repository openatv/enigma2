#include <stdio.h>
#include <libsig_comp.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <unistd.h>

#include <lib/gdi/grc.h>
#include <lib/gdi/gfbdc.h>
#include <lib/gdi/font.h> 

#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/elabel.h>
#include <lib/gui/ebutton.h>

#include <lib/gui/ewindow.h>

#include <lib/python/python.h>
#include <lib/python/connections.h>

#ifdef OBJECT_DEBUG
int object_total_remaining;

void object_dump()
{
	printf("%d items left\n", object_total_remaining);
}
#endif

void dumpRegion(const gRegion &region)
{
	fprintf(stderr, "extends: %d %d -> %d %d (%d rects)\n", 
		region.extends.left(), region.extends.top(),
		region.extends.right(), region.extends.bottom(), region.rects.size());
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


class eMain: public eApplication, public Object
{
	eInit init;
public:
	eMain()
	{
		init.setRunlevel(eAutoInitNumbers::main);
	}
};

eWidgetDesktop *wdsk;

// typedef struct _object PyObject;

void print(int i)
{
	printf("C++ says: it's a %d!!!\n", i);
}

int main(int argc, char **argv)
{
#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif


#if 1
	eMain main;

	ePtr<gFBDC> my_dc;
	gFBDC::getInstance(my_dc);

	gPainter p(my_dc);
	
	gRGB pal[256];
	pal[0] = 0;
	pal[1] = 0xff00ff;
	pal[2] = 0xffFFff;
	pal[3] = 0x00ff00;
	
	for (int a=0; a<0x10; ++a)
		pal[a | 0x10] = 0x111111 * a;
	for (int a=0; a<0x10; ++a)
		pal[a | 0x20] = (0x111100 * a) | 0xFF;
	for (int a=0; a<0x10; ++a)
		pal[a | 0x30] = (0x110011 * a) | 0xFF00;
	for (int a=0; a<0x10; ++a)
		pal[a | 0x40] = (0x001111 * a) | 0xFF0000;
	p.setPalette(pal, 0, 256);

	fontRenderClass::getInstance()->AddFont("/dbox2/cdkroot/share/fonts/arial.ttf", "Arial", 100);

	eWidgetDesktop dsk(eSize(720, 576));
	
	wdsk = &dsk;
	dsk.setDC(my_dc);
#endif

		/* redrawing is done in an idle-timer, so we have to set the context */
	dsk.setRedrawTask(main);
	
	ePython python;
	
	printf("executing main\n");
	python.execute("mytest", "__main__");

	return 0;
}

eWidgetDesktop *getDesktop()
{
	return wdsk;
}

void runMainloop()
{
	eApp->exec();
}
