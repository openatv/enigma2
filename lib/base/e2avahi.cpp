#include "e2avahi.h"
#include "ebase.h"
#include <avahi-common/error.h>
#include <avahi-client/client.h>
#include <avahi-client/publish.h>
#include <avahi-client/lookup.h>
#include <avahi-common/malloc.h>
#include <avahi-common/timeval.h>
#include <list>
#include <algorithm>

/* Our link to avahi */
static AvahiClient *avahi_client = NULL;

/* API to the E2 event loop */
static AvahiPoll avahi_poll_api;

struct AvahiTimeout: public sigc::trackable
{
	ePtr<eTimer> timer;
	AvahiTimeoutCallback callback;
	void *userdata;

	void timeout()
	{
		eDebug("[Avahi] timeout elapsed");
		callback(this, userdata);
	}

	AvahiTimeout(eMainloop *mainloop, AvahiTimeoutCallback _callback, void *_userdata):
		timer(eTimer::create(mainloop)),
		callback(_callback),
		userdata(_userdata)
	{
		CONNECT(timer->timeout, AvahiTimeout::timeout);
	}
};

struct AvahiWatch: public sigc::trackable
{
	ePtr<eSocketNotifier> sn;
	AvahiWatchCallback callback;
	void *userdata;
	int lastEvent;

	void activated(int event)
	{
		eDebug("[Avahi] watch activated: %#x", event);
		lastEvent = event;
		callback(this, sn->getFD(), (AvahiWatchEvent)event, userdata);
	}

	AvahiWatch(eMainloop *mainloop, int fd, int req, AvahiWatchCallback cb, void *ud):
		sn(eSocketNotifier::create(mainloop, fd, req)),
		callback(cb),
		userdata(ud),
		lastEvent(0)
	{
		CONNECT(sn->activated, AvahiWatch::activated);
	}
};

struct AvahiServiceEntry
{
	AvahiEntryGroup *group;
	const char* service_name;
	const char* service_type;
	unsigned short port_num;

	AvahiServiceEntry(const char *n, const char *t, unsigned short p):
		group(NULL),
		service_name(n),
		service_type(t),
		port_num(p)
	{}
	AvahiServiceEntry():
		group(NULL)
	{}
};
inline bool operator==(const AvahiServiceEntry& lhs, const AvahiServiceEntry& rhs)
{
	return (lhs.service_type == rhs.service_type) &&
			(lhs.port_num == rhs.port_num); 
}
inline bool operator!=(const AvahiServiceEntry& lhs, const AvahiServiceEntry& rhs)
{ return !(lhs == rhs); }
typedef std::list<AvahiServiceEntry> AvahiServiceEntryList;
static AvahiServiceEntryList avahi_services;

struct AvahiBrowserEntry
{
	AvahiServiceBrowser *browser;
	const char* service_type;
	E2AvahiResolveCallback callback;
	void *userdata;

	AvahiBrowserEntry(): browser(NULL) {} /* For std:list */
	AvahiBrowserEntry(const char* t, E2AvahiResolveCallback cb, void *ud):
		browser(NULL), service_type(t), callback(cb), userdata(ud)
	{}
};
/* Implement equality operator to make "std::find" work */
inline bool operator==(const AvahiBrowserEntry& lhs, const AvahiBrowserEntry& rhs)
{
	return (lhs.service_type == rhs.service_type) &&
		(lhs.callback == rhs.callback) &&
		(lhs.userdata == rhs.userdata);
}
inline bool operator!=(const AvahiBrowserEntry& lhs, const AvahiBrowserEntry& rhs)
{ return !(lhs == rhs); }
typedef std::list<AvahiBrowserEntry> AvahiBrowserEntryList;
static AvahiBrowserEntryList avahi_browsers;

static void avahi_group_callback(AvahiEntryGroup *group,
		AvahiEntryGroupState state, void *d)
{
}

static void avahi_service_try_register(AvahiServiceEntry *entry)
{
	if (entry->group)
		return; /* Already registered */

	if ((!avahi_client) || (avahi_client_get_state(avahi_client) != AVAHI_CLIENT_S_RUNNING))
	{
		eDebug("[Avahi] Not running yet, cannot register type %s.\n", entry->service_type);
		return;
	}

	entry->group = avahi_entry_group_new(avahi_client, avahi_group_callback, NULL);
	if (!entry->group) {
		eDebug("[Avahi] avahi_entry_group_new failed, cannot register %s %s.\n", entry->service_type, entry->service_name);
		return;
	}

	const char *service_name = entry->service_name;
	/* Blank or NULL service name, use our host name as service name,
	 * this appears to be what other services do. */
	if ((!service_name) || (!*service_name))
		service_name = avahi_client_get_host_name(avahi_client);

	if (!avahi_entry_group_add_service(entry->group,
			AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC,
			(AvahiPublishFlags)0,
			service_name, entry->service_type,
			NULL, NULL, entry->port_num, NULL))
	{
		avahi_entry_group_commit(entry->group);
		eDebug("[Avahi] Registered %s (%s) on %s:%u\n",
			service_name, entry->service_type,
			avahi_client_get_host_name(avahi_client), entry->port_num);
	}
	/* NOTE: group is freed by avahi_client_free */
}


