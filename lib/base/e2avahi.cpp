#include "e2avahi.h"
#include <avahi-common/simple-watch.h>
#include <avahi-common/error.h>
#include <avahi-client/client.h>
#include <avahi-client/publish.h>
#include <avahi-client/lookup.h>
#include <avahi-common/malloc.h>

/* For now, instantiate a poll that we'll never actually start. To
 * be replaced with the E2 mainloop */
static AvahiSimplePoll *avahi_poll = NULL;
/* Our link to avahi */
static AvahiClient *avahi_client = NULL;

static void avahi_client_callback(AvahiClient *client, AvahiClientState state, void *d)
{
	eDebug("[Avahi] client state: %d\n", state);
}

static void avahi_group_callback(AvahiEntryGroup *group,
		AvahiEntryGroupState state, void *d)
{
}

/* In future, this will connect the mainloop to avahi... */
void e2avahi_init(eMainloop* reactor)
{
	avahi_poll = avahi_simple_poll_new();
	if (!avahi_poll) {
		eDebug("avahi_simple_poll_new failed\n");
		return;
	}
	avahi_client = avahi_client_new(avahi_simple_poll_get(avahi_poll),
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
