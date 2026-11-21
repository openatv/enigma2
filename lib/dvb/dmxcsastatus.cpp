#include <fcntl.h>
#include <linux/netlink.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/dvb/dmxcsastatus.h>

#ifndef NETLINK_KOBJECT_UEVENT
#define NETLINK_KOBJECT_UEVENT 15
#endif

eDMXCSAStatus *eDMXCSAStatus::instance = nullptr;

eDMXCSAStatus::eDMXCSAStatus()
	: m_fd(-1), m_active(0), m_uevent_fd(-1)
{
	instance = this;

	m_fd = ::open("/sys/module/dmxcsa/active", O_RDONLY | O_CLOEXEC);
	if (m_fd < 0)
		return;	// No software descrambler on this box.

	readActive();
	// A sysfs file is always readable; a change shows as POLLPRI.
	m_sn = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Priority);
	CONNECT(m_sn->activated, eDMXCSAStatus::notified);
	eDebug("[eDMXCSAStatus] watching /sys/module/dmxcsa/active");

	struct sockaddr_nl sa = {};
	sa.nl_family = AF_NETLINK;
	sa.nl_groups = 1;	// The events the kernel sends itself.
	m_uevent_fd = ::socket(AF_NETLINK, SOCK_DGRAM | SOCK_CLOEXEC, NETLINK_KOBJECT_UEVENT);
	if (m_uevent_fd >= 0 && ::bind(m_uevent_fd, (struct sockaddr *)&sa, sizeof(sa)) < 0)
	{
		::close(m_uevent_fd);
		m_uevent_fd = -1;
	}
	if (m_uevent_fd < 0)
	{
		eDebug("[eDMXCSAStatus] no uevents: %m");
		return;
	}
	m_uevent_sn = eSocketNotifier::create(eApp, m_uevent_fd, eSocketNotifier::Read);
	CONNECT(m_uevent_sn->activated, eDMXCSAStatus::readUevent);
}

eDMXCSAStatus::~eDMXCSAStatus()
{
	m_sn = nullptr;
	m_uevent_sn = nullptr;
	if (m_fd >= 0)
		::close(m_fd);
	if (m_uevent_fd >= 0)
		::close(m_uevent_fd);
	if (instance == this)
		instance = nullptr;
}

void eDMXCSAStatus::readActive()
{
	char buf[128];
	unsigned int active = 0;

	// Reading from the start is what arms the next notification.
	if (ssize_t n = ::pread(m_fd, buf, sizeof(buf) - 1, 0); n > 0)
	{
		buf[n] = 0;
		const char *p = buf;
		for (;;)
		{
			char *end;
			long demux = strtol(p, &end, 10);
			if (end == p)
				break;
			if (demux >= 0 && demux < 32)
				active |= 1u << demux;
			p = end;
		}
	}
	m_active = active;
}

void eDMXCSAStatus::notified(int)
{
	unsigned int was = m_active;

	readActive();
	if (m_active != was)
	{
		eDebug("[eDMXCSAStatus] active demuxes %#x -> %#x", was, m_active);
		activeChanged();
	}
}

void eDMXCSAStatus::readUevent(int)
{
	char buf[2048];
	ssize_t len;

	// Every uevent of the box arrives here; only those of the module count.
	while ((len = ::recv(m_uevent_fd, buf, sizeof(buf) - 1, MSG_DONTWAIT)) > 0)
	{
		const char *what = nullptr;
		bool ours = false;
		int demux = -1;

		buf[len] = 0;
		for (const char *p = buf; p < buf + len; p += strlen(p) + 1)
		{
			if (!strcmp(p, "DEVPATH=/module/dmxcsa"))
				ours = true;
			else if (!strncmp(p, "DMXCSA_EVENT=", 13))
				what = p + 13;
			else if (!strncmp(p, "DMXCSA_DEMUX=", 13))
				demux = atoi(p + 13);
		}
		if (!ours || !what || demux < 0)
			continue;
		eDebug("[eDMXCSAStatus] demux%d: %s", demux, what);
		if (!strcmp(what, "raised"))
			event(demux, evDelayRaised);
		else if (!strcmp(what, "limit"))
			event(demux, evDelayLimit);
		else if (!strcmp(what, "badcw"))
			event(demux, evBadCw);
	}
}

eAutoInitP0<eDMXCSAStatus> init_dmxcsastatus(eAutoInitNumbers::rc + 4, "software descrambler status");
