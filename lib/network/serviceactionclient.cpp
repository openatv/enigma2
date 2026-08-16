#include <lib/network/serviceactionclient.h>
#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
#include <sigc++/bind.h>

#define SAC_SOCKET_PATH "/var/run/daemon.socket"

eServiceActionClient *eServiceActionClient::getInstance()
{
	static eServiceActionClient s_inst;
	return &s_inst;
}

uint32_t eServiceActionClient::sendAction(const std::string &type, const std::string &data, int timeoutMs)
{
	uint32_t id = m_nextId++;
	if (m_nextId == 0)
		m_nextId = 1;

	Slot &slot = m_slots[type];
	if (slot.currentId != 0) {
		/* same type already in flight – queue as pending, replacing any earlier pending */
		slot.hasPending = true;
		slot.pendingId = id;
		slot.pendingData = data;
		slot.pendingTimeout = timeoutMs;
		return id;
	}
	slot.currentId = id;
	_fire(id, type, data, timeoutMs);
	return id;
}

void eServiceActionClient::_fire(uint32_t id, const std::string &type, const std::string &data, int timeoutMs)
{
	int fd = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
	if (fd < 0) {
		eWarning("[SAC] socket: %s", strerror(errno));
		_done(id, type, 127);
		return;
	}

	struct sockaddr_un sa;
	memset(&sa, 0, sizeof(sa));
	sa.sun_family = AF_UNIX;
	strncpy(sa.sun_path, SAC_SOCKET_PATH, sizeof(sa.sun_path) - 1);

	if (::connect(fd, reinterpret_cast<struct sockaddr *>(&sa), sizeof(sa)) < 0) {
		eWarning("[SAC] connect %s: %s", SAC_SOCKET_PATH, strerror(errno));
		::close(fd);
		_done(id, type, 127);
		return;
	}

	/* new line-based protocol: "ACTION <id> <type> <data>\n"
	 * If data is empty, the trailing space+data are omitted. */
	char msg[512];
	int n;
	if (data.empty())
		n = snprintf(msg, sizeof(msg), "ACTION %u %s\n", id, type.c_str());
	else
		n = snprintf(msg, sizeof(msg), "ACTION %u %s %s\n", id, type.c_str(), data.c_str());
	if (n > 0)
		::send(fd, msg, static_cast<size_t>(n), MSG_NOSIGNAL);

	Request *r = new Request();
	r->fd = fd;
	r->id = id;
	r->type = type;
	r->sn = eSocketNotifier::create(eApp, fd, eSocketNotifier::Read);
	r->timer = eTimer::create(eApp);

	r->snConn = r->sn->activated.connect(
		sigc::bind(sigc::mem_fun(*this, &eServiceActionClient::_readable), r));
	r->timerConn = r->timer->timeout.connect(
		sigc::bind(sigc::mem_fun(*this, &eServiceActionClient::_onTimeout), r));
	r->timer->start(timeoutMs, true);

	m_inflight[id] = r;
}

void eServiceActionClient::_readable(int what, Request *r)
{
	if (!(what & eSocketNotifier::Read))
		return;

	char tmp[256];
	ssize_t n = ::recv(r->fd, tmp, sizeof(tmp) - 1, MSG_DONTWAIT);
	if (n <= 0) {
		uint32_t id = r->id;
		std::string type = r->type;
		_cleanup(r);
		_done(id, type, 127);
		return;
	}
	tmp[n] = '\0';
	r->buf += tmp;

	size_t pos = r->buf.find('\n');
	if (pos == std::string::npos)
		return;

	std::string line = r->buf.substr(0, pos);
	uint32_t id = r->id;
	std::string type = r->type;
	_cleanup(r); /* r is invalid after this point */

	int exitCode = 127;
	if (line.size() > 5 && line.compare(0, 5, "DONE ") == 0) {
		/* "DONE <id> <exitcode>" */
		const char *p = line.c_str() + 5;
		strtoul(p, const_cast<char **>(&p), 10); /* skip echoed id */
		while (*p == ' ') p++;
		exitCode = atoi(p);
	} else if (line.size() > 6 && line.compare(0, 6, "ERROR ") == 0) {
		/* "ERROR <id> <exitcode>" */
		const char *p = line.c_str() + 6;
		strtoul(p, const_cast<char **>(&p), 10); /* skip echoed id */
		while (*p == ' ') p++;
		exitCode = atoi(p);
		if (exitCode == 0)
			exitCode = 1;
	} else if (line.size() > 3 && line.compare(0, 3, "RC:") == 0) {
		/* old daemon protocol fallback */
		exitCode = atoi(line.c_str() + 3);
	}

	_done(id, type, exitCode);
}

void eServiceActionClient::_onTimeout(Request *r)
{
	eWarning("[SAC] timeout id=%u type=%s", r->id, r->type.c_str());
	uint32_t id = r->id;
	std::string type = r->type;
	_cleanup(r);
	_done(id, type, 127);
}

void eServiceActionClient::_cleanup(Request *r)
{
	r->snConn.disconnect();
	r->timerConn.disconnect();
	r->timer->stop();
	r->sn = nullptr;
	r->timer = nullptr;
	::close(r->fd);
	r->fd = -1;
	m_inflight.erase(r->id);
	delete r;
}

void eServiceActionClient::_done(uint32_t id, const std::string &type, int exitCode)
{
	/* if a pending request of the same type was queued, fire it now */
	auto it = m_slots.find(type);
	if (it != m_slots.end()) {
		Slot &slot = it->second;
		slot.currentId = 0;
		if (slot.hasPending) {
			uint32_t nid = slot.pendingId;
			std::string ndata = slot.pendingData;
			int nto = slot.pendingTimeout;
			slot.hasPending = false;
			slot.pendingId = 0;
			slot.pendingData.clear();
			slot.currentId = nid;
			_fire(nid, type, ndata, nto);
		}
	}

	actionResult(static_cast<int>(id), exitCode); /* emit */
}