/* Browser part */

static void avahi_resolver_callback(AvahiServiceResolver *resolver,
		AvahiIfIndex iface, AvahiProtocol proto,
		AvahiResolverEvent event, const char *name,
		const char *type, const char *domain,
		const char *host_name, const AvahiAddress *address,
		uint16_t port, AvahiStringList *txt,
		AvahiLookupResultFlags flags, void *d)
{
	AvahiBrowserEntry *entry = (AvahiBrowserEntry*)d;

	switch (event) {
		case AVAHI_RESOLVER_FAILURE:
			eDebug("[Avahi] Failed to resolve service '%s' of type '%s': %s\n",
				name, type, avahi_strerror(avahi_client_errno(avahi_service_resolver_get_client(resolver))));
			break;
		case AVAHI_RESOLVER_FOUND:
			if (flags & (AVAHI_LOOKUP_RESULT_LOCAL | AVAHI_LOOKUP_RESULT_OUR_OWN))
				break; /* Skip local/own services, we don't want to see them */
			eDebug("[Avahi] ADD Service '%s' of type '%s' at %s:%u", name, type, host_name, port);
			entry->callback(entry->userdata, E2AVAHI_EVENT_ADD, name, type, host_name, port);
			break;
	}

	avahi_service_resolver_free(resolver);
}

static void avahi_browser_callback(AvahiServiceBrowser *browser,
		AvahiIfIndex iface, AvahiProtocol proto,
		AvahiBrowserEvent event, const char *name,
		const char *type, const char *domain,
		AvahiLookupResultFlags flags, void *d)
{
	AvahiBrowserEntry *entry = (AvahiBrowserEntry*)d;
	struct AvahiClient *client = avahi_service_browser_get_client(browser);

	switch (event) {
	case AVAHI_BROWSER_NEW:
		eDebug("[Avahi] Resolving service '%s' of type '%s'", name, type);
		avahi_service_resolver_new(client, iface,
				proto, name, type, domain,
				AVAHI_PROTO_UNSPEC, (AvahiLookupFlags)0,
				avahi_resolver_callback, d);
		break;
	case AVAHI_BROWSER_REMOVE:
		eDebug("[Avahi] REMOVE service '%s' of type '%s' in domain '%s'", name, type, domain);
		entry->callback(entry->userdata, E2AVAHI_EVENT_REMOVE, name, type, NULL, 0);
		break;
	case AVAHI_BROWSER_ALL_FOR_NOW:
		/* Useless information... */
		break;
	case AVAHI_BROWSER_FAILURE:
		eDebug("[Avahi] AVAHI_BROWSER_FAILURE");
		/* We'll probably need to restart everything? */
		entry->browser = NULL;
		break;
	case AVAHI_BROWSER_CACHE_EXHAUSTED:
		/* Useless information... */
		break;
	}
}

static void avahi_browser_try_register(AvahiBrowserEntry *entry)
{
	if (entry->browser)
		return; /* Already registered */

	if ((!avahi_client) || (avahi_client_get_state(avahi_client) != AVAHI_CLIENT_S_RUNNING))
	{
		eDebug("[Avahi] Not running yet, cannot browse for type %s.", entry->service_type);
		return;
	}

	entry->browser = avahi_service_browser_new(avahi_client,
			AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC,
			entry->service_type, NULL, (AvahiLookupFlags)0,
			avahi_browser_callback, entry);
	if (!entry->browser) {
		eDebug("[Avahi] avahi_service_browser_new failed: %s\n",
				avahi_strerror(avahi_client_errno(avahi_client)));
	}
}

static void avahi_client_try_register_all()
{
	for (AvahiServiceEntryList::iterator it = avahi_services.begin();
		it != avahi_services.end(); ++it)
	{
		avahi_service_try_register(&(*it));
	}
	for (AvahiBrowserEntryList::iterator it = avahi_browsers.begin();
		it != avahi_browsers.end(); ++it)
	{
		avahi_browser_try_register(&(*it));
	}
}

static void avahi_client_reset_all()
{
	for (AvahiServiceEntryList::iterator it = avahi_services.begin();
		it != avahi_services.end(); ++it)
	{
		if (it->group)
		{
			avahi_entry_group_free(it->group);
			it->group = NULL;
		}
	}
	for (AvahiBrowserEntryList::iterator it = avahi_browsers.begin();
		it != avahi_browsers.end(); ++it)
	{
		if (it->browser)
		{
			avahi_service_browser_free(it->browser);
			it->browser = NULL;
		}
	}
}

