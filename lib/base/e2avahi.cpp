#include "e2avahi.h"
#include "ebase.h"
#include <algorithm>
#include <arpa/inet.h>
#include <avahi-client/client.h>
#include <avahi-client/lookup.h>
#include <avahi-client/publish.h>
#include <avahi-common/error.h>
#include <avahi-common/malloc.h>
#include <avahi-common/timeval.h>
#include <ifaddrs.h>
#include <list>
#include <net/if.h>
#include <strings.h>

/* Our link to avahi */
static AvahiClient* avahi_client = NULL;

/* Set to true to enable the eDebug() calls below */
static bool avahi_debug = false;
// clang-format off
#define avahiDebug(...) do { if (avahi_debug) eDebug(__VA_ARGS__); } while (0)
// clang-format on

/* API to the E2 event loop */
static AvahiPoll avahi_poll_api;

struct AvahiTimeout : public sigc::trackable {
	ePtr<eTimer> timer;
	AvahiTimeoutCallback callback;
	void* userdata;

	void timeout() {
		// eDebug("[Avahi] timeout elapsed");
		callback(this, userdata);
	}

	AvahiTimeout(eMainloop* mainloop, AvahiTimeoutCallback _callback, void* _userdata) : timer(eTimer::create(mainloop)), callback(_callback), userdata(_userdata) {
		CONNECT(timer->timeout, AvahiTimeout::timeout);
	}
};

struct AvahiWatch : public sigc::trackable {
	ePtr<eSocketNotifier> sn;
	AvahiWatchCallback callback;
	void* userdata;
	int lastEvent;

	void activated(int event) {
		avahiDebug("[Avahi] watch activated: %#x", event);
		lastEvent = event;
		callback(this, sn->getFD(), (AvahiWatchEvent)event, userdata);
	}

	AvahiWatch(eMainloop* mainloop, int fd, int req, AvahiWatchCallback cb, void* ud) : sn(eSocketNotifier::create(mainloop, fd, req)), callback(cb), userdata(ud), lastEvent(0) {
		CONNECT(sn->activated, AvahiWatch::activated);
	}
};

struct AvahiServiceEntry {
	AvahiEntryGroup* group;
	char* service_name;
	char* service_type;
	unsigned short port_num;

	AvahiServiceEntry(const char* n, const char* t, unsigned short p) : group(NULL), service_name(n ? strdup(n) : NULL), service_type(t ? strdup(t) : NULL), port_num(p) {
		avahiDebug("[Avahi] AvahiServiceEntry %s (%s) %u", service_name, service_type, port_num);
	}
	AvahiServiceEntry() : group(NULL), service_name(NULL), service_type(NULL) {}
};
inline bool operator==(const AvahiServiceEntry& lhs, const AvahiServiceEntry& rhs) {
	return (strcmp(lhs.service_type, rhs.service_type) == 0) && (lhs.port_num == rhs.port_num);
}
inline bool operator!=(const AvahiServiceEntry& lhs, const AvahiServiceEntry& rhs) {
	return !(lhs == rhs);
}
typedef std::list<AvahiServiceEntry> AvahiServiceEntryList;
static AvahiServiceEntryList avahi_services;

struct AvahiBrowserEntry {
	AvahiServiceBrowser* browser;
	const char* service_type;
	E2AvahiResolveCallback callback;
	void* userdata;

	AvahiBrowserEntry() : browser(NULL) {} /* For std:list */
	AvahiBrowserEntry(const char* t, E2AvahiResolveCallback cb, void* ud) : browser(NULL), service_type(t), callback(cb), userdata(ud) {}
};
/* Implement equality operator to make "std::find" work */
inline bool operator==(const AvahiBrowserEntry& lhs, const AvahiBrowserEntry& rhs) {
	return (lhs.service_type == rhs.service_type) && (lhs.callback == rhs.callback) && (lhs.userdata == rhs.userdata);
}
inline bool operator!=(const AvahiBrowserEntry& lhs, const AvahiBrowserEntry& rhs) {
	return !(lhs == rhs);
}
typedef std::list<AvahiBrowserEntry> AvahiBrowserEntryList;
static AvahiBrowserEntryList avahi_browsers;

/* eNetworkServiceBrowser instances currently start()ed. Kept here (not inside
 * the class) purely so the existing avahi_client_try_register_all()/
 * avahi_client_reset_all() lifecycle hooks below can (re)register them
 * whenever the avahi client (re)connects, same as for avahi_services/avahi_browsers. */
