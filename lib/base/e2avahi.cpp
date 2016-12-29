#include "e2avahi.h"
#include "ebase.h"
#include <avahi-common/error.h>
#include <avahi-client/client.h>
#include <avahi-client/publish.h>
#include <avahi-client/lookup.h>
#include <avahi-common/malloc.h>
#include <avahi-common/timeval.h>

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

static void avahi_client_callback(AvahiClient *client, AvahiClientState state, void *d)
{
	eDebug("[Avahi] client state: %d", state);
}

static void avahi_group_callback(AvahiEntryGroup *group,
		AvahiEntryGroupState state, void *d)
{
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


/* In future, this will connect the mainloop to avahi... */
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
	}
}

void e2avahi_announce(const char* service_name, const char* service_type, unsigned short port_num)
{
	AvahiEntryGroup *group;

	if ((!avahi_client) || (avahi_client_get_state(avahi_client) != AVAHI_CLIENT_S_RUNNING))
	{
		eDebug("[Avahi] Not running yet, cannot register.\n");
		return;
	}

	group = avahi_entry_group_new(avahi_client, avahi_group_callback, NULL);
	if (group && !avahi_entry_group_add_service(group,
			AVAHI_IF_UNSPEC, AVAHI_PROTO_UNSPEC,
			(AvahiPublishFlags)0, service_name, service_type,
			NULL, NULL, port_num, NULL))
	{
		avahi_entry_group_commit(group);
		eDebug("[Avahi] Registered %s (%s) on %s:%u\n",
			service_name, service_type, 
			avahi_client_get_host_name(avahi_client), port_num);
	}
	/* NOTE: group is freed by avahi_client_free */

	return;
}
