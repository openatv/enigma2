#pragma once

#ifndef SWIG
class eMainloop;

/* Initialization and shutdown */
void e2avahi_init(eMainloop* reactor);
void e2avahi_close();
#endif

/* Offer a service. There's currently no way to withdraw it. Leave
 * service_name NULL or blank to use avahi's local hostname as service
 * name (recommended, since it must be unique on the network) */
void e2avahi_announce(const char* service_name, const char* service_type, unsigned short port_num);

#define E2AVAHI_EVENT_ADD 1
#define E2AVAHI_EVENT_REMOVE 2

typedef void (*E2AvahiResolveCallback) (
	void* userdata,
	int event, /* One of E2AVAHI_EVENT_... */
	const char *name, /* name+type combination is unique on the network */
	const char *type,
	const char *host_name, /* hostname and port are only valid in ADD */
	uint16_t port);

/* Starts searching for services on other machines. Basically, one expects
 * to activate this once, and then keep updating a static list of matches. */
void e2avahi_resolve(const char* service_type, E2AvahiResolveCallback callback, void *userdata);
/* Stop looking for services. Callback will no longer be triggered after this. Pass the same
 * data as to the call to e2avahi_resolve. */
void e2avahi_resolve_cancel(const char* service_type, E2AvahiResolveCallback callback, void *userdata);