typedef std::list<eNetworkServiceBrowser*> NetworkServiceBrowserList;
static NetworkServiceBrowserList networkservice_browsers;

static void avahi_group_callback(AvahiEntryGroup* group, AvahiEntryGroupState state, void* d) {}

static void avahi_service_try_register(AvahiServiceEntry* entry) {
	if (entry->group)
		return; /* Already registered */

	if ((!avahi_client) || (avahi_client_get_state(avahi_client) != AVAHI_CLIENT_S_RUNNING)) {
		avahiDebug("[Avahi] Not running yet, cannot register type %s.", entry->service_type);
		return;
	}

	entry->group = avahi_entry_group_new(avahi_client, avahi_group_callback, NULL);
	if (!entry->group) {
		avahiDebug("[Avahi] avahi_entry_group_new failed, cannot register %s %s.", entry->service_type, entry->service_name);
		return;
	}

	const char* service_name = entry->service_name;
	/* Blank or NULL service name, use our host name as service name,
	 * this appears to be what other services do. */
	if ((!service_name) || (!*service_name))
		service_name = avahi_client_get_host_name(avahi_client);

	avahiDebug("[Avahi] Will Register %s (%s) on %s:%u", service_name, entry->service_type, avahi_client_get_host_name(avahi_client), entry->port_num);

	if (!avahi_entry_group_add_service(entry->group, AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC, (AvahiPublishFlags)0, service_name, entry->service_type, NULL, NULL, entry->port_num, NULL)) {
		avahi_entry_group_commit(entry->group);
		avahiDebug("[Avahi] Registered %s (%s) on %s:%u", service_name, entry->service_type, avahi_client_get_host_name(avahi_client), entry->port_num);
	}
	/* NOTE: group is freed by avahi_client_free */
}


/* Browser part */

static void avahi_resolver_callback(AvahiServiceResolver* resolver, AvahiIfIndex iface, AvahiProtocol proto, AvahiResolverEvent event, const char* name, const char* type, const char* domain,
									const char* host_name, const AvahiAddress* address, uint16_t port, AvahiStringList* txt, AvahiLookupResultFlags flags, void* d) {
	AvahiBrowserEntry* entry = (AvahiBrowserEntry*)d;

	switch (event) {
		case AVAHI_RESOLVER_FAILURE:
			avahiDebug("[Avahi] Failed to resolve service '%s' of type '%s': %s", name, type, avahi_strerror(avahi_client_errno(avahi_service_resolver_get_client(resolver))));
			break;
		case AVAHI_RESOLVER_FOUND:
			if (flags & (AVAHI_LOOKUP_RESULT_LOCAL | AVAHI_LOOKUP_RESULT_OUR_OWN))
				break; /* Skip local/own services, we don't want to see them */
			avahiDebug("[Avahi] ADD Service '%s' of type '%s' at %s:%u", name, type, host_name, port);
			entry->callback(entry->userdata, E2AVAHI_EVENT_ADD, name, type, host_name, port);
			break;
	}

	avahi_service_resolver_free(resolver);
}

static void avahi_browser_callback(AvahiServiceBrowser* browser, AvahiIfIndex iface, AvahiProtocol proto, AvahiBrowserEvent event, const char* name, const char* type, const char* domain,
								   AvahiLookupResultFlags flags, void* d) {
	AvahiBrowserEntry* entry = (AvahiBrowserEntry*)d;
	struct AvahiClient* client = avahi_service_browser_get_client(browser);

	switch (event) {
		case AVAHI_BROWSER_NEW:
			avahiDebug("[Avahi] Resolving service '%s' of type '%s'", name, type);
			avahi_service_resolver_new(client, iface, proto, name, type, domain, AVAHI_PROTO_UNSPEC, (AvahiLookupFlags)0, avahi_resolver_callback, d);
			break;
		case AVAHI_BROWSER_REMOVE:
			avahiDebug("[Avahi] REMOVE service '%s' of type '%s' in domain '%s'", name, type, domain);
			entry->callback(entry->userdata, E2AVAHI_EVENT_REMOVE, name, type, NULL, 0);
			break;
		case AVAHI_BROWSER_ALL_FOR_NOW:
			/* Useless information... */
			break;
		case AVAHI_BROWSER_FAILURE:
			avahiDebug("[Avahi] AVAHI_BROWSER_FAILURE");
			/* We'll probably need to restart everything? */
			entry->browser = NULL;
			break;
		case AVAHI_BROWSER_CACHE_EXHAUSTED:
			/* Useless information... */
			break;
	}
}

