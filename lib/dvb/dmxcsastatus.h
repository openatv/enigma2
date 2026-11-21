#ifndef __lib_dvb_dmxcsastatus_h
#define __lib_dvb_dmxcsastatus_h

#include <lib/base/ebase.h>
#include <sigc++/sigc++.h>

/*
 * The software descrambler (dmxcsa) lists the demuxes that carry a service it
 * descrambles in /sys/module/dmxcsa/active and wakes whoever waits on that
 * file when the list changes. What a viewer should hear of - a control word
 * that came late or does not fit - it sends as a uevent. That is all enigma2
 * knows of it: a state and three events to show, nothing to control.
 */
class eDMXCSAStatus: public sigc::trackable
{
	static eDMXCSAStatus *instance;
	int m_fd;
	unsigned int m_active;	/* one bit per demux */
	ePtr<eSocketNotifier> m_sn;
	int m_uevent_fd;
	ePtr<eSocketNotifier> m_uevent_sn;
	void notified(int what);
	void readActive();
	void readUevent(int what);
public:
	enum { evDelayRaised, evDelayLimit, evBadCw };
	eDMXCSAStatus();
	~eDMXCSAStatus();
	eDMXCSAStatus(const eDMXCSAStatus &) = delete;
	eDMXCSAStatus &operator=(const eDMXCSAStatus &) = delete;
	static eDMXCSAStatus *getInstance() { return instance; }
	bool isActive(int demux) const { return demux >= 0 && demux < 32 && (m_active & (1u << demux)); }
	sigc::signal<void()> activeChanged;
	sigc::signal<void(int, int)> event;	/* demux, one of the events above */
};

#endif
