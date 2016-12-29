#pragma once

#include "ebase.h"

/* Initialization and shutdown */
void e2avahi_init(eMainloop* reactor);
void e2avahi_close();

/* Offer a service. There's currently no way to withdraw it. */
void e2avahi_announce(const char* service_name, const char* service_type, unsigned short port_num);