static void avahi_browser_try_register(AvahiBrowserEntry* entry) {
	if (entry->browser)
		return; /* Already registered */

	if ((!avahi_client) || (avahi_client_get_state(avahi_client) != AVAHI_CLIENT_S_RUNNING)) {
		avahiDebug("[Avahi] Not running yet, cannot browse for type %s.", entry->service_type);
		return;
	}

	entry->browser = avahi_service_browser_new(avahi_client, AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC, entry->service_type, NULL, (AvahiLookupFlags)0, avahi_browser_callback, entry);
	if (!entry->browser) {
		avahiDebug("[Avahi] avahi_service_browser_new failed: %s", avahi_strerror(avahi_client_errno(avahi_client)));
	}
}

/* Friend of eNetworkServiceBrowser (declared in e2avahi.h). */
void e2avahi_networkservicebrowser_try_register_all() {
	for (NetworkServiceBrowserList::iterator it = networkservice_browsers.begin(); it != networkservice_browsers.end(); ++it) {
		for (std::vector<std::string>::iterator t = (*it)->m_serviceTypes.begin(); t != (*it)->m_serviceTypes.end(); ++t) {
			(*it)->tryRegister(*t);
		}
	}
}

/* Friend of eNetworkServiceBrowser. */
void e2avahi_networkservicebrowser_reset_all() {
	for (NetworkServiceBrowserList::iterator it = networkservice_browsers.begin(); it != networkservice_browsers.end(); ++it) {
		for (std::map<std::string, AvahiServiceBrowser*>::iterator b = (*it)->m_browsers.begin(); b != (*it)->m_browsers.end(); ++b) {
			if (b->second)
				avahi_service_browser_free(b->second);
		}
		(*it)->m_browsers.clear();
		/* Keep m_instances/m_allForNow as-is - they'll be superseded once the
		 * client reconnects and browsing resumes, same "stale until refreshed"
		 * approach the Python-side registry uses (see doc section 4.3). */
	}
}

/* Friend of eNetworkServiceBrowser. Used from e2avahi_close(): avahi_client_free()
 * already freed every AvahiServiceBrowser/AvahiServiceResolver owned by the
 * client, so this only drops our now-dangling pointers, never calls
 * avahi_service_browser_free() on them again. */
void e2avahi_networkservicebrowser_clear_all() {
	for (NetworkServiceBrowserList::iterator it = networkservice_browsers.begin(); it != networkservice_browsers.end(); ++it) {
		(*it)->m_browsers.clear();
		(*it)->m_instances.clear();
		(*it)->m_allForNow.clear();
	}
}

static void avahi_client_try_register_all() {
	for (AvahiServiceEntryList::iterator it = avahi_services.begin(); it != avahi_services.end(); ++it) {
		avahi_service_try_register(&(*it));
	}
	for (AvahiBrowserEntryList::iterator it = avahi_browsers.begin(); it != avahi_browsers.end(); ++it) {
		avahi_browser_try_register(&(*it));
	}
	e2avahi_networkservicebrowser_try_register_all();
}

static void avahi_client_reset_all() {
	for (AvahiServiceEntryList::iterator it = avahi_services.begin(); it != avahi_services.end(); ++it) {
		if (it->group) {
			avahi_entry_group_free(it->group);
			it->group = NULL;
		}
	}
	for (AvahiBrowserEntryList::iterator it = avahi_browsers.begin(); it != avahi_browsers.end(); ++it) {
		if (it->browser) {
			avahi_service_browser_free(it->browser);
			it->browser = NULL;
		}
	}
	e2avahi_networkservicebrowser_reset_all();
}

