#undef WITH_SDL

#ifdef WITH_SDL
#error
#define SDLDC
#endif

#include <stdio.h>
#include <libsig_comp.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <unistd.h>

#include <lib/gdi/grc.h>
#include <lib/gdi/gfbdc.h>
#include <lib/gdi/glcddc.h>

#ifdef WITH_SDL
#error
#include <lib/gdi/sdl.h>
#endif
#include <lib/gdi/font.h> 

#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/elabel.h>
#include <lib/gui/ebutton.h>

#include <lib/gui/ewindow.h>

#include <lib/python/python.h>
#include <lib/python/connections.h>

#include <lib/gui/elistboxcontent.h>

#include <lib/driver/rc.h>

#include <lib/actions/action.h>

#include <lib/gdi/epng.h>

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
#if 0
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
#endif

}

eWidgetDesktop *wdsk, *lcddsk;

// typedef struct _object PyObject;

void print(int i)
{
	printf("C++ says: it's a %d!!!\n", i);
}

PSignal1<void,int> keyPressed;

PSignal1<void,int> &keyPressedSignal()
{
	return keyPressed;
}

void keyEvent(const eRCKey &key)
{
	ePtr<eActionMap> ptr;
	eActionMap::getInstance(ptr);
	ptr->keyPressed(0, key.code, key.flags);
//	if (!key.flags)
//		keyPressed(key.code);
}

/************************************************/
#include <unistd.h>
#include <lib/components/scan.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/dvbtime.h>
#include <lib/dvb/epgcache.h>

class eMain: public eApplication, public Object
{
	eInit init;
	
	ePtr<eDVBResourceManager> m_mgr;
	ePtr<eDVBDB> m_dvbdb;
	ePtr<eDVBLocalTimeHandler> m_locale_time_handler;
	ePtr<eComponentScan> m_scan;
	ePtr<eEPGCache> m_epgcache;

public:
	eMain()
	{
		init.setRunlevel(eAutoInitNumbers::main);

				/* TODO: put into init */
		m_dvbdb = new eDVBDB();
		m_mgr = new eDVBResourceManager();
		m_locale_time_handler = new eDVBLocalTimeHandler();
		m_epgcache = new eEPGCache();
		m_mgr->setChannelList(m_dvbdb);
		
//		m_scan = new eComponentScan();
//		m_scan->start();

	}
	
	~eMain()
	{
		m_scan = 0;
	}
};

/************************************************/

eLabel *lcd_label, *lcd_clock;

int main(int argc, char **argv)
{
#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif


	ePython python;
	eMain main;
	
	int double_buffer = 0;

#if 1
#ifdef SDLDC
	ePtr<gSDLDC> my_dc;
	gSDLDC::getInstance(my_dc);
#else
	ePtr<gFBDC> my_dc;
	gFBDC::getInstance(my_dc);
	
	double_buffer = my_dc->haveDoubleBuffering();
#endif

	ePtr<gLCDDC> my_lcd_dc;
	gLCDDC::getInstance(my_lcd_dc);

	fontRenderClass::getInstance()->AddFont(FONTDIR "/arial.ttf", "Arial", 100);

	eWidgetDesktop dsk(eSize(720, 576));
	eWidgetDesktop dsk_lcd(eSize(132, 64));
	
	if (double_buffer)
	{
		eDebug(" - double buffering found, enable buffered graphics mode.");
		dsk.setCompositionMode(eWidgetDesktop::cmBuffered);
	}
	
	wdsk = &dsk;
	lcddsk = &dsk_lcd;

	dsk.setDC(my_dc);
	dsk_lcd.setDC(my_lcd_dc);

	ePtr<gPixmap> m_pm;
	loadPNG(m_pm, "data/pal.png");
	if (!m_pm)
	{
		eFatal("hi ghost, please copy pal.png into your ./data, thanks!");
	} else
		dsk.setPalette(*m_pm);

	dsk.setBackgroundColor(gRGB(0,0,0,0xFF));
#endif

		/* redrawing is done in an idle-timer, so we have to set the context */
	dsk.setRedrawTask(main);
	dsk_lcd.setRedrawTask(main);

	eWindow *lcd_win = new eWindow(&dsk_lcd);
	
	lcd_win->setFlag(eWindow::wfNoBorder);
	
	lcd_win->move(ePoint(0, 0));
	lcd_win->resize(eSize(132, 64));
	
	lcd_label = new eLabel(lcd_win);
	lcd_label->move(ePoint(0, 10));
	lcd_label->resize(eSize(132, 36));
	ePtr<gFont> font = new gFont("Arial", 16);
	lcd_label->setFont(font);

	lcd_clock = new eLabel(lcd_win);
	lcd_clock->move(ePoint(50, 46));
	lcd_clock->resize(eSize(132, 20));
	//ePtr<gFont> clkfont = new gFont("Arial", 18);
	lcd_clock->setFont(font);

	//lcd_label->setText("bla bla bla, this lcd\nSUCKS!");
	//lcd_clock->setText("88:88:88");

	lcd_win->show();
	
	eRCInput::getInstance()->keyEvent.connect(slot(keyEvent));
	
	printf("executing main\n");

	python.execute("mytest", "__main__");

//	eApp->exec();

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

void quitMainloop()
{
	eApp->quit(0);
}

void setLCD(const char *string)
{
	lcd_label->setText(string);
}

void setLCDClock(const char *string)
{
	lcd_clock->setText(string);
}
