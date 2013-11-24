#ifndef __LIB_COMPONENTS_TUXTXTAPP_H__
#define __LIB_COMPONENTS_TUXTXTAPP_H__

#include <string>
#include <lib/base/ebase.h>
#include <lib/base/thread.h>
#include <lib/base/message.h>
#include <lib/python/python.h>
#include <lib/python/connections.h>

class eTuxtxtApp: private eThread, public Object
{
#ifndef SWIG
	int pid;
	int demux;
	bool enableTtCaching, uiRunning;
	static eTuxtxtApp *instance;
	pthread_mutex_t cacheChangeLock;

	eFixedMessagePump<int> messagePump;
	void recvEvent(const int &evt);

	void thread();
	void thread_finished();
#endif
public:
	eTuxtxtApp();
	~eTuxtxtApp();
	static eTuxtxtApp *getInstance() { return instance; }
	int startUi();
	void initCache();
	void freeCache();
	void startCaching( int tpid, int tdemux );
	void stopCaching();
	void resetPid() { pid = 0; demux = 0; }
	void setEnableTtCachingOnOff( int onoff );
	void handleKey( int key );
	PSignal0<void> appClosed;
};

#endif // __LIB_COMPONENTS_TUXTXTAPP_H__
