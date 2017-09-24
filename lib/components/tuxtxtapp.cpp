#include <lib/components/tuxtxtapp.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/rc.h>
#include <lib/gdi/lcd.h>
#include <lib/gdi/fb.h>
#include <lib/gui/ewidget.h>
#include <lib/gui/ewidgetdesktop.h>
#include <lib/python/python.h>

extern "C" int tuxtxt_run_ui(int pid, int demux);
extern "C" int tuxtxt_init();
extern "C" void tuxtxt_start(int tpid, int demux);
extern "C" int tuxtxt_stop();
extern "C" void tuxtxt_close();
extern "C" void tuxtxt_handlePressedKey(int key);

eAutoInitP0<eTuxtxtApp> init_eTuxtxtApp(eAutoInitNumbers::lowlevel, "Tuxtxt");
eTuxtxtApp *eTuxtxtApp::instance = NULL;

#if HAVE_AMLOGIC
eTuxtxtApp::eTuxtxtApp() : pid(0), demux(0), enableTtCaching(false), uiRunning(false), messagePump(eApp, 0)
#else
eTuxtxtApp::eTuxtxtApp() : pid(0), enableTtCaching(false), uiRunning(false), messagePump(eApp, 0)
#endif

{
	CONNECT(messagePump.recv_msg, eTuxtxtApp::recvEvent);
	pthread_mutex_init( &cacheChangeLock, 0 );
	if (!instance)
		instance=this;
}

eTuxtxtApp::~eTuxtxtApp()
{
	if (instance==this)
		instance=0;
	kill();
	pthread_mutex_destroy( &cacheChangeLock );
}

void eTuxtxtApp::recvEvent(const int &evt)
{
	uiRunning = false;
	eDBoxLCD::getInstance()->unlock();
	eDBoxLCD::getInstance()->update();
	fbClass::getInstance()->unlock();
	/* emit */appClosed();
}

int eTuxtxtApp::startUi()
{
	if (fbClass::getInstance()->lock() >= 0)
	{
		eDBoxLCD::getInstance()->lock();
		pthread_mutex_lock( &cacheChangeLock );
		uiRunning = true;
		pthread_mutex_unlock( &cacheChangeLock );
		run();
	}
	else
	{
		/* emit */appClosed();
	}
	return 0;
}

void eTuxtxtApp::thread()
{
	hasStarted();
	tuxtxt_run_ui(pid, demux);
}

void eTuxtxtApp::thread_finished()
{
	messagePump.send(0);
}

void eTuxtxtApp::initCache()
{
	tuxtxt_init();
}

void eTuxtxtApp::freeCache()
{
	pthread_mutex_lock( &cacheChangeLock );
	if ( !uiRunning )
	{
		tuxtxt_close();
		pid = 0;
	}
	pthread_mutex_unlock( &cacheChangeLock );
}

void eTuxtxtApp::startCaching( int tpid, int tdemux)
{
	pid = tpid;
	demux = tdemux;
	if (enableTtCaching)
		tuxtxt_start(pid, demux);
}

void eTuxtxtApp::stopCaching()
{
	pthread_mutex_lock( &cacheChangeLock );
	if ( !uiRunning )
		tuxtxt_stop();

	pthread_mutex_unlock( &cacheChangeLock );
}

void eTuxtxtApp::setEnableTtCachingOnOff( int onoff )
{
	if (onoff && !enableTtCaching)		// Switch caching on
	{
		eDebug("[eTuxttxtApp] enable caching");
		enableTtCaching = true;
		if (pid)
		{
			initCache();
			startCaching(pid, demux);
		}
	}
	else if (!onoff && enableTtCaching)	// Switch caching off
	{
		eDebug("[eTuxttxtApp] disable caching");
		enableTtCaching = false;
		int savePid = pid;
		freeCache();
		pid = savePid;
	}
}

void eTuxtxtApp::handleKey( int key )
{
	tuxtxt_handlePressedKey(key);
}