static void avahi_client_callback(AvahiClient* client, AvahiClientState state, void* d) {
	avahiDebug("[Avahi] client state: %d", state);
	switch (state) {
		case AVAHI_CLIENT_S_RUNNING:
			/* The server has startup successfully and registered its host
			 * name on the network, register all our services */
			avahi_client_try_register_all();
			break;
		case AVAHI_CLIENT_FAILURE:
			/* Problem? Maybe we have to re-register everything? */
			avahiDebug("[Avahi] Client failure: %s\n", avahi_strerror(avahi_client_errno(client)));
			break;
		case AVAHI_CLIENT_S_COLLISION:
			/* Let's drop our registered services. When the server is back
			 * in AVAHI_SERVER_RUNNING state we will register them
			 * again with the new host name. */
		case AVAHI_CLIENT_S_REGISTERING:
			/* The server records are now being established. This
			 * might be caused by a host name change. We need to wait
			 * for our own records to register until the host name is
			 * properly esatblished. */
			avahi_client_reset_all();
			break;
		case AVAHI_CLIENT_CONNECTING:
			/* No action... */
			break;
	}
}

/** Create a new watch for the specified file descriptor and for
 * the specified events. The API will call the callback function
 * whenever any of the events happens. */
static AvahiWatch* avahi_watch_new(const AvahiPoll* api, int fd, AvahiWatchEvent event, AvahiWatchCallback callback, void* userdata) {
	avahiDebug("[Avahi] %s(%d %#x)", __func__, fd, event);
	return new AvahiWatch((eMainloop*)api->userdata, fd, event, callback, userdata);
}


/** Update the events to wait for. It is safe to call this function from an AvahiWatchCallback */
static void avahi_watch_update(AvahiWatch* w, AvahiWatchEvent event) {
	avahiDebug("[Avahi] %s(%#x)", __func__, event);
	w->sn->setRequested(event);
}

/** Return the events that happened. It is safe to call this function from an AvahiWatchCallback  */
AvahiWatchEvent avahi_watch_get_events(AvahiWatch* w) {
	avahiDebug("[Avahi] %s", __func__);
	return (AvahiWatchEvent)w->lastEvent;
}

/** Free a watch. It is safe to call this function from an AvahiWatchCallback */
void avahi_watch_free(AvahiWatch* w) {
	avahiDebug("[Avahi] %s", __func__);
	delete w;
}

static void avahi_set_timer(AvahiTimeout* t, const struct timeval* tv) {
	if (tv) {
		/*struct timeval now;
		gettimeofday(&now, NULL);*/
		AvahiUsec usec = (-avahi_age(tv));
		if (usec < 0)
			usec = 0;
		t->timer->start((usec + 999) / 1000, true);
	}
}

/** Set a wakeup time for the polling loop. The API will call the
callback function when the absolute time *tv is reached. If tv is
NULL, the timeout is disabled. After the timeout expired the
callback function will be called and the timeout is disabled. You
can reenable it by calling timeout_update()  */
AvahiTimeout* avahi_timeout_new(const AvahiPoll* api, const struct timeval* tv, AvahiTimeoutCallback callback, void* userdata) {
	//	eDebug("[Avahi] %s", __func__);

	AvahiTimeout* result = new AvahiTimeout((eMainloop*)api->userdata, callback, userdata);
	avahi_set_timer(result, tv);

	return result;
}

/** Update the absolute expiration time for a timeout, If tv is
 * NULL, the timeout is disabled. It is safe to call this function from an AvahiTimeoutCallback */
void avahi_timeout_update(AvahiTimeout* t, const struct timeval* tv) {
	//	eDebug("[Avahi] %s", __func__);
	t->timer->stop();
	avahi_set_timer(t, tv);
}

/** Free a timeout. It is safe to call this function from an AvahiTimeoutCallback */
void avahi_timeout_free(AvahiTimeout* t) {
	//	eDebug("[Avahi] %s", __func__);
	t->timer->stop();
	delete t;
}


/* Connect the mainloop to avahi... */
void e2avahi_init(eMainloop* reactor) {
	avahi_poll_api.userdata = reactor;
	avahi_poll_api.watch_new = avahi_watch_new;
	avahi_poll_api.watch_update = avahi_watch_update;
	avahi_poll_api.watch_get_events = avahi_watch_get_events;
	avahi_poll_api.watch_free = avahi_watch_free;
	avahi_poll_api.timeout_new = avahi_timeout_new;
	avahi_poll_api.timeout_update = avahi_timeout_update;
	avahi_poll_api.timeout_free = avahi_timeout_free;

	avahi_client = avahi_client_new(&avahi_poll_api, AVAHI_CLIENT_NO_FAIL, avahi_client_callback, NULL, NULL);
}

