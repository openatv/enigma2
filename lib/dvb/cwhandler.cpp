#include <lib/dvb/cwhandler.h>
#include <lib/base/eerror.h>

#include <unistd.h>
#include <string.h>
#include <poll.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <linux/dvb/ca.h>
#include <arpa/inet.h>

eDVBCWHandler* eDVBCWHandler::instance = nullptr;

eDVBCWHandler* eDVBCWHandler::getInstance()
{
	if (!instance)
		instance = new eDVBCWHandler();
	return instance;
}

eDVBCWHandler::eDVBCWHandler()
	: m_running(false)
	, m_thread(0)
{
	m_wake_pipe[0] = -1;
	m_wake_pipe[1] = -1;

	if (pipe2(m_wake_pipe, O_NONBLOCK | O_CLOEXEC) != 0)
	{
		eWarning("[eDVBCWHandler] Failed to create wake pipe: %m");
		return;
	}

	m_running = true;
	if (pthread_create(&m_thread, nullptr, threadFunc, this) != 0)
	{
		eWarning("[eDVBCWHandler] Failed to create thread: %m");
		m_running = false;
		return;
	}

	eDebug("[eDVBCWHandler] Started");
}

eDVBCWHandler::~eDVBCWHandler()
{
	m_running = false;

	// Wake up poll
	if (m_wake_pipe[1] >= 0)
	{
		char c = 'q';
		ssize_t ret __attribute__((unused)) = ::write(m_wake_pipe[1], &c, 1);
	}

	if (m_thread)
		pthread_join(m_thread, nullptr);

	// Close all connections
	{
		std::lock_guard<std::mutex> lock(m_connections_mutex);
		for (auto& conn : m_connections)
		{
			if (conn.softcam_fd >= 0) ::close(conn.softcam_fd);
			if (conn.proxy_fd >= 0) ::close(conn.proxy_fd);
			// client_fd is owned by ePMTClient
		}
		m_connections.clear();
	}

	if (m_wake_pipe[0] >= 0) ::close(m_wake_pipe[0]);
	if (m_wake_pipe[1] >= 0) ::close(m_wake_pipe[1]);

	eDebug("[eDVBCWHandler] Stopped");
}

void eDVBCWHandler::registerEngine(uint32_t serviceId, eDVBCSAEngine* engine, uint8_t ecm_mode)
{
	std::lock_guard<std::mutex> lock(m_targets_mutex);

	// Check if this exact engine is already registered for this serviceId
	auto range = m_targets.equal_range(serviceId);
	for (auto it = range.first; it != range.second; ++it)
	{
		if (it->second.engine == engine)
		{
			// Already registered - just update ecm_mode
			it->second.ecm_mode = ecm_mode;
			eDebug("[eDVBCWHandler] Registered engine for serviceId %u, ecm_mode=0x%02X", serviceId, ecm_mode);
			return;
		}
	}

	// New engine for this serviceId (e.g. Timeshift alongside Live)
	CwTarget target;
	target.engine = engine;
	target.ecm_mode = ecm_mode;
	m_targets.insert({serviceId, target});
	eDebug("[eDVBCWHandler] Registered engine for serviceId %u, ecm_mode=0x%02X", serviceId, ecm_mode);
}

void eDVBCWHandler::unregisterEngine(uint32_t serviceId, eDVBCSAEngine* engine)
{
	std::lock_guard<std::mutex> lock(m_targets_mutex);
	auto range = m_targets.equal_range(serviceId);
	for (auto it = range.first; it != range.second; ++it)
	{
		if (it->second.engine == engine)
		{
			m_targets.erase(it);
			eDebug("[eDVBCWHandler] Unregistered engine for serviceId %u", serviceId);
			return;
		}
	}
	eDebug("[eDVBCWHandler] Unregister: no engine found for serviceId %u", serviceId);
}

void eDVBCWHandler::updateEcmMode(uint32_t serviceId, eDVBCSAEngine* engine, uint8_t ecm_mode)
{
	std::lock_guard<std::mutex> lock(m_targets_mutex);
	auto range = m_targets.equal_range(serviceId);
	for (auto it = range.first; it != range.second; ++it)
	{
		if (it->second.engine == engine)
		{
			if (it->second.ecm_mode != ecm_mode)
			{
				eDebug("[eDVBCWHandler] Updated ecm_mode for serviceId %u to 0x%02X", serviceId, ecm_mode);
				it->second.ecm_mode = ecm_mode;
			}
			return;
		}
	}
}

