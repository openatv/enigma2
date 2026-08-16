#pragma once

#include <lib/base/object.h>
#include <lib/python/connections.h>
#include <lib/python/python.h>

#ifndef SWIG
#include <avahi-client/lookup.h>
#include <libsig_comp.h>
#include <map>
#include <string>
#include <utility>
#include <vector>

class eMainloop;
class eTimer;

/* Initialization and shutdown */
void e2avahi_init(eMainloop* reactor);
void e2avahi_close();
#endif

/* Enable/disable eDebug() output from e2avahi.cpp */
void e2avahi_set_debug(bool enable);

/* Offer a service. There's currently no way to withdraw it. Leave
 * service_name NULL or blank to use avahi's local hostname as service
 * name (recommended, since it must be unique on the network) */
void e2avahi_announce(const char* service_name, const char* service_type, unsigned short port_num);

#define E2AVAHI_EVENT_ADD 1
#define E2AVAHI_EVENT_REMOVE 2

typedef void (*E2AvahiResolveCallback)(void* userdata, int event, /* One of E2AVAHI_EVENT_... */
									   const char* name, /* name+type combination is unique on the network */
									   const char* type, const char* host_name, /* hostname and port are only valid in ADD */
									   uint16_t port);

/* Starts searching for services on other machines. Basically, one expects
 * to activate this once, and then keep updating a static list of matches. */
void e2avahi_resolve(const char* service_type, E2AvahiResolveCallback callback, void* userdata);
/* Stop looking for services. Callback will no longer be triggered after this. Pass the same
 * data as to the call to e2avahi_resolve. */
void e2avahi_resolve_cancel(const char* service_type, E2AvahiResolveCallback callback, void* userdata);


/* Browses one or more mDNS/DNS-SD service types (e.g. "_smb._tcp") and
 * exposes fully resolved instances (address, interface, TXT records) to
 * Python. Complements e2avahi_resolve() above, which only forwards
 * name/type/hostname/port and cannot be driven from Python directly
 * (a bare C callback pointer isn't usable there). Does not replace the
 * existing API - lib/service/servicepeer.cpp keeps using it unchanged. */
class eNetworkServiceBrowser : public sigc::trackable, public iObject {
	DECLARE_REF(eNetworkServiceBrowser);

#ifndef SWIG
	struct Instance {
		int interfaceIndex;
		int protocol; /* AVAHI_PROTO_INET / AVAHI_PROTO_INET6 */
		std::string serviceName;
		std::string serviceType;
		std::string domain;
		std::string hostname;
		std::vector<std::string> addresses; /* literal, already resolved - no NSS/.local lookup needed */
		unsigned short port;
		std::vector<std::pair<std::string, std::string>> txt;
	};
	/* interfaceIndex:protocol:serviceName:serviceType:domain - the tuple that
	 * uniquely identifies one service instance, not just its name. */
	typedef std::string InstanceKey;

	std::map<InstanceKey, Instance> m_instances;
	std::vector<std::string> m_serviceTypes;
	std::map<std::string, AvahiServiceBrowser*> m_browsers;
	std::map<std::string, bool> m_allForNow;
	bool m_started;
	bool m_failed;
	ePtr<eTimer> m_restartTimer;
	int m_backoffMs;

	static InstanceKey makeKey(int interfaceIndex, int protocol, const char* name, const char* type, const char* domain);

	void tryRegister(const std::string& serviceType);
	void handleBrowserEvent(AvahiServiceBrowser* browser, int interfaceIndex, int protocol, AvahiBrowserEvent event, const char* name, const char* type, const char* domain,
							AvahiLookupResultFlags flags);
	void handleResolverEvent(int interfaceIndex, int protocol, AvahiResolverEvent event, const char* name, const char* type, const char* domain, const char* hostName, const AvahiAddress* address,
							 unsigned short port, AvahiStringList* txt, AvahiLookupResultFlags flags);
	void scheduleRestart();
	void restartTimeout();

	static void avahiBrowserCallback(AvahiServiceBrowser* browser, AvahiIfIndex iface, AvahiProtocol proto, AvahiBrowserEvent event, const char* name, const char* type, const char* domain,
									 AvahiLookupResultFlags flags, void* userdata);
	static void avahiResolverCallback(AvahiServiceResolver* resolver, AvahiIfIndex iface, AvahiProtocol proto, AvahiResolverEvent event, const char* name, const char* type, const char* domain,
									  const char* hostName, const AvahiAddress* address, uint16_t port, AvahiStringList* txt, AvahiLookupResultFlags flags, void* userdata);

	friend void e2avahi_networkservicebrowser_try_register_all();
	friend void e2avahi_networkservicebrowser_reset_all();
	friend void e2avahi_networkservicebrowser_clear_all();
#endif

public:
	eNetworkServiceBrowser();
	~eNetworkServiceBrowser();

	/* Can be called before start() or while already running - a type added
	 * later starts browsing immediately if the browser is already started. */
	void addServiceType(const char* serviceType);

	void start();
	void stop();

	/* Snapshot of all currently known service instances, as a list of dicts
	 * with keys: name, type, domain, hostname, addresses (list of str),
	 * port, interface (int ifindex), protocol ("inet"/"inet6"), txt (dict).
	 * Call after `changed` fires. */
	PyObject* getServices();

	/* Fires on every instance ADD/REMOVE, on ALL_FOR_NOW (initial browse
	 * results for one of the added service types are complete) and on
	 * FAILURE (temporary, browser resubscribes with backoff). No payload -
	 * call getServices() again to get the current snapshot. */
	PSignal0<void> changed;
};
