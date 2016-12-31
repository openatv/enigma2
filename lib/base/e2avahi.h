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

