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

#ifdef OBJECT_DEBUG
int object_total_remaining;

void object_dump()
{
	printf("%d items left\n", object_total_remaining);
}
#endif
using namespace std;
	void print(const string &str, const char *c)
	{
		printf("%s (%s)\n", str.c_str(), c);
	}

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

	eWindow *wnd = new eWindow(&dsk);
	wnd->move(ePoint(100, 100));
	wnd->resize(eSize(200, 200));
	wnd->show();

	eLabel *label = new eButton(wnd);
	label->setText("Hello!!");
	label->move(ePoint(40, 40));
	label->resize(eSize(100, 40));

	label = new eButton(wnd);
	label->setText("2nd!!");
	label->move(ePoint(40, 90));
	label->resize(eSize(100, 40));

#if 0	
	eWidget *bla2 = new eWidget(0);
	dsk.addRootWidget(bla2, 0);
	
	bla2->move(ePoint(160, 160));
	bla2->resize(eSize(200, 200));
	bla2->show();
#endif

//	dsk.recalcClipRegions();
//	dsk.paint();
//	dsk.invalidate(gRegion(eRect(0, 0, 720, 576)));

//	dumpRegion(wnd->m_visible_region);
//	dumpRegion(label->m_visible_region);
//	dumpRegion(label->m_visible_region);
	
	eDebug("painting!");
	

	ePython python;
	
	printf("about to execute TEST :)\n");
	python.execute("mytest", "test");

	sleep(2);
#endif

#if 0

		// connections mit parametern: geht! :)
	using namespace std;
	using namespace SigC;

	
	Signal1<void,const string &> printer;
	int i;
	for (i=1; i<argc; ++i)
		printer.connect(bind(slot(print), argv[i]));
	printer("hello world\n");
#endif

	return 0;
}

eWidgetDesktop *getDesktop()
{
	return wdsk;
}