void e2avahi_close() {
	if (avahi_client) {
		avahi_client_free(avahi_client);
		avahi_client = NULL;
		/* Remove all group entries */
		for (AvahiServiceEntryList::iterator it = avahi_services.begin(); it != avahi_services.end(); ++it) {
			it->group = NULL;
		}
		e2avahi_networkservicebrowser_clear_all();
	}
}


void e2avahi_set_debug(bool enable) {
	avahi_debug = enable;
}

void e2avahi_announce(const char* service_name, const char* service_type, unsigned short port_num) {
	avahi_services.push_back(AvahiServiceEntry(service_name, service_type, port_num));
	avahi_service_try_register(&avahi_services.back());
}

void e2avahi_resolve(const char* service_type, E2AvahiResolveCallback callback, void* userdata) {
	avahi_browsers.push_back(AvahiBrowserEntry(service_type, callback, userdata));
	avahi_browser_try_register(&avahi_browsers.back());
}

void e2avahi_resolve_cancel(const char* service_type, E2AvahiResolveCallback callback, void* userdata) {
	AvahiBrowserEntry entry(service_type, callback, userdata);
	AvahiBrowserEntryList::iterator it = std::find(avahi_browsers.begin(), avahi_browsers.end(), entry);
	if (it == avahi_browsers.end()) {
		avahiDebug("[Avahi] Cannot remove resolver for %s, not found", service_type);
		return;
	}
	if (it->browser) {
		avahi_service_browser_free(it->browser);
		it->browser = NULL;
	}
	avahi_browsers.erase(it);
}


/* eNetworkServiceBrowser ---------------------------------------------- */

DEFINE_REF(eNetworkServiceBrowser);

eNetworkServiceBrowser::eNetworkServiceBrowser() : m_started(false), m_failed(false), m_backoffMs(0) {
	m_restartTimer = eTimer::create(eApp);
	CONNECT(m_restartTimer->timeout, eNetworkServiceBrowser::restartTimeout);
}

eNetworkServiceBrowser::~eNetworkServiceBrowser() {
	stop();
}

void eNetworkServiceBrowser::addServiceType(const char* serviceType) {
	if (!serviceType || !*serviceType)
		return;
	for (std::vector<std::string>::iterator it = m_serviceTypes.begin(); it != m_serviceTypes.end(); ++it) {
		if (*it == serviceType)
			return; /* already added */
	}
	m_serviceTypes.push_back(serviceType);
	if (m_started)
		tryRegister(serviceType);
}

void eNetworkServiceBrowser::start() {
	if (m_started)
		return;
	m_started = true;
	networkservice_browsers.push_back(this);
	for (std::vector<std::string>::iterator it = m_serviceTypes.begin(); it != m_serviceTypes.end(); ++it) {
		tryRegister(*it);
	}
}

void eNetworkServiceBrowser::stop() {
	if (!m_started)
		return;
	m_restartTimer->stop();
	for (std::map<std::string, AvahiServiceBrowser*>::iterator it = m_browsers.begin(); it != m_browsers.end(); ++it) {
		if (it->second)
			avahi_service_browser_free(it->second);
	}
	m_browsers.clear();
	m_instances.clear();
	m_allForNow.clear();
	m_failed = false;
	m_backoffMs = 0;
	networkservice_browsers.remove(this);
	m_started = false;
}

void eNetworkServiceBrowser::tryRegister(const std::string& serviceType) {
	if (m_browsers.count(serviceType) && m_browsers[serviceType])
		return; /* already registered */

	if ((!avahi_client) || (avahi_client_get_state(avahi_client) != AVAHI_CLIENT_S_RUNNING)) {
		avahiDebug("[eNetworkServiceBrowser] Not running yet, cannot browse for type %s.", serviceType.c_str());
		return; /* retried from e2avahi_networkservicebrowser_try_register_all() once running */
	}

	AvahiServiceBrowser* browser = avahi_service_browser_new(avahi_client, AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC, serviceType.c_str(), NULL, (AvahiLookupFlags)0, avahiBrowserCallback, this);
	if (!browser) {
		avahiDebug("[eNetworkServiceBrowser] avahi_service_browser_new failed for %s: %s", serviceType.c_str(), avahi_strerror(avahi_client_errno(avahi_client)));
		return;
	}
	m_browsers[serviceType] = browser;
	m_backoffMs = 0; /* successful (re)registration resets the FAILURE backoff */
}

