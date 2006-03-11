#ifdef WITH_SDL
#define SDLDC
#endif

#include <stdio.h>
#include <unistd.h>
#include <libsig_comp.h>

#include <lib/actions/action.h>
#include <lib/driver/rc.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gdi/gfbdc.h>
#include <lib/gdi/glcddc.h>
#include <lib/gdi/grc.h>
#ifdef WITH_SDL
#include <lib/gdi/sdl.h>
#endif
#include <lib/gdi/epng.h>
#include <lib/gdi/font.h> 
#include <lib/gui/ebutton.h>
#include <lib/gui/elabel.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/gui/ewindow.h>
#include <lib/python/connections.h>
#include <lib/python/python.h>

#ifdef HAVE_GSTREAMER
#include <gst/gst.h>
#endif

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
	}
	
	~eMain()
	{
		m_dvbdb->saveServicelist();
		m_scan = 0;
	}
};

/************************************************/

int exit_code;

int main(int argc, char **argv)
{
#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif

#ifdef HAVE_GSTREAMER
	gst_init(&argc, &argv);
#else
#error bla
#endif

	// set pythonpath if unset
	setenv("PYTHONPATH", LIBDIR "/enigma2/python", 0);
	printf("PYTHONPATH: %s\n", getenv("PYTHONPATH"));


	ePython python;
	eMain main;
	
#if 1
#ifdef SDLDC
	ePtr<gSDLDC> my_dc;
	gSDLDC::getInstance(my_dc);
#else
	ePtr<gFBDC> my_dc;
	gFBDC::getInstance(my_dc);
	
	int double_buffer = my_dc->haveDoubleBuffering();
#endif

	ePtr<gLCDDC> my_lcd_dc;
	gLCDDC::getInstance(my_lcd_dc);

	fontRenderClass::getInstance()->AddFont(FONTDIR "/md_khmurabi_10.ttf", "Regular", 100);
	fontRenderClass::getInstance()->AddFont(FONTDIR "/ae_AlMateen.ttf", "Replacement", 90);
	eTextPara::setReplacementFont("Replacement");
	
			/* some characters are wrong in the regular font, force them to use the replacement font */
	for (int i = 0x60c; i <= 0x66d; ++i)
		eTextPara::forceReplacementGlyph(i);
	eTextPara::forceReplacementGlyph(0xfdf2);
	for (int i = 0xfe80; i < 0xff00; ++i)
		eTextPara::forceReplacementGlyph(i);
	

	eWidgetDesktop dsk(eSize(720, 576));
	eWidgetDesktop dsk_lcd(eSize(132, 64));
	
/*	if (double_buffer)
	{
		eDebug(" - double buffering found, enable buffered graphics mode.");
		dsk.setCompositionMode(eWidgetDesktop::cmBuffered);
	} */
	
	wdsk = &dsk;
	lcddsk = &dsk_lcd;

	dsk.setDC(my_dc);
	dsk_lcd.setDC(my_lcd_dc);

	ePtr<gPixmap> m_pm;
	loadPNG(m_pm, DATADIR "/enigma2/pal.png");
	if (!m_pm)
	{
		eFatal("pal.png not found!");
	} else
		dsk.setPalette(*m_pm);

	dsk.setBackgroundColor(gRGB(0,0,0,0xFF));
#endif

		/* redrawing is done in an idle-timer, so we have to set the context */
	dsk.setRedrawTask(main);
	dsk_lcd.setRedrawTask(main);

	eRCInput::getInstance()->keyEvent.connect(slot(keyEvent));
	
	printf("executing main\n");

	python.execute("mytest", "__main__");
	
	dsk.paint();
	dsk_lcd.paint();

	{
		gPainter p(my_lcd_dc);
		p.resetClip(eRect(0, 0, 132, 64));
		p.clear();
		p.flush();
	}

	return exit_code;
}

eWidgetDesktop *getDesktop(int which)
{
	return which ? lcddsk : wdsk;
}

eApplication *getApplication()
{
	return eApp;
}

void runMainloop()
{
	eApp->runLoop();
}

void quitMainloop(int exitCode)
{
	exit_code = exitCode;
	eApp->quit(0);
}

void setLCD(const char *string)
{
}

void setLCDClock(const char *string)
{
}