int eDVBCWHandler::addConnection(int softcam_fd)
{
	int pair[2];
	if (socketpair(AF_UNIX, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0, pair) != 0)
	{
		eWarning("[eDVBCWHandler] socketpair failed: %m");
		return -1;
	}

	// Set softcam_fd to non-blocking for our poll loop
	int flags = fcntl(softcam_fd, F_GETFL, 0);
	if (flags >= 0)
		fcntl(softcam_fd, F_SETFL, flags | O_NONBLOCK);

	Connection conn;
	conn.softcam_fd = softcam_fd;
	conn.proxy_fd = pair[0];  // our end
	conn.client_fd = pair[1]; // ePMTClient's end

	{
		std::lock_guard<std::mutex> lock(m_connections_mutex);
		m_connections.push_back(conn);
	}

	// Wake up poll loop to pick up new connection
	char c = 'w';
	ssize_t ret __attribute__((unused)) = ::write(m_wake_pipe[1], &c, 1);

	eDebug("[eDVBCWHandler] Added connection: softcam_fd=%d, proxy_fd=%d, client_fd=%d", softcam_fd, pair[0], pair[1]);
	return pair[1]; // return the fd for ePMTClient
}

void eDVBCWHandler::removeConnection(int client_fd)
{
	std::lock_guard<std::mutex> lock(m_connections_mutex);
	for (auto it = m_connections.begin(); it != m_connections.end(); ++it)
	{
		if (it->client_fd == client_fd)
		{
			eDebug("[eDVBCWHandler] Removing connection: softcam_fd=%d, client_fd=%d", it->softcam_fd, client_fd);
			if (it->softcam_fd >= 0) ::close(it->softcam_fd);
			if (it->proxy_fd >= 0) ::close(it->proxy_fd);
			m_connections.erase(it);

			// Wake up poll loop
			char c = 'w';
			ssize_t ret __attribute__((unused)) = ::write(m_wake_pipe[1], &c, 1);
			return;
		}
	}
}

void* eDVBCWHandler::threadFunc(void* arg)
{
	static_cast<eDVBCWHandler*>(arg)->threadLoop();
	return nullptr;
}

void eDVBCWHandler::threadLoop()
{
	char buf[4096];

	while (m_running)
	{
		// Build poll fd list
		std::vector<struct pollfd> pfds;
		std::vector<Connection> conns_snapshot;

		{
			std::lock_guard<std::mutex> lock(m_connections_mutex);
			conns_snapshot = m_connections;
		}

		// Wake pipe
		struct pollfd wpfd;
		wpfd.fd = m_wake_pipe[0];
		wpfd.events = POLLIN;
		wpfd.revents = 0;
		pfds.push_back(wpfd);

		// For each connection: poll softcam_fd and proxy_fd
		for (const auto& conn : conns_snapshot)
		{
			struct pollfd pfd;

			pfd.fd = conn.softcam_fd;
			pfd.events = POLLIN;
			pfd.revents = 0;
			pfds.push_back(pfd);

			pfd.fd = conn.proxy_fd;
			pfd.events = POLLIN;
			pfd.revents = 0;
			pfds.push_back(pfd);
		}

		int ret = poll(pfds.data(), pfds.size(), 1000);
		if (ret < 0)
		{
			if (errno == EINTR)
				continue;
			eWarning("[eDVBCWHandler] poll error: %m");
			break;
		}

		if (ret == 0)
			continue;

		// Check wake pipe
		if (pfds[0].revents & POLLIN)
		{
			// Drain pipe
			while (::read(m_wake_pipe[0], buf, sizeof(buf)) > 0);
		}

		// Process connections
		for (size_t i = 0; i < conns_snapshot.size(); i++)
		{
			int softcam_idx = 1 + i * 2;
			int proxy_idx = 2 + i * 2;
			const Connection& conn = conns_snapshot[i];

			// Softcam → proxy_fd (and intercept CWs)
			bool softcam_disconnected = false;
			if (pfds[softcam_idx].revents & POLLIN)
			{
				ssize_t n = ::read(conn.softcam_fd, buf, sizeof(buf));
				if (n > 0)
				{
					// Intercept CW packets before forwarding
					processCwFromRawPacket((const uint8_t*)buf, n);
					// Forward everything to ePMTClient via socketpair
					ssize_t written = 0;
					while (written < n)
					{
						ssize_t w = ::write(conn.proxy_fd, buf + written, n - written);
						if (w < 0)
						{
							if (errno == EAGAIN || errno == EINTR)
							{
								// Socketpair buffer full (MainLoop not reading) - drop this chunk
								// CWs were already intercepted and setKey() called
								eDebug("[eDVBCWHandler] Socketpair buffer full, dropping %zd bytes (CWs already processed)", n - written);
								break;
							}
							break; // Error
						}
						written += w;
					}
				}
				else if (n == 0)
				{
					// EOF - softcam closed the connection
					eDebug("[eDVBCWHandler] Softcam EOF on fd %d", conn.softcam_fd);
					softcam_disconnected = true;
				}
				else if (errno != EINTR && errno != EAGAIN)
				{
					eDebug("[eDVBCWHandler] Softcam read error on fd %d: %m", conn.softcam_fd);
					softcam_disconnected = true;
				}
			}

			// Handle softcam disconnect
			if (softcam_disconnected || (pfds[softcam_idx].revents & (POLLHUP | POLLERR)))
			{
				eDebug("[eDVBCWHandler] Softcam disconnected on fd %d", conn.softcam_fd);
				// Close proxy_fd so ePMTClient gets connectionLost
				std::lock_guard<std::mutex> lock(m_connections_mutex);
				for (auto it = m_connections.begin(); it != m_connections.end(); ++it)
				{
					if (it->softcam_fd == conn.softcam_fd)
					{
						::close(it->softcam_fd);
						::close(it->proxy_fd);
						m_connections.erase(it);
						break;
					}
				}
				continue;
			}

			// proxy_fd → softcam (CAPMT writes from ePMTClient)
			bool proxy_disconnected = false;
			if (pfds[proxy_idx].revents & POLLIN)
			{
				ssize_t n = ::read(conn.proxy_fd, buf, sizeof(buf));
				if (n > 0)
				{
					ssize_t written = 0;
					while (written < n)
					{
						ssize_t w = ::write(conn.softcam_fd, buf + written, n - written);
						if (w < 0)
						{
							if (errno == EAGAIN || errno == EINTR)
							{
								// Brief spin-wait for softcam to catch up (small CAPMT packets)
								usleep(1000);
								continue;
							}
							break; // Error
						}
						written += w;
					}
				}
				else if (n == 0)
				{
					eDebug("[eDVBCWHandler] ePMTClient EOF on proxy_fd %d", conn.proxy_fd);
					proxy_disconnected = true;
				}
				else if (errno != EINTR && errno != EAGAIN)
				{
					eDebug("[eDVBCWHandler] ePMTClient read error on proxy_fd %d: %m", conn.proxy_fd);
					proxy_disconnected = true;
				}
			}

			// Handle ePMTClient disconnect
			if (proxy_disconnected || (pfds[proxy_idx].revents & (POLLHUP | POLLERR)))
			{
				eDebug("[eDVBCWHandler] ePMTClient disconnected on proxy_fd %d", conn.proxy_fd);
				std::lock_guard<std::mutex> lock(m_connections_mutex);
				for (auto it = m_connections.begin(); it != m_connections.end(); ++it)
				{
					if (it->proxy_fd == conn.proxy_fd)
					{
						::close(it->softcam_fd);
						::close(it->proxy_fd);
						m_connections.erase(it);
						break;
					}
				}
			}
		}
	}
}

