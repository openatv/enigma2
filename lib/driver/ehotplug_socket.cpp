#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/driver/ehotplug_socket.h>

#define HOTPLUG_SOCKET_PATH "/var/run/hotplug.socket"

eHotplugSocket *eHotplugSocket::instance;

eHotplugSocket::eHotplugSocket()
	: m_listenfd(-1), m_sockpath(HOTPLUG_SOCKET_PATH)
{
	instance = this;

	unlink(m_sockpath);

	m_listenfd = socket(AF_UNIX, SOCK_STREAM, 0);
	if (m_listenfd < 0) {
		eDebug("[eHotplugSocket] socket: %s", strerror(errno));
		return;
	}

	int flags = fcntl(m_listenfd, F_GETFL);
	if (flags < 0 || fcntl(m_listenfd, F_SETFL, flags | O_NONBLOCK) < 0) {
		eDebug("[eHotplugSocket] fcntl: %s", strerror(errno));
		close(m_listenfd);
		m_listenfd = -1;
		return;
	}

	struct sockaddr_un addr;
	memset(&addr, 0, sizeof(addr));
	addr.sun_family = AF_UNIX;
	strncpy(addr.sun_path, m_sockpath, sizeof(addr.sun_path) - 1);
	socklen_t addrlen = sizeof(addr.sun_family) + strlen(addr.sun_path);

	if (bind(m_listenfd, (struct sockaddr *)&addr, addrlen) < 0) {
		eDebug("[eHotplugSocket] bind: %s", strerror(errno));
		close(m_listenfd);
		m_listenfd = -1;
		return;
	}
	if (listen(m_listenfd, 4) < 0) {
		eDebug("[eHotplugSocket] listen: %s", strerror(errno));
		close(m_listenfd);
		m_listenfd = -1;
		return;
	}

	m_listensn = eSocketNotifier::create(eApp, m_listenfd, POLLIN);
	CONNECT(m_listensn->activated, eHotplugSocket::onAccept);
	eDebug("[eHotplugSocket] listening on %s", m_sockpath);
}

eHotplugSocket::~eHotplugSocket()
{
	for (Conn *c : m_conns) {
		c->sn = nullptr;
		close(c->fd);
		delete c;
	}
	m_conns.clear();
	m_listensn = nullptr;
	if (m_listenfd >= 0) {
		close(m_listenfd);
		unlink(m_sockpath);
	}
	instance = nullptr;
}

eHotplugSocket *eHotplugSocket::getInstance()
{
	return instance;
}

void eHotplugSocket::onAccept(int /*what*/)
{
	int fd = accept(m_listenfd, nullptr, nullptr);
	if (fd < 0) {
		if (errno != EAGAIN && errno != EINTR)
			eDebug("[eHotplugSocket] accept: %s", strerror(errno));
		return;
	}
	int flags = fcntl(fd, F_GETFL);
	if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
		eDebug("[eHotplugSocket] fcntl conn: %s", strerror(errno));
		close(fd);
		return;
	}

	Conn *conn = new Conn;
	conn->fd = fd;
	conn->sn = eSocketNotifier::create(eApp, fd, POLLIN | POLLHUP | POLLERR);
	conn->sn->activated.connect(
		sigc::bind(sigc::mem_fun(*this, &eHotplugSocket::onData), conn)
	);
	m_conns.push_back(conn);
}

void eHotplugSocket::onData(int what, Conn *c)
{
	if (what & POLLIN) {
		char buf[4096];
		ssize_t n = read(c->fd, buf, sizeof(buf));
		if (n > 0) {
			c->buffer.append(buf, (size_t)n);
			return;
		}
		if (n < 0 && (errno == EAGAIN || errno == EINTR))
			return;
		/* n == 0: remote closed; fall through to emit + cleanup */
	}
	if (!c->buffer.empty())
		dataReceived(c->buffer.c_str());
	closeConn(c);
}

void eHotplugSocket::closeConn(Conn *c)
{
	m_conns.remove(c);
	c->sn = nullptr;
	close(c->fd);
	delete c;
}

eAutoInitP0<eHotplugSocket> init_hotplug_socket(eAutoInitNumbers::rc + 2, "Hotplug socket");