static void avahi_client_callback(AvahiClient *client, AvahiClientState state, void *d)
{
	eDebug("[Avahi] client state: %d", state);
	switch(state)
	{
		case AVAHI_CLIENT_S_RUNNING:
			/* The server has startup successfully and registered its host
			 * name on the network, register all our services */
			avahi_client_try_register_all();
			break;
		case AVAHI_CLIENT_FAILURE:
			/* Problem? Maybe we have to re-register everything? */
			eWarning("[Avahi] Client failure: %s\n", avahi_strerror(avahi_client_errno(client)));
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
static AvahiWatch* avahi_watch_new(const AvahiPoll *api, int fd, AvahiWatchEvent event, AvahiWatchCallback callback, void *userdata)
{
	eDebug("[Avahi] %s(%d %#x)", __func__, fd, event);

	return new AvahiWatch((eMainloop*)api->userdata, fd, event, callback, userdata);
}


/** Update the events to wait for. It is safe to call this function from an AvahiWatchCallback */
static void avahi_watch_update(AvahiWatch *w, AvahiWatchEvent event)
{
	eDebug("[Avahi] %s(%#x)", __func__, event);
	w->sn->setRequested(event);
}

/** Return the events that happened. It is safe to call this function from an AvahiWatchCallback  */
AvahiWatchEvent avahi_watch_get_events(AvahiWatch *w)
{
	eDebug("[Avahi] %s", __func__);
	return (AvahiWatchEvent)w->lastEvent;
}

/** Free a watch. It is safe to call this function from an AvahiWatchCallback */
void avahi_watch_free(AvahiWatch *w)
{
	eDebug("[Avahi] %s", __func__);
	delete w;
}

static void avahi_set_timer(AvahiTimeout *t, const struct timeval *tv)
{
	if (tv)
	{
		/*struct timeval now;
		gettimeofday(&now, NULL);*/
		AvahiUsec usec = (- avahi_age(tv));
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
AvahiTimeout* avahi_timeout_new(const AvahiPoll *api, const struct timeval *tv, AvahiTimeoutCallback callback, void *userdata)
{
	eDebug("[Avahi] %s", __func__);

	AvahiTimeout* result = new AvahiTimeout((eMainloop*)api->userdata, callback, userdata);
	avahi_set_timer(result, tv);

	return result;
}

/** Update the absolute expiration time for a timeout, If tv is
 * NULL, the timeout is disabled. It is safe to call this function from an AvahiTimeoutCallback */
void avahi_timeout_update(AvahiTimeout *t, const struct timeval *tv)
{
	eDebug("[Avahi] %s\n", __func__);
	t->timer->stop();
	avahi_set_timer(t, tv);
}

/** Free a timeout. It is safe to call this function from an AvahiTimeoutCallback */
void avahi_timeout_free(AvahiTimeout *t)
{
	eDebug("[Avahi] %s\n", __func__);
	t->timer->stop();
	delete t;
}


/* Connect the mainloop to avahi... */
void e2avahi_init(eMainloop* reactor)
{
	avahi_poll_api.userdata = reactor;
	avahi_poll_api.watch_new = avahi_watch_new;
	avahi_poll_api.watch_update = avahi_watch_update;
	avahi_poll_api.watch_get_events = avahi_watch_get_events;
	avahi_poll_api.watch_free = avahi_watch_free;
	avahi_poll_api.timeout_new = avahi_timeout_new;
	avahi_poll_api.timeout_update = avahi_timeout_update;
	avahi_poll_api.timeout_free = avahi_timeout_free;

	avahi_client = avahi_client_new(&avahi_poll_api,
		AVAHI_CLIENT_NO_FAIL, avahi_client_callback, NULL, NULL);
}

void e2avahi_close()
{
	if (avahi_client)
	{
		avahi_client_free(avahi_client);
		avahi_client = NULL;
		/* Remove all group entries */
		for (AvahiServiceEntryList::iterator it = avahi_services.begin();
			it != avahi_services.end(); ++it)
		{
			it->group = NULL;
		}
	}
}


void e2avahi_announce(const char* service_name, const char* service_type, unsigned short port_num)
{
	avahi_services.push_back(AvahiServiceEntry(service_name, service_type, port_num));
	avahi_service_try_register(&avahi_services.back());
}

void e2avahi_resolve(const char* service_type, E2AvahiResolveCallback callback, void *userdata)
{
	avahi_browsers.push_back(AvahiBrowserEntry(service_type, callback, userdata));
	avahi_browser_try_register(&avahi_browsers.back());
}

void e2avahi_resolve_cancel(const char* service_type, E2AvahiResolveCallback callback, void *userdata)
{
	AvahiBrowserEntry entry(service_type, callback, userdata);
	AvahiBrowserEntryList::iterator it = std::find(avahi_browsers.begin(), avahi_browsers.end(), entry);
	if (it == avahi_browsers.end()) {
		eWarning("[Avahi] Cannot remove resolver for %s, not found", service_type);
		return;
	}
	if (it->browser)
	{
		avahi_service_browser_free(it->browser);
		it->browser = NULL;
	}
	avahi_browsers.erase(it);
}
