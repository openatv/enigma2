#include "servicepeer.h"

#include <lib/base/e2avahi.h>
#include <lib/base/eerror.h>
#include <string>
#include <map>
#include <sstream>

static const char* service_type = "_e2stream._tcp";
typedef std::map<std::string, std::string> PeerMapping;
static PeerMapping peers;

static void peer_register(const char *name,	const char *host_name, uint16_t port)
{
	eWarning("ADD Peer %s=%s:%u", name, host_name, port);
	std::ostringstream url;
	url << "http://" << host_name << ":" << port;
	peers[std::string(name)] = url.str();
}

static void peer_remove(const char *name)
{
	eWarning("REMOVE Peer %s", name);
	PeerMapping::iterator it = peers.find(std::string(name));
	if (it != peers.end())
		peers.erase(it);
}

static void e2avahi_resolve_callback(
    void* userdata,
	int event, /* One of E2AVAHI_EVENT_... */
	const char *name, /* name+type combination is unique on the network */
	const char *type,
	const char *host_name, /* hostname and port are only valid in ADD */
	uint16_t port)
{
	switch (event)
	{
		case E2AVAHI_EVENT_ADD:
			peer_register(name, host_name, port);
			break;
		case E2AVAHI_EVENT_REMOVE:
			peer_remove(name);
			break;
	}
}

void init_servicepeer()
{
	e2avahi_resolve(service_type, e2avahi_resolve_callback, &peers);
}

void done_servicepeer()
{
	e2avahi_resolve_cancel(service_type, e2avahi_resolve_callback, &peers);
}

PyObject *getPeerStreamingBoxes()
{
	ePyObject ret = PyList_New(peers.size());
	int idx = 0;
	for (PeerMapping::iterator it = peers.begin(); it != peers.end(); ++it)
	{
		PyList_SET_ITEM(ret, idx++, PyString_FromString((char *)it->second.c_str()));
	}
	return ret;
}
