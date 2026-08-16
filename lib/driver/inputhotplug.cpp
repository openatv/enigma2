#include <sys/socket.h>
#include <linux/netlink.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/driver/inputhotplug.h>
#include <lib/driver/rcinput_swig.h>

#ifndef NETLINK_KOBJECT_UEVENT
#define NETLINK_KOBJECT_UEVENT 15
#endif

eInputHotplug *eInputHotplug::instance;

eInputHotplug::eInputHotplug() : m_fd(-1)
{
	instance = this;

	struct sockaddr_nl sa;
	memset(&sa, 0, sizeof(sa));
	sa.nl_family = AF_NETLINK;
	sa.nl_groups = 0xFFFFFFFF;

	m_fd = socket(AF_NETLINK, SOCK_DGRAM, NETLINK_KOBJECT_UEVENT);
	if (m_fd < 0) {
		eDebug("[eInputHotplug] socket: %s", strerror(errno));
		return;
	}
	if (bind(m_fd, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
		eDebug("[eInputHotplug] bind: %s", strerror(errno));
		close(m_fd);
		m_fd = -1;
		return;
	}

	m_sn = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Read);
	CONNECT(m_sn->activated, eInputHotplug::doRead);
	eDebug("[eInputHotplug] listening for input hotplug events");
}

eInputHotplug::~eInputHotplug()
{
	if (m_fd >= 0)
		close(m_fd);
	instance = nullptr;
}

eInputHotplug *eInputHotplug::getInstance()
{
	return instance;
}

void eInputHotplug::doRead(int /*what*/)
{
	char buf[4096];
	ssize_t len = recv(m_fd, buf, sizeof(buf) - 1, MSG_DONTWAIT);
	if (len <= 0)
		return;
	buf[len] = '\0';
	parseUevent(buf, len);
}

void eInputHotplug::parseUevent(const char *buf, ssize_t len)
{
	char action[32]    = {};
	char subsystem[32] = {};
	char devname[64]   = {};

	const char *p   = buf;
	const char *end = buf + len;

	/* raw kernel uevent: first null-terminated record is "ACTION@devpath" */
	const char *at = (const char *)memchr(p, '@', (size_t)(end - p));
	if (at) {
		size_t al = (size_t)(at - p);
		if (al < sizeof(action) - 1)
			memcpy(action, p, al);
	}
	while (p < end && *p) p++;
	if (p < end) p++;

	/* parse KEY=VALUE\0 records */
	while (p < end) {
		if (!*p) { p++; continue; }
		const char *eq = (const char *)memchr(p, '=', (size_t)(end - p));
		if (!eq) break;

		const char *key    = p;
		size_t      klen   = (size_t)(eq - p);
		const char *val    = eq + 1;
		const char *valEnd = (const char *)memchr(val, '\0', (size_t)(end - val));
		if (!valEnd) valEnd = end;
		size_t vlen = (size_t)(valEnd - val);

		if (klen == 6 && !memcmp(key, "ACTION", 6) && !action[0]) {
			size_t n = vlen < sizeof(action) - 1 ? vlen : sizeof(action) - 1;
			memcpy(action, val, n);
		} else if (klen == 9 && !memcmp(key, "SUBSYSTEM", 9)) {
			size_t n = vlen < sizeof(subsystem) - 1 ? vlen : sizeof(subsystem) - 1;
			memcpy(subsystem, val, n);
		} else if (klen == 7 && !memcmp(key, "DEVNAME", 7)) {
			size_t n = vlen < sizeof(devname) - 1 ? vlen : sizeof(devname) - 1;
			memcpy(devname, val, n);
		}

		p = valEnd + 1;
	}

	if (strcmp(subsystem, "input") != 0 || !devname[0] || !action[0])
		return;

	char devpath[80];
	snprintf(devpath, sizeof(devpath), "/dev/%s", devname);

	eDebug("[eInputHotplug] %s %s", action, devpath);

	if (!strcmp(action, "add"))
		addInputDevice(devpath);
	else if (!strcmp(action, "remove"))
		removeInputDevice(devpath);

	/* notify Python subscribers */
	hotplugEvent(action, devpath);
}

eAutoInitP0<eInputHotplug> init_inputhotplug(eAutoInitNumbers::rc + 3, "Input hotplug driver");
