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

#include <lib/gui/elistboxcontent.h>

#include <lib/driver/rc.h>

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

eWidgetDesktop *wdsk;

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
	if (!key.flags)
		keyPressed(key.code);
}

/************************************************/
#include <lib/dvb/dvb.h>
#include <lib/dvb/db.h>
#include <lib/dvb/isection.h>
#include <lib/dvb/esection.h>
#include <lib/dvb_si/pmt.h>
#include <lib/dvb/scan.h>
#include <unistd.h>

class eMain: public eApplication, public Object
{
	eInit init;
	
	ePtr<eDVBScan> m_scan;

	ePtr<eDVBResourceManager> m_mgr;
	ePtr<iDVBChannel> m_channel;
	ePtr<eDVBDB> m_dvbdb;

	void scanEvent(int evt)
	{
		eDebug("scan event %d!", evt);
		if (evt == eDVBScan::evtFinish)
		{
			m_scan->insertInto(m_dvbdb);
			quit(0);
		}
	}
	ePtr<eConnection> m_scan_event_connection;
public:
	eMain()
	{
		init.setRunlevel(eAutoInitNumbers::main);

#if 0
		m_dvbdb = new eDVBDB();
		m_mgr = new eDVBResourceManager();

		eDVBFrontendParametersSatellite fesat;
		
		fesat.frequency = 11817000; // 12070000;
		fesat.symbol_rate = 27500000;
		fesat.polarisation = eDVBFrontendParametersSatellite::Polarisation::Vertical;
		fesat.fec = eDVBFrontendParametersSatellite::FEC::f3_4;
		fesat.inversion = eDVBFrontendParametersSatellite::Inversion::Off;
		fesat.orbital_position = 192;

		eDVBFrontendParameters *fe = new eDVBFrontendParameters();
		
		fe->setDVBS(fesat);

		if (m_mgr->allocateRawChannel(m_channel))
			eDebug("shit it failed!");

		eDebug("starting scan...");
		
		std::list<ePtr<iDVBFrontendParameters> > list;
		
		list.push_back(fe);
		
		m_scan = new eDVBScan(m_channel);
		m_scan->start(list);
		m_scan->connectEvent(slot(*this, &eMain::scanEvent), m_scan_event_connection);
#endif
	}
	
	~eMain()
	{
		m_scan = 0;
	}
};

/************************************************/


int main(int argc, char **argv)
{
#ifdef OBJECT_DEBUG
	atexit(object_dump);
#endif


	ePython python;
	eMain main;

#if 1
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
	dsk.setBackgroundColor(gColor(0));
	dsk.setDC(my_dc);
#endif

		/* redrawing is done in an idle-timer, so we have to set the context */
	dsk.setRedrawTask(main);
	
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