void eNetworkServiceBrowser::scheduleRestart() {
	if (m_backoffMs < 1000)
		m_backoffMs = 1000;
	else if (m_backoffMs < 30000)
		m_backoffMs *= 2;
	m_restartTimer->start(m_backoffMs, true);
}

void eNetworkServiceBrowser::restartTimeout() {
	for (std::vector<std::string>::iterator it = m_serviceTypes.begin(); it != m_serviceTypes.end(); ++it) {
		tryRegister(*it);
	}
}

eNetworkServiceBrowser::InstanceKey eNetworkServiceBrowser::makeKey(int interfaceIndex, int protocol, const char* name, const char* type, const char* domain) {
	/* interfaceIndex+protocol+name+type+domain uniquely identifies one
	 * service instance (see doc section 4.16) - the name alone is not enough,
	 * e.g. the same NAS can show up once per interface. */
	char buf[512];
	snprintf(buf, sizeof(buf), "%d:%d:%s:%s:%s", interfaceIndex, protocol, name ? name : "", type ? type : "", domain ? domain : "");
	return std::string(buf);
}

void eNetworkServiceBrowser::avahiBrowserCallback(AvahiServiceBrowser* browser, AvahiIfIndex iface, AvahiProtocol proto, AvahiBrowserEvent event, const char* name, const char* type,
												  const char* domain, AvahiLookupResultFlags flags, void* userdata) {
	((eNetworkServiceBrowser*)userdata)->handleBrowserEvent(browser, (int)iface, (int)proto, event, name, type, domain, flags);
}

void eNetworkServiceBrowser::avahiResolverCallback(AvahiServiceResolver* resolver, AvahiIfIndex iface, AvahiProtocol proto, AvahiResolverEvent event, const char* name, const char* type,
												   const char* domain, const char* hostName, const AvahiAddress* address, uint16_t port, AvahiStringList* txt, AvahiLookupResultFlags flags,
												   void* userdata) {
	((eNetworkServiceBrowser*)userdata)->handleResolverEvent((int)iface, (int)proto, event, name, type, domain, hostName, address, port, txt, flags);
	avahi_service_resolver_free(resolver);
}

/* True if interfaceIndex is the loopback interface (typically "lo"). Services
 * this box announces via its own avahi client are visible to the browser
 * again over loopback, on top of the announcement's real interface(s) -
 * that's pure local noise callers never want, so it's dropped before even
 * starting a resolver for it. */
static bool isLoopbackInterfaceIndex(int interfaceIndex) {
	char ifName[IF_NAMESIZE];
	if (!if_indextoname((unsigned int)interfaceIndex, ifName))
		return false;
	struct ifaddrs* ifaddr = NULL;
	if (getifaddrs(&ifaddr) != 0)
		return false;
	bool isLoopback = false;
	for (struct ifaddrs* ifa = ifaddr; ifa; ifa = ifa->ifa_next) {
		if (ifa->ifa_name && strcmp(ifa->ifa_name, ifName) == 0 && (ifa->ifa_flags & IFF_LOOPBACK)) {
			isLoopback = true;
			break;
		}
	}
	freeifaddrs(ifaddr);
	return isLoopback;
}

void eNetworkServiceBrowser::handleBrowserEvent(AvahiServiceBrowser* browser, int interfaceIndex, int protocol, AvahiBrowserEvent event, const char* name, const char* type, const char* domain,
												AvahiLookupResultFlags flags) {
	switch (event) {
		case AVAHI_BROWSER_NEW:
			if (isLoopbackInterfaceIndex(interfaceIndex)) {
				avahiDebug("[eNetworkServiceBrowser] Ignoring '%s' of type '%s' on loopback ifindex=%d", name, type, interfaceIndex);
				break;
			}
			avahiDebug("[eNetworkServiceBrowser] Resolving '%s' of type '%s' on ifindex=%d proto=%s", name, type, interfaceIndex, protocol == AVAHI_PROTO_INET6 ? "inet6" : "inet");
			avahi_service_resolver_new(avahi_client, (AvahiIfIndex)interfaceIndex, (AvahiProtocol)protocol, name, type, domain, AVAHI_PROTO_UNSPEC, (AvahiLookupFlags)0, avahiResolverCallback, this);
			break;
		case AVAHI_BROWSER_REMOVE: {
			avahiDebug("[eNetworkServiceBrowser] REMOVE '%s' of type '%s' in domain '%s'", name, type, domain);
			InstanceKey key = makeKey(interfaceIndex, protocol, name, type, domain);
			m_instances.erase(key);
			changed();
			break;
		}
		case AVAHI_BROWSER_ALL_FOR_NOW:
			m_allForNow[type] = true;
			changed();
			break;
		case AVAHI_BROWSER_FAILURE: {
			eWarning("[eNetworkServiceBrowser] browser failure for type '%s': %s", type, avahi_strerror(avahi_client_errno(avahi_service_browser_get_client(browser))));
			/* Don't call avahi_service_browser_free() here - same as the existing
			 * avahi_browser_callback() above, which also just drops the reference
			 * on AVAHI_BROWSER_FAILURE instead of freeing it. */
			m_browsers.erase(type);
			m_failed = true;
			scheduleRestart();
			changed();
			break;
		}
		case AVAHI_BROWSER_CACHE_EXHAUSTED:
			break;
	}
}