void eDVBCWHandler::processCwFromRawPacket(const uint8_t* data, int len)
{
	/*
	 * Softcam Protocol 3 packet format:
	 * [0xA5] [msgid: 4 bytes] [tag: 4 bytes] [data...]
	 *
	 * CA_SET_DESCR tag: 0x40 0x10 0x6F 0x86
	 * CA_SET_DESCR data: 1 byte padding + ca_descr_t (16 bytes) = 17 bytes
	 *
	 * Total CA_SET_DESCR packet: 1 + 4 + 4 + 17 = 26 bytes
	 *
	 * ca_descr_t: { uint32_t index, uint32_t parity, uint8_t cw[8] }
	 *
	 * Note: No residual buffering needed - Unix domain sockets deliver
	 * small packets atomically, and ePMTClient handles reassembly for
	 * all packet types via its state machine on the socketpair end.
	 */
	static const uint8_t CW_TAG[] = { 0x40, 0x10, 0x6F, 0x86 };
	static const int CW_PACKET_SIZE = 26; // 0xA5 + 4 msgid + 4 tag + 17 data

	int pos = 0;
	while (pos <= len - CW_PACKET_SIZE)
	{
		// Find next 0xA5 frame start
		if (data[pos] != 0xA5)
		{
			pos++;
			continue;
		}

		// Check if this is a CA_SET_DESCR packet
		// Tag is at offset 5 (after 0xA5 + 4 byte msgid)
		if (memcmp(&data[pos + 5], CW_TAG, 4) != 0)
		{
			// Not a CW packet - skip past this frame start
			pos++;
			continue;
		}

		// Extract serviceId from msgid (bytes 1-4, big-endian)
		uint32_t serviceId;
		memcpy(&serviceId, &data[pos + 1], 4);
		serviceId = ntohl(serviceId);

		// Extract ca_descr_t from data (offset 10 = 1+4+4+1 padding)
		ca_descr_t descr;
		memcpy(&descr, &data[pos + 10], sizeof(ca_descr_t));
		descr.index = ntohl(descr.index);
		descr.parity = ntohl(descr.parity);

		// Deliver CW to all engines registered for this serviceId (Live + Timeshift)
		{
			std::lock_guard<std::mutex> lock(m_targets_mutex);
			auto range = m_targets.equal_range(serviceId);
			for (auto it = range.first; it != range.second; ++it)
			{
				it->second.engine->setKey(descr.parity, it->second.ecm_mode, descr.cw);
				eDebug("[eDVBCWHandler] CW set: parity=%d, hasEven=%d, hasOdd=%d, CW=%02X",
					descr.parity, it->second.engine->hasEvenKey(), it->second.engine->hasOddKey(), descr.cw[0]);
			}
		}

		pos += CW_PACKET_SIZE;
	}
}
