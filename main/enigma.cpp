#ifdef WITH_SDL
#define SDLDC
#endif

#include <stdio.h>
#include <unistd.h>
#include <libsig_comp.h>

#include <lib/actions/action.h>
#include <lib/driver/rc.h>
#include <lib/base/ioprio.h>
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

#include "bsod.h" 

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

static eWidgetDesktop *wdsk, *lcddsk;

static int prev_ascii_code;

int getPrevAsciiCode()
{
	int ret = prev_ascii_code;
	prev_ascii_code = 0;
	return ret;
}

void keyEvent(const eRCKey &key)
{
	ePtr<eActionMap> ptr;
	eActionMap::getInstance(ptr);
	if (key.flags & eRCKey::flagAscii)
	{
		prev_ascii_code = key.code;
		ptr->keyPressed(key.producer->getIdentifier(), 510 /* faked KEY_ASCII */, 0);
	}
	else
		ptr->keyPressed(key.producer->getIdentifier(), key.code, key.flags);
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

int exit_code;

int main(int argc, char **argv)
{
#ifdef MEMLEAK_CHECK
	atexit(DumpUnfreed);
#endif

#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif

#ifdef HAVE_GSTREAMER
	gst_init(&argc, &argv);
#endif

	// set pythonpath if unset
	setenv("PYTHONPATH", LIBDIR "/enigma2/python", 0);
	printf("PYTHONPATH: %s\n", getenv("PYTHONPATH"));
	
	bsodLogInit();

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


		/* ok, this is currently hardcoded for arabic. */
			/* some characters are wrong in the regular font, force them to use the replacement font */
	for (int i = 0x60c; i <= 0x66d; ++i)
		eTextPara::forceReplacementGlyph(i);
	eTextPara::forceReplacementGlyph(0xfdf2);
	for (int i = 0xfe80; i < 0xff00; ++i)
		eTextPara::forceReplacementGlyph(i);
	

	eWidgetDesktop dsk(eSize(720, 576));
	eWidgetDesktop dsk_lcd(eSize(132, 64));
	
	dsk.setStyleID(0);
	dsk_lcd.setStyleID(1);
	
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
	
	gRC::getInstance()->setSpinnerDC(my_dc);

	eRCInput::getInstance()->keyEvent.connect(slot(keyEvent));
	
	printf("executing main\n");
	
	bsodCatchSignals();

	setIoPrio(IOPRIO_CLASS_BE, 3);

	python.execute("mytest", "__main__");
	
	if (exit_code == 5) /* python crash */
		bsodFatal();
	
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