/* True if hostName's leading label matches this box's own avahi hostname
 * (e.g. "dm900.local" against "dm900"). A resolved service reporting our
 * own hostname for a foreign address is bogus - typically a stale
 * avahi-daemon cache entry left over from when this box itself held that
 * address (e.g. before a DHCP lease change) - not a real remote host name. */
static bool isOwnAvahiHostname(const char* hostName) {
	if (!hostName || !avahi_client)
		return false;
	const char* ownName = avahi_client_get_host_name(avahi_client);
	if (!ownName || !*ownName)
		return false;
	size_t ownLen = strlen(ownName);
	return strncasecmp(hostName, ownName, ownLen) == 0 && (hostName[ownLen] == '\0' || hostName[ownLen] == '.');
}

/* True if addrStr (as produced by avahi_address_snprint()) belongs to one of
 * this box's own, non-loopback interfaces. AVAHI_LOOKUP_RESULT_OUR_OWN above
 * only catches services this box itself actively publishes via this same
 * avahi client - it does not catch a resolver hit that happens to resolve to
 * our own address for other reasons (e.g. a stale/replayed record), so this
 * is a second, address-based check on top of it. */
static bool isOwnAddress(const char* addrStr) {
	if (!addrStr || !*addrStr)
		return false;
	struct ifaddrs* ifaddr = NULL;
	if (getifaddrs(&ifaddr) != 0)
		return false;
	bool isOwn = false;
	for (struct ifaddrs* ifa = ifaddr; ifa; ifa = ifa->ifa_next) {
		if (!ifa->ifa_addr || (ifa->ifa_flags & IFF_LOOPBACK))
			continue;
		if (ifa->ifa_addr->sa_family != AF_INET && ifa->ifa_addr->sa_family != AF_INET6)
			continue;
		char ifAddrStr[INET6_ADDRSTRLEN];
		const void* addrPtr = ifa->ifa_addr->sa_family == AF_INET ? (const void*)&((struct sockaddr_in*)ifa->ifa_addr)->sin_addr : (const void*)&((struct sockaddr_in6*)ifa->ifa_addr)->sin6_addr;
		if (inet_ntop(ifa->ifa_addr->sa_family, addrPtr, ifAddrStr, sizeof(ifAddrStr)) && strcmp(ifAddrStr, addrStr) == 0) {
			isOwn = true;
			break;
		}
	}
	freeifaddrs(ifaddr);
	return isOwn;
}

