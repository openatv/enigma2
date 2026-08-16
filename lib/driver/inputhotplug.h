#ifndef __lib_driver_inputhotplug_h
#define __lib_driver_inputhotplug_h

#include <lib/python/connections.h>

class eSocketNotifier;

class eInputHotplug
{
#ifndef SWIG
	static eInputHotplug *instance;
	int m_fd;
	ePtr<eSocketNotifier> m_sn;
	void doRead(int what);
	void parseUevent(const char *buf, ssize_t len);
#endif
public:
#ifndef SWIG
	eInputHotplug();
	~eInputHotplug();
#endif
#ifdef SWIG
	eInputHotplug();
	~eInputHotplug();
#endif
	static eInputHotplug *getInstance();
	/* Fired on input device add/remove.
	 * arg0: action   ("add" or "remove")
	 * arg1: devpath  ("/dev/input/eventN") */
	PSignal2<void, const char *, const char *> hotplugEvent;
};

#endif
