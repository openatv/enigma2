#include "e2avahi.h"
#include "ebase.h"
#include <avahi-common/error.h>
#include <avahi-client/client.h>
#include <avahi-client/publish.h>
#include <avahi-client/lookup.h>
#include <avahi-common/malloc.h>
#include <avahi-common/timeval.h>
#include <list>

/* Our link to avahi */
static AvahiClient *avahi_client = NULL;

/* API to the E2 event loop */
static AvahiPoll avahi_poll_api;

struct AvahiTimeout: public Object
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

struct AvahiWatch: public Object
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
typedef std::list<AvahiServiceEntry> AvahiServiceEntryList;
static AvahiServiceEntryList avahi_services;

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
		eDebug("[Avahi] Not running yet, cannot register %s.\n", entry->service_name);
		return;
	}

	entry->group = avahi_entry_group_new(avahi_client, avahi_group_callback, NULL);
	if (!entry->group) {
		eDebug("[Avahi] avahi_entry_group_new failed, cannot register %s.\n", entry->service_name);
		return;
	}
		
	if (!avahi_entry_group_add_service(entry->group,
			AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC,
			(AvahiPublishFlags)0,
			entry->service_name, entry->service_type,
			NULL, NULL, entry->port_num, NULL))
	{
		avahi_entry_group_commit(entry->group);
		eDebug("[Avahi] Registered %s (%s) on %s:%u\n",
			entry->service_name, entry->service_type, 
			avahi_client_get_host_name(avahi_client), entry->port_num);
	}
	/* NOTE: group is freed by avahi_client_free */
}

static void avahi_service_try_register_all()
{
	for (AvahiServiceEntryList::iterator it = avahi_services.begin();
		it != avahi_services.end(); ++it)
	{
		avahi_service_try_register(&(*it));
	}
}

static void avahi_service_reset_all()
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
}

static void avahi_client_callback(AvahiClient *client, AvahiClientState state, void *d)
{
	eDebug("[Avahi] client state: %d", state);
	switch(state)
	{
		case AVAHI_CLIENT_S_RUNNING:
			/* The server has startup successfully and registered its host
			 * name on the network, register all our services */
			avahi_service_try_register_all();
			break;
        case AVAHI_CLIENT_FAILURE:
			/* Problem? Maybe we have to re-register everything? */
            eDebug("[Avahi] Client failure: %s\n", avahi_strerror(avahi_client_errno(client)));
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
            avahi_service_reset_all();
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
	AvahiServiceEntry entry(service_name, service_type, port_num);
	avahi_service_try_register(&entry);
	avahi_services.push_back(entry);
}