void eNetworkServiceBrowser::handleResolverEvent(int interfaceIndex, int protocol, AvahiResolverEvent event, const char* name, const char* type, const char* domain, const char* hostName,
												 const AvahiAddress* address, unsigned short port, AvahiStringList* txt, AvahiLookupResultFlags flags) {
	if (event != AVAHI_RESOLVER_FOUND) {
		avahiDebug("[eNetworkServiceBrowser] Failed to resolve '%s' of type '%s' on ifindex=%d proto=%s: %s", name, type, interfaceIndex, protocol == AVAHI_PROTO_INET6 ? "inet6" : "inet",
				   avahi_strerror(avahi_client_errno(avahi_client)));
		return;
	}
	if (flags & (AVAHI_LOOKUP_RESULT_LOCAL | AVAHI_LOOKUP_RESULT_OUR_OWN))
		return; /* skip our own announced services, same as the existing e2avahi_resolve() path */

	if (address) {
		char ownCheckBuf[AVAHI_ADDRESS_STR_MAX];
		if (avahi_address_snprint(ownCheckBuf, sizeof(ownCheckBuf), address) && isOwnAddress(ownCheckBuf)) {
			avahiDebug("[eNetworkServiceBrowser] '%s' of type '%s' resolved to our own address %s - skipping", name, type, ownCheckBuf);
			return;
		}
	}

	avahiDebug("[eNetworkServiceBrowser] ADD '%s' of type '%s' at %s:%u", name, type, hostName, port);

	bool bogusHostname = isOwnAvahiHostname(hostName);
	if (bogusHostname)
		avahiDebug("[eNetworkServiceBrowser] '%s' resolved to our own hostname '%s' for a different address - ignoring hostname, keeping the address/shares", name, hostName);

	Instance inst;
	inst.interfaceIndex = interfaceIndex;
	inst.protocol = protocol;
	inst.serviceName = name ? name : "";
	inst.serviceType = type ? type : "";
	inst.domain = domain ? domain : "";
	inst.hostname = (hostName && !bogusHostname) ? hostName : "";
	inst.port = port;

	if (address) {
		char addrbuf[AVAHI_ADDRESS_STR_MAX];
		if (avahi_address_snprint(addrbuf, sizeof(addrbuf), address))
			inst.addresses.push_back(addrbuf);
	}

	for (AvahiStringList* l = txt; l; l = avahi_string_list_get_next(l)) {
		char *key = NULL, *value = NULL;
		size_t valueSize = 0;
		if (avahi_string_list_get_pair(l, &key, &value, &valueSize) == 0) {
			inst.txt.push_back(std::make_pair(std::string(key ? key : ""), value ? std::string(value, valueSize) : std::string()));
		}
		avahi_free(key);
		avahi_free(value);
	}

	InstanceKey key = makeKey(interfaceIndex, protocol, name, type, domain);
	m_instances[key] = inst;
	changed();
}

PyObject* eNetworkServiceBrowser::getServices() {
	ePyObject ret = PyList_New(m_instances.size());
	int idx = 0;
	for (std::map<InstanceKey, Instance>::iterator it = m_instances.begin(); it != m_instances.end(); ++it, ++idx) {
		Instance& s = it->second;

		PyObject* addrs = PyList_New(s.addresses.size());
		for (size_t i = 0; i < s.addresses.size(); i++)
			PyList_SET_ITEM(addrs, i, PyUnicode_FromString(s.addresses[i].c_str()));

		PyObject* txt = PyDict_New();
		for (size_t i = 0; i < s.txt.size(); i++) {
			PyObject* value = PyUnicode_FromString(s.txt[i].second.c_str());
			PyDict_SetItemString(txt, s.txt[i].first.c_str(), value);
			Py_DECREF(value);
		}

		PyObject* d = PyDict_New();
		PyObject* name = PyUnicode_FromString(s.serviceName.c_str());
		PyObject* stype = PyUnicode_FromString(s.serviceType.c_str());
		PyObject* domain = PyUnicode_FromString(s.domain.c_str());
		PyObject* hostname = PyUnicode_FromString(s.hostname.c_str());
		PyObject* port = PyLong_FromLong(s.port);
		PyObject* iface = PyLong_FromLong(s.interfaceIndex);
		PyObject* proto = PyUnicode_FromString(s.protocol == AVAHI_PROTO_INET6 ? "inet6" : "inet");
		PyDict_SetItemString(d, "name", name);
		PyDict_SetItemString(d, "type", stype);
		PyDict_SetItemString(d, "domain", domain);
		PyDict_SetItemString(d, "hostname", hostname);
		PyDict_SetItemString(d, "addresses", addrs);
		PyDict_SetItemString(d, "port", port);
		PyDict_SetItemString(d, "interface", iface);
		PyDict_SetItemString(d, "protocol", proto);
		PyDict_SetItemString(d, "txt", txt);
		Py_DECREF(name);
		Py_DECREF(stype);
		Py_DECREF(domain);
		Py_DECREF(hostname);
		Py_DECREF(port);
		Py_DECREF(iface);
		Py_DECREF(proto);
		Py_DECREF(addrs);
		Py_DECREF(txt);

		PyList_SET_ITEM(ret, idx, d);
	}
	return ret;
}
