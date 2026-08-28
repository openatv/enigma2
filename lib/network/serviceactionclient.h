#ifndef __lib_network_serviceactionclient_h
#define __lib_network_serviceactionclient_h

#include <stdint.h>
#include <lib/python/connections.h>

#ifndef SWIG
#include <map>
#include <string>
#include <sigc++/connection.h>
#include <lib/base/ebase.h>
#endif

#ifdef SWIG
class eServiceActionClient
#else
class eServiceActionClient : public sigc::trackable
#endif
{
#ifndef SWIG
	struct Request {
		int fd = -1;
		ePtr<eSocketNotifier> sn;
		ePtr<eTimer> timer;
		std::string buf;
		uint32_t id = 0;
		std::string type;
		sigc::connection snConn;
		sigc::connection timerConn;
	};

	struct Slot {
		uint32_t currentId = 0;
		bool hasPending = false;
		uint32_t pendingId = 0;
		std::string pendingData;
		int pendingTimeout = 15000;
	};

	uint32_t m_nextId = 1;
	std::map<uint32_t, Request *> m_inflight;
	std::map<std::string, Slot> m_slots;

	void _fire(uint32_t id, const std::string &type, const std::string &data, int timeoutMs);
	void _readable(int what, Request *r);
	void _onTimeout(Request *r);
	void _cleanup(Request *r);
	void _done(uint32_t id, const std::string &type, int exitCode);
#endif

public:
	/* Emitted when an action completes: (requestId, exitCode)  exitCode=0 means success */
	PSignal2<void, int, int> actionResult;

	static eServiceActionClient *getInstance();

	/* Sends an action to the socketdaemon asynchronously.
	 * Returns a request ID > 0 that will be echoed in actionResult.
	 * If the same type is already in flight the new request is queued and
	 * replaces any previously queued (but not yet started) request of the
	 * same type. */
	uint32_t sendAction(const std::string &type, const std::string &data, int timeoutMs = 15000);
};

#endif /* __lib_network_serviceactionclient_h */
