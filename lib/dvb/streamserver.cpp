#include <algorithm>
#include <stdio.h>
#include <sys/select.h>
#include <unistd.h>
#include <string.h>
#include <sys/types.h>
#include <pwd.h>
#include <shadow.h>
#include <crypt.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <gio/gio.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/wrappers.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/cfile.h>
#include <lib/base/e2avahi.h>
#include <lib/base/message.h>
#include <lib/nav/core.h>

#include <lib/dvb/streamserver.h>
#include <lib/dvb/encoder.h>
#include <lib/python/python_helpers.h>

enum eStreamServerDBusEventType
{
	streamserver_event_availability_changed,
	streamserver_event_source_state_changed,
	streamserver_event_upstream_state_changed,
	streamserver_event_upstream_bitrate_changed,
	streamserver_event_rtsp_client_count_changed,
	streamserver_event_hls_client_count_changed,
	streamserver_event_rtsp_state_changed,
	streamserver_event_hls_state_changed,
	streamserver_event_uri_parameters_changed,
	streamserver_event_dbus_error,
	streamserver_event_ping
};

struct eStreamServerDBusEvent
{
	eStreamServerDBusEventType type;
	int value;
	std::string text;

	eStreamServerDBusEvent()
		: type(streamserver_event_ping), value(0)
	{
	}

	eStreamServerDBusEvent(eStreamServerDBusEventType type, int value, const std::string &text)
		: type(type), value(value), text(text)
	{
	}
};

struct eStreamServerDBusBackend
{
	const char *name;
	const char *path;
	const char *interface;
};

static const eStreamServerDBusBackend live555_backend = {
	"org.enigma2.Live555",
	"/org/enigma2/Live555",
	"org.enigma2.Live555"
};

static const char *classic_encoder_lock_file = "/tmp/enigma2-classic-transcoding.lock";

static bool isLocalStreamHost(const std::string &remotehost)
{
	return remotehost == "::1" ||
		remotehost == "127.0.0.1" ||
		remotehost.find("127.0.0.1") != std::string::npos ||
		remotehost.find("::ffff:127.") != std::string::npos;
}

struct eStreamServerDBus: public sigc::trackable
{
	eStreamServer *owner;
	GDBusConnection *connection;
	GDBusConnection *signal_connection;
	GMainContext *signal_context;
	GMainLoop *signal_loop;
	GThread *signal_thread;
	guint name_watch_id;
	const eStreamServerDBusBackend *backend;
	gint stopping;
	bool available;
	std::string rtsp_user;
	std::string rtsp_pass;
	std::string rtsp_path;
	std::string hls_user;
	std::string hls_pass;
	std::string hls_path;
	eFixedMessagePump<eStreamServerDBusEvent> event_pump;

	eStreamServerDBus(eStreamServer *owner)
		: owner(owner), connection(NULL), signal_connection(NULL), signal_context(NULL), signal_loop(NULL), signal_thread(NULL),
		  name_watch_id(0), backend(NULL), stopping(0), available(false), rtsp_path("stream"), hls_path("stream"), event_pump(eApp, 0)
	{
		CONNECT(event_pump.recv_msg, eStreamServerDBus::handleEvent);
		signal_thread = g_thread_new("estreamserver-dbus", signalThread, this);
	}

	~eStreamServerDBus()
	{
		g_atomic_int_set(&stopping, 1);
		if (signal_loop)
			g_main_loop_quit(signal_loop);
		if (signal_thread)
			g_thread_join(signal_thread);
		if (connection)
			g_object_unref(connection);
	}

	static gpointer signalThread(gpointer user_data)
	{
		eStreamServerDBus *self = static_cast<eStreamServerDBus*>(user_data);
		GError *error = NULL;
		self->signal_context = g_main_context_new();
		g_main_context_push_thread_default(self->signal_context);
		self->signal_connection = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &error);
		if (!self->signal_connection)
		{
			self->sendError("DBus signal connection failed", error);
			if (error)
				g_error_free(error);
			g_main_context_pop_thread_default(self->signal_context);
			g_main_context_unref(self->signal_context);
			self->signal_context = NULL;
			return NULL;
		}
		self->subscribeSignals(&live555_backend);
		self->watchName(&live555_backend);
		self->signal_loop = g_main_loop_new(self->signal_context, FALSE);
		if (!g_atomic_int_get(&self->stopping))
			g_main_loop_run(self->signal_loop);
		if (self->name_watch_id)
		{
			g_bus_unwatch_name(self->name_watch_id);
			self->name_watch_id = 0;
		}
		g_main_loop_unref(self->signal_loop);
		self->signal_loop = NULL;
		g_object_unref(self->signal_connection);
		self->signal_connection = NULL;
		g_main_context_pop_thread_default(self->signal_context);
		g_main_context_unref(self->signal_context);
		self->signal_context = NULL;
		return NULL;
	}

	void subscribeSignals(const eStreamServerDBusBackend *signal_backend)
	{
		g_dbus_connection_signal_subscribe(signal_connection, signal_backend->name, signal_backend->interface,
			NULL, signal_backend->path, NULL, G_DBUS_SIGNAL_FLAGS_NONE, onSignal, this, NULL);
	}

	void watchName(const eStreamServerDBusBackend *signal_backend)
	{
		name_watch_id = g_bus_watch_name_on_connection(signal_connection, signal_backend->name,
			G_BUS_NAME_WATCHER_FLAGS_NONE, onNameAppeared, onNameVanished, this, NULL);
	}

	static void onNameAppeared(GDBusConnection * /*connection*/, const gchar *name, const gchar *name_owner, gpointer user_data)
	{
		eStreamServerDBus *self = static_cast<eStreamServerDBus*>(user_data);
		if (g_atomic_int_get(&self->stopping))
			return;
		self->backend = &live555_backend;
		self->setAvailable(true);
		eDebug("[eStreamServer] DBus backend %s appeared%s%s", name, name_owner ? " as " : "", name_owner ? name_owner : "");
	}

	static void onNameVanished(GDBusConnection * /*connection*/, const gchar *name, gpointer user_data)
	{
		eStreamServerDBus *self = static_cast<eStreamServerDBus*>(user_data);
		if (g_atomic_int_get(&self->stopping))
			return;
		if (!strcmp(name, live555_backend.name))
			self->backend = NULL;
		self->setAvailable(false);
		eDebug("[eStreamServer] DBus backend %s vanished", name);
	}

	static int variantToInt(GVariant *value, int default_value)
	{
		if (!value)
			return default_value;
		if (g_variant_is_of_type(value, G_VARIANT_TYPE_INT32))
			return g_variant_get_int32(value);
		if (g_variant_is_of_type(value, G_VARIANT_TYPE_UINT32))
			return (int)g_variant_get_uint32(value);
		if (g_variant_is_of_type(value, G_VARIANT_TYPE_BOOLEAN))
			return g_variant_get_boolean(value) ? 1 : 0;
		return default_value;
	}

	static std::string variantToString(GVariant *value, const std::string &default_value)
	{
		if (!value || !g_variant_is_of_type(value, G_VARIANT_TYPE_STRING))
			return default_value;
		return std::string(g_variant_get_string(value, NULL));
	}

	static int firstInt(GVariant *parameters)
	{
		GVariant *child = parameters && g_variant_n_children(parameters) > 0 ? g_variant_get_child_value(parameters, 0) : NULL;
		int value = variantToInt(child, 0);
		if (child)
			g_variant_unref(child);
		return value;
	}

	static std::string childString(GVariant *parameters, gsize index)
	{
		GVariant *child = parameters && g_variant_n_children(parameters) > index ? g_variant_get_child_value(parameters, index) : NULL;
		std::string value = variantToString(child, "");
		if (child)
			g_variant_unref(child);
		return value;
	}

	static void onSignal(GDBusConnection *connection, const gchar *sender_name, const gchar *object_path,
		const gchar *interface_name, const gchar *signal_name, GVariant *parameters, gpointer user_data)
	{
		eStreamServerDBus *self = static_cast<eStreamServerDBus*>(user_data);
		if (!strcmp(signal_name, "ping"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_ping, 0, ""));
		else if (!strcmp(signal_name, "sourceStateChanged"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_source_state_changed, firstInt(parameters), ""));
		else if (!strcmp(signal_name, "upstreamStateChanged"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_upstream_state_changed, firstInt(parameters), ""));
		else if (!strcmp(signal_name, "tcpBitrate"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_upstream_bitrate_changed, firstInt(parameters), ""));
		else if (!strcmp(signal_name, "rtspStateChanged"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_rtsp_state_changed, firstInt(parameters), ""));
		else if (!strcmp(signal_name, "hlsStateChanged"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_hls_state_changed, firstInt(parameters), ""));
		else if (!strcmp(signal_name, "rtspClientCountChanged"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_rtsp_client_count_changed, firstInt(parameters), childString(parameters, 1)));
		else if (!strcmp(signal_name, "hlsClientCountChanged"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_hls_client_count_changed, firstInt(parameters), childString(parameters, 1)));
		else if (!strcmp(signal_name, "uriParametersChanged"))
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_uri_parameters_changed, 0, childString(parameters, 0)));
		else if (!strcmp(signal_name, "encoderError"))
		{
			std::string message = childString(parameters, 0);
			self->event_pump.send(eStreamServerDBusEvent(streamserver_event_dbus_error, 0, message.empty() ? "Encoder error" : message));
		}
	}

	void handleEvent(const eStreamServerDBusEvent &event)
	{
		switch (event.type)
		{
		case streamserver_event_availability_changed:
			if (!event.value)
				owner->clearLive555Clients();
			owner->availabilityChanged(event.value);
			break;
		case streamserver_event_source_state_changed:
			owner->sourceStateChanged(event.value);
			break;
		case streamserver_event_upstream_state_changed:
			owner->upstreamStateChanged(event.value);
			break;
		case streamserver_event_upstream_bitrate_changed:
			owner->upstreamBitrateChanged(event.value);
			break;
		case streamserver_event_rtsp_client_count_changed:
			owner->updateLive555ClientCount("rtsp", event.value, event.text);
			owner->rtspClientCountChanged(event.value, event.text.c_str());
			break;
		case streamserver_event_hls_client_count_changed:
			owner->updateLive555ClientCount("hls", event.value, event.text);
			owner->hlsClientCountChanged(event.value, event.text.c_str());
			break;
		case streamserver_event_rtsp_state_changed:
			owner->rtspStateChanged(event.value);
			break;
		case streamserver_event_hls_state_changed:
			owner->hlsStateChanged(event.value);
			break;
		case streamserver_event_uri_parameters_changed:
			owner->uriParametersChanged(event.text.c_str());
			break;
		case streamserver_event_dbus_error:
			owner->dbusError(event.text.c_str());
			break;
		case streamserver_event_ping:
			owner->ping();
			break;
		}
	}

	void setAvailable(bool value)
	{
		if (available != value)
		{
			available = value;
			event_pump.send(eStreamServerDBusEvent(streamserver_event_availability_changed, value ? 1 : 0, ""));
		}
	}

	void sendError(const char *prefix, GError *error)
	{
		std::string message(prefix ? prefix : "DBus error");
		if (error && error->message)
		{
			message += ": ";
			message += error->message;
		}
		event_pump.send(eStreamServerDBusEvent(streamserver_event_dbus_error, 0, message));
	}

	bool ensureConnection()
	{
		if (connection)
			return true;
		GError *error = NULL;
		connection = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &error);
		if (!connection)
		{
			sendError("DBus connection failed", error);
			if (error)
				g_error_free(error);
			setAvailable(false);
			return false;
		}
		return true;
	}

	GVariant *getPropertyOn(const eStreamServerDBusBackend *candidate, const char *property, bool report_error)
	{
		if (!ensureConnection())
			return NULL;
		GError *error = NULL;
		GVariant *reply = g_dbus_connection_call_sync(connection, candidate->name, candidate->path,
			"org.freedesktop.DBus.Properties", "Get",
			g_variant_new("(ss)", candidate->interface, property),
			G_VARIANT_TYPE("(v)"), G_DBUS_CALL_FLAGS_NONE, 1000, NULL, &error);
		if (!reply)
		{
			if (report_error)
				sendError(property, error);
			if (error)
				g_error_free(error);
			return NULL;
		}
		GVariant *value = NULL;
		g_variant_get(reply, "(v)", &value);
		g_variant_unref(reply);
		return value;
	}

	bool ensureBackend()
	{
		if (backend)
		{
			GVariant *value = getPropertyOn(backend, "sourceState", false);
			if (value)
			{
				g_variant_unref(value);
				setAvailable(true);
				return true;
			}
			backend = NULL;
			setAvailable(false);
		}
		GVariant *value = getPropertyOn(&live555_backend, "sourceState", false);
		if (value)
		{
			g_variant_unref(value);
			backend = &live555_backend;
			setAvailable(true);
			eDebug("[eStreamServer] using DBus backend %s", backend->name);
			return true;
		}
		backend = NULL;
		setAvailable(false);
		return false;
	}

	GVariant *getProperty(const char *property, bool report_error = true)
	{
		if (!ensureBackend())
			return NULL;
		return getPropertyOn(backend, property, report_error);
	}

	int getInt(const char *property, int default_value)
	{
		GVariant *value = getProperty(property);
		int result = variantToInt(value, default_value);
		if (value)
			g_variant_unref(value);
		return result;
	}

	bool getBool(const char *property, bool default_value)
	{
		return getInt(property, default_value ? 1 : 0) != 0;
	}

	std::string getString(const char *property, const std::string &default_value)
	{
		GVariant *value = getProperty(property, false);
		std::string result = variantToString(value, default_value);
		if (value)
			g_variant_unref(value);
		return result;
	}

	bool setPropertyVariant(const char *property, GVariant *value)
	{
		if (!ensureBackend())
		{
			if (value)
				g_variant_unref(value);
			return false;
		}
		GError *error = NULL;
		GVariant *reply = g_dbus_connection_call_sync(connection, backend->name, backend->path,
			"org.freedesktop.DBus.Properties", "Set",
			g_variant_new("(ssv)", backend->interface, property, value),
			G_VARIANT_TYPE_UNIT, G_DBUS_CALL_FLAGS_NONE, 1000, NULL, &error);
		if (!reply)
		{
			sendError(property, error);
			if (error)
				g_error_free(error);
			return false;
		}
		g_variant_unref(reply);
		return true;
	}

	bool callBoolMethod(const char *method, GVariant *parameters)
	{
		if (!ensureBackend())
		{
			if (parameters)
				g_variant_unref(parameters);
			return false;
		}
		GError *error = NULL;
		GVariant *reply = g_dbus_connection_call_sync(connection, backend->name, backend->path,
			backend->interface, method, parameters, G_VARIANT_TYPE("(b)"),
			G_DBUS_CALL_FLAGS_NONE, 3000, NULL, &error);
		if (!reply)
		{
			sendError(method, error);
			if (error)
				g_error_free(error);
			return false;
		}
		gboolean result = FALSE;
		g_variant_get(reply, "(b)", &result);
		g_variant_unref(reply);
		return result;
	}

	bool callVoidMethod(const char *method, GVariant *parameters)
	{
		if (!ensureBackend())
		{
			if (parameters)
				g_variant_unref(parameters);
			return false;
		}
		GError *error = NULL;
		GVariant *reply = g_dbus_connection_call_sync(connection, backend->name, backend->path,
			backend->interface, method, parameters, G_VARIANT_TYPE_UNIT,
			G_DBUS_CALL_FLAGS_NONE, 3000, NULL, &error);
		if (!reply)
		{
			sendError(method, error);
			if (error)
				g_error_free(error);
			return false;
		}
		g_variant_unref(reply);
		return true;
	}
};

eStreamClient::eStreamClient(eStreamServer *handler, int socket, const std::string remotehost)
 : parent(handler), encoderFd(-1), streamFd(socket), streamThread(NULL), m_remotehost(remotehost),
   m_useencoder(false), m_live555Upstream(false), running(false), m_timeout(eTimer::create(eApp))
{
}

eStreamClient::~eStreamClient()
{
	rsn->stop();
	stop();
	if (streamThread)
	{
		streamThread->stop();
		delete streamThread;
	}
	if (encoderFd >= 0)
	{
		if (eEncoder::getInstance()) eEncoder::getInstance()->freeEncoder(encoderFd);
	}
	if (streamFd >= 0) ::close(streamFd);
}

void eStreamClient::start()
{
	rsn = eSocketNotifier::create(eApp, streamFd, eSocketNotifier::Read);
	CONNECT(rsn->activated, eStreamClient::notifier);
	CONNECT(m_timeout->timeout, eStreamClient::stopStream);
}

void eStreamClient::set_socket_option(int fd, int optid, int option)
{
	if(::setsockopt(fd, SOL_SOCKET, optid, &option, sizeof(option)))
		eDebug("[eStreamClient] Failed to set socket option: %m");
}

void eStreamClient::set_tcp_option(int fd, int optid, int option)
{
	if(::setsockopt(fd, SOL_TCP, optid, &option, sizeof(option)))
		eDebug("[eStreamClient] Failed to set TCP parameter: %m");
}

void eStreamClient::notifier(int what)
{
	if (!(what & eSocketNotifier::Read))
		return;

	ePtr<eStreamClient> ref = this;
	char buf[512];
	int len;
	if ((len = singleRead(streamFd, buf, sizeof(buf))) <= 0)
	{
		rsn->stop();
		stop();
		// Free encoder on disconnect
		if (encoderFd >= 0)
		{
			eDebug("[eStreamClient] connection lost: freeing encoder fd=%d", encoderFd);
			if (eEncoder::getInstance()) eEncoder::getInstance()->freeEncoder(encoderFd);
			encoderFd = -1;
		}
		parent->connectionLost(this);
		return;
	}
	request.append(buf, len);
	if (running || (request.find('\n') == std::string::npos))
		return;

	if (request.substr(0, 5) == "GET /")
	{
		size_t pos;
		size_t posdur;
		if (eSimpleConfig::getBool("config.streaming.authentication", false))
		{
			bool authenticated = false;
			if ((pos = request.find("Authorization: Basic ")) != std::string::npos)
			{
				std::string authentication, username, password;
				std::string hash = request.substr(pos + 21);
				pos = hash.find('\r');
				hash = hash.substr(0, pos);
				authentication = base64decode(hash);
				pos = authentication.find(':');
				if (pos != std::string::npos)
				{
					char *buffer = (char*)malloc(4096);
					if (buffer)
					{
						struct passwd pwd = {};
						struct passwd *pwdresult = NULL;
						std::string crypt;
						username = authentication.substr(0, pos);
						password = authentication.substr(pos + 1);
						getpwnam_r(username.c_str(), &pwd, buffer, 4096, &pwdresult);
						if (pwdresult)
						{
							struct crypt_data cryptdata = {};
							char *cryptresult = NULL;
							cryptdata.initialized = 0;
							crypt = pwd.pw_passwd;
							if (crypt == "*" || crypt == "x")
							{
								struct spwd spwd = {};
								struct spwd *spwdresult = NULL;
								getspnam_r(username.c_str(), &spwd, buffer, 4096, &spwdresult);
								if (spwdresult)
								{
									crypt = spwd.sp_pwdp;
								}
							}
							cryptresult = crypt_r(password.c_str(), crypt.c_str(), &cryptdata);
							authenticated = cryptresult && cryptresult == crypt;
						}
						free(buffer);
					}
				}
			}
			if (!authenticated)
			{
				const char *reply = "HTTP/1.0 401 Authorization Required\r\nWWW-Authenticate: Basic realm=\"streamserver\"\r\n\r\n";
				writeAll(streamFd, reply, strlen(reply));
				rsn->stop();
				parent->connectionLost(this);
				return;
			}
		}
		pos = request.find(' ', 5);
		if (pos != std::string::npos)
		{
			std::string serviceref = urlDecode(request.substr(5, pos - 5));
			if (!serviceref.empty())
			{
				const char *reply = "HTTP/1.0 200 OK\r\nConnection: Close\r\nContent-Type: video/mpeg\r\nServer: streamserver\r\n\r\n";
				writeAll(streamFd, reply, strlen(reply));
				/* We don't expect any incoming data, so set a tiny buffer */
				set_socket_option(streamFd, SO_RCVBUF, 1 * 1024);
				 /* We like 188k packets, so set the TCP window size to that */
				set_socket_option(streamFd, SO_SNDBUF, 188 * 1024);
				/* activate keepalive */
				set_socket_option(streamFd, SO_KEEPALIVE, 1);
				/* configure keepalive */
				set_tcp_option(streamFd, TCP_KEEPINTVL, 10); // every 10 seconds
				set_tcp_option(streamFd, TCP_KEEPIDLE, 1);	// after 1 second of idle
				set_tcp_option(streamFd, TCP_KEEPCNT, 2);	// drop connection after second miss
				/* also set 10 seconds data push timeout */
				set_tcp_option(streamFd, TCP_USER_TIMEOUT, 10 * 1000);

				if (serviceref.substr(0, 10) == "file?file=") /* convert openwebif stream request back to serviceref */
				{
					std::string filepart = serviceref.substr(10);
					size_t argpos = std::string::npos;
					const char *args[] = {
						"&bitrate=", "&duration=", "&width=", "&height=", "&framerate=",
						"&interlaced=", "&aspectratio=", "&vcodec=", "&acodec=",
						"&encoder=", "&live555=", "&sessionid=", nullptr
					};
					for (int i = 0; args[i]; ++i)
					{
						size_t p = filepart.find(args[i]);
						if (p != std::string::npos && (argpos == std::string::npos || p < argpos))
							argpos = p;
					}
					if (argpos != std::string::npos)
						serviceref = "1:0:1:0:0:0:0:0:0:0:" + filepart.substr(0, argpos) + "?" + filepart.substr(argpos + 1);
					else
						serviceref = "1:0:1:0:0:0:0:0:0:0:" + filepart;
				}
				/* Strip session ID from URL if it exists, PLi streaming can not handle it */
				pos = serviceref.find("&sessionid=");
				if (pos != std::string::npos) {
					serviceref.erase(pos, std::string::npos);
				}
				pos = serviceref.find("?sessionid=");
				if (pos != std::string::npos) {
					serviceref.erase(pos, std::string::npos);
				}

				pos = serviceref.find('?');
				if (pos == std::string::npos)
				{
					parent->startStream(serviceref, m_remotehost);

					eDebug("[eDVBServiceStream] stream ref: %s", serviceref.c_str());
					if (eDVBServiceStream::start(serviceref.c_str(), streamFd) >= 0)
					{
						running = true;
						m_serviceref = serviceref;
						m_useencoder = false;
					}
				}
				else
				{
					request = serviceref.substr(pos);
					serviceref = serviceref.substr(0, pos);
					/* BC support for ? instead of & as URL argument seperator */
					while((pos = request.find('?')) != std::string::npos)
					{
						request.replace(pos, 1, "&");
					}
					pos = request.find("&bitrate=");
					posdur = request.find("&duration=");
					eDebug("[eDVBServiceStream] stream ref: %s", serviceref.c_str());
					if (posdur != std::string::npos)
					{

						parent->startStream(serviceref, m_remotehost);

						if (eDVBServiceStream::start(serviceref.c_str(), streamFd) >= 0)
						{
							running = true;
							m_serviceref = serviceref;
							m_useencoder = false;
						}
						int timeout = 0;
						sscanf(request.substr(posdur).c_str(), "&duration=%d", &timeout);
						eDebug("[eDVBServiceStream] duration: %d seconds", timeout);
						if (timeout)
						{
							m_timeout->startLongTimer(timeout);
						}
					}
					else if (pos != std::string::npos)
					{
						/* we need to stream transcoded data */
						int bitrate = 1024 * 1024;
						int width = 720;
						int height = 576;
						int framerate = 25000;
						int interlaced = 0;
						int aspectratio = 0;
						int buffersize;
						std::string vcodec = "h264";
						std::string acodec = "aac";
						bool live555Upstream = request.find("&live555=1") != std::string::npos;

						if (!parent->canStartEncoderClient(m_remotehost, live555Upstream))
						{
							eWarning("[eStreamClient] encoder busy, rejecting transcoding request from %s live555=%d",
								m_remotehost.c_str(), live555Upstream ? 1 : 0);
							const char *reply = "HTTP/1.0 409 Conflict\r\nConnection: Close\r\nContent-Type: text/plain\r\n\r\nEncoder busy\r\n";
							writeAll(streamFd, reply, strlen(reply));
							rsn->stop();
							parent->connectionLost(this);
							return;
						}

						sscanf(request.substr(pos).c_str(), "&bitrate=%d", &bitrate);
						pos = request.find("&width=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "&width=%d", &width);
						pos = request.find("&height=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "&height=%d", &height);
						pos = request.find("&framerate=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "&framerate=%d", &framerate);
						pos = request.find("&interlaced=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "&interlaced=%d", &interlaced);
						pos = request.find("&aspectratio=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "&aspectratio=%d", &aspectratio);
						pos = request.find("&vcodec=");
						if (pos != std::string::npos)
						{
							vcodec = request.substr(pos + 8);
							pos = vcodec.find('&');
							if (pos != std::string::npos)
							{
								vcodec = vcodec.substr(0, pos);
							}
						}
						pos = request.find("&acodec=");
						if (pos != std::string::npos)
						{
							acodec = request.substr(pos + 8);
							pos = acodec.find('&');
							if (pos != std::string::npos)
							{
								acodec = acodec.substr(0, pos);
							}
						}
						encoderFd = -1;

						if (eEncoder::getInstance())
						{
							eServiceReference ref(serviceref);
							if (ref && ref.type == eServiceReference::idServiceHDMIIn)
								encoderFd = eEncoder::getInstance()->allocateHDMIEncoder(serviceref, buffersize, bitrate, width, height, framerate, !!interlaced, aspectratio,
										vcodec, acodec);
							else
								encoderFd = eEncoder::getInstance()->allocateEncoder(serviceref, buffersize, bitrate, width, height, framerate, !!interlaced, aspectratio,
										vcodec, acodec);
						}

						if (encoderFd >= 0)
						{
							m_serviceref = serviceref;
							m_useencoder = true;
							m_live555Upstream = live555Upstream;
							parent->updateClassicEncoderLock();

							streamThread = new eDVBRecordStreamThread(188, buffersize);

							if (streamThread)
							{
								streamThread->setTargetFD(streamFd);
								streamThread->start(encoderFd);
								running = true;
							}
						}
					}
				}
			}
		}
	}
	if (!running)
	{
		const char *reply = "HTTP/1.0 400 Bad Request\r\n\r\n";
		writeAll(streamFd, reply, strlen(reply));
		rsn->stop();
		parent->connectionLost(this);
		return;
	}
	request.clear();
}

void eStreamClient::stopStream()
{
	rsn->stop();
	// Free encoder BEFORE connectionLost removes us from the list
	// This ensures the encoder is released even if the destructor is delayed
	if (encoderFd >= 0)
	{
		eDebug("[eStreamClient] stopStream: freeing encoder fd=%d", encoderFd);
		if (eEncoder::getInstance()) eEncoder::getInstance()->freeEncoder(encoderFd);
		encoderFd = -1;
	}
	ePtr<eStreamClient> ref = this;
	parent->connectionLost(this);
}

std::string eStreamClient::getRemoteHost()
{
	return m_remotehost;
}

std::string eStreamClient::getServiceref()
{
	return m_serviceref;
}

bool eStreamClient::isUsingEncoder()
{
	return m_useencoder;
}

bool eStreamClient::isLive555Upstream()
{
	return m_live555Upstream;
}

DEFINE_REF(eStreamServer);

eStreamServer *eStreamServer::m_instance = NULL;

eStreamServer::eStreamServer()
 : eServerSocket(8001, eApp), m_dbus(new eStreamServerDBus(this))
{
	m_instance = this;
	unlink(classic_encoder_lock_file);
	e2avahi_announce(NULL, "_e2stream._tcp", 8001);
}

eStreamServer::~eStreamServer()
{
	for (eSmartPtrList<eStreamClient>::iterator it = clients.begin(); it != clients.end(); )
	{
		it = clients.erase(it);
	}
	delete m_dbus;
	m_dbus = NULL;
	unlink(classic_encoder_lock_file);
}

eStreamServer *eStreamServer::getInstance()
{
	return m_instance;
}

void eStreamServer::newConnection(int socket)
{
	ePtr<eStreamClient> client = new eStreamClient(this, socket, RemoteHost());
	clients.push_back(client);
	client->start();
}

void eStreamServer::connectionLost(eStreamClient *client)
{
	eSmartPtrList<eStreamClient>::iterator it = std::find(clients.begin(), clients.end(), client );
	if (it != clients.end())
	{
        std::string serviceref = it->getServiceref();
		if(serviceref.empty())
			serviceref = it->getDVBService().toString();
		std::string client = it->getRemoteHost();
		clients.erase(it);
		updateClassicEncoderLock();
		streamStatusChanged(2,serviceref.c_str(), client.c_str());
		eNavigation::getInstance()->removeStreamService(serviceref);
	}
}

void eStreamServer::startStream(const std::string serviceref, const std::string remotehost)
{
	streamStatusChanged(0,serviceref.c_str(), remotehost.c_str());
	eNavigation::getInstance()->addStreamService(serviceref);
}

void eStreamServer::stopStream()
{
	eSmartPtrList<eStreamClient>::iterator it = clients.begin();
	if (it != clients.end())
	{
		streamStatusChanged(1,it->getServiceref().c_str(), it->getRemoteHost().c_str());
		eNavigation::getInstance()->removeStreamService(it->getServiceref());
		it->stopStream();
	}
}

bool eStreamServer::stopStreamClient(const std::string remotehost, const std::string serviceref)
{
	for (eSmartPtrList<eStreamClient>::iterator it = clients.begin(); it != clients.end(); ++it)
	{
		if(it->getRemoteHost() == remotehost && it->getServiceref() == serviceref)
		{
			it->stopStream();
			return true;
		}
	}
	return false;
}

bool eStreamServer::hasExternalEncoderClients()
{
	for (eSmartPtrList<eStreamClient>::iterator it = clients.begin(); it != clients.end(); ++it)
	{
		if (it->isUsingEncoder() && !it->isLive555Upstream() && !isLocalStreamHost(it->getRemoteHost()))
			return true;
	}
	return false;
}

bool eStreamServer::hasLive555EncoderClients()
{
	return live555ClientCount() > 0 || sourceState() != 0;
}

bool eStreamServer::canStartEncoderClient(const std::string remotehost, bool live555Upstream)
{
	if (live555Upstream)
		return isLocalStreamHost(remotehost) && !hasExternalEncoderClients();
	return !hasLive555EncoderClients();
}

void eStreamServer::updateClassicEncoderLock()
{
	if (hasExternalEncoderClients())
	{
		CFile f(classic_encoder_lock_file, "w");
		if (f)
			fprintf(f, "1\n");
	}
	else
	{
		unlink(classic_encoder_lock_file);
	}
}

int eStreamServer::live555ClientCount(const std::string &protocol) const
{
	int total = 0;
	for (std::vector<eLive555StreamClient>::const_iterator it = m_live555Clients.begin(); it != m_live555Clients.end(); ++it)
	{
		if ((protocol.empty() || it->protocol == protocol) && it->count > 0)
			total += it->count;
	}
	return total;
}

std::string eStreamServer::live555ServiceRef()
{
	return serviceRef();
}

void eStreamServer::updateLive555ClientCount(const std::string &protocol, int count, const std::string &remotehost)
{
	if (count < 0)
		count = 0;

	int current = live555ClientCount(protocol);
	if (!count)
	{
		clearLive555Clients(protocol);
		return;
	}

	if (remotehost.empty())
	{
		if (count < current)
			pruneLive555Clients(protocol, count);
		return;
	}

	std::string serviceref = live555ServiceRef();
	int delta = count - current;
	if (delta > 0)
	{
		std::vector<eLive555StreamClient>::iterator found = m_live555Clients.end();
		for (std::vector<eLive555StreamClient>::iterator it = m_live555Clients.begin(); it != m_live555Clients.end(); ++it)
		{
			if (it->protocol == protocol && it->remotehost == remotehost)
			{
				found = it;
				break;
			}
		}

		if (found == m_live555Clients.end())
		{
			eLive555StreamClient client;
			client.protocol = protocol;
			client.remotehost = remotehost;
			client.serviceref = serviceref;
			client.count = delta;
			m_live555Clients.push_back(client);
		}
		else
		{
			if (!serviceref.empty())
				found->serviceref = serviceref;
			found->count += delta;
		}

		for (int i = 0; i < delta; ++i)
			streamStatusChanged(streamStatusChangedNewClient, serviceref.c_str(), remotehost.c_str());
		if (!serviceref.empty())
			eNavigation::getInstance()->addStreamService(serviceref);
		eDebug("[eStreamServer] live555 %s client %s connected count=%d", protocol.c_str(), remotehost.c_str(), count);
	}
	else if (delta < 0)
	{
		int remove_count = -delta;
		std::vector<std::string> removed_refs;
		for (std::vector<eLive555StreamClient>::iterator it = m_live555Clients.begin(); it != m_live555Clients.end() && remove_count > 0; )
		{
			if (it->protocol != protocol || it->remotehost != remotehost)
			{
				++it;
				continue;
			}

			int removed = it->count < remove_count ? it->count : remove_count;
			std::string event_ref = serviceref.empty() ? it->serviceref : serviceref;
			if (!event_ref.empty() && std::find(removed_refs.begin(), removed_refs.end(), event_ref) == removed_refs.end())
				removed_refs.push_back(event_ref);
			for (int i = 0; i < removed; ++i)
				streamStatusChanged(streamStatusChangedClientDisconnected, event_ref.c_str(), remotehost.c_str());
			it->count -= removed;
			remove_count -= removed;
			if (it->count <= 0)
				it = m_live555Clients.erase(it);
			else
				++it;
		}
		if (remove_count > 0)
			pruneLive555Clients(protocol, count);
		else if (!live555ClientCount())
		{
			for (std::vector<std::string>::const_iterator it = removed_refs.begin(); it != removed_refs.end(); ++it)
				eNavigation::getInstance()->removeStreamService(*it);
		}
		eDebug("[eStreamServer] live555 %s client %s disconnected count=%d", protocol.c_str(), remotehost.c_str(), count);
	}
	else
	{
		for (std::vector<eLive555StreamClient>::iterator it = m_live555Clients.begin(); it != m_live555Clients.end(); ++it)
		{
			if (it->protocol == protocol && it->remotehost == remotehost && !serviceref.empty())
				it->serviceref = serviceref;
		}
	}
}

void eStreamServer::clearLive555Clients(const std::string &protocol)
{
	std::string serviceref = live555ServiceRef();
	std::vector<std::string> removed_refs;
	bool removed_any = false;
	for (std::vector<eLive555StreamClient>::iterator it = m_live555Clients.begin(); it != m_live555Clients.end(); )
	{
		if (!protocol.empty() && it->protocol != protocol)
		{
			++it;
			continue;
		}
		std::string event_ref = serviceref.empty() ? it->serviceref : serviceref;
		if (!event_ref.empty() && std::find(removed_refs.begin(), removed_refs.end(), event_ref) == removed_refs.end())
			removed_refs.push_back(event_ref);
		for (int i = 0; i < it->count; ++i)
			streamStatusChanged(streamStatusChangedClientDisconnected, event_ref.c_str(), it->remotehost.c_str());
		removed_any = true;
		it = m_live555Clients.erase(it);
	}
	if (removed_any && !live555ClientCount())
	{
		for (std::vector<std::string>::const_iterator it = removed_refs.begin(); it != removed_refs.end(); ++it)
			eNavigation::getInstance()->removeStreamService(*it);
	}
}

void eStreamServer::pruneLive555Clients(const std::string &protocol, int target_count)
{
	if (target_count < 0)
		target_count = 0;

	std::string serviceref = live555ServiceRef();
	std::vector<std::string> removed_refs;
	int current = live555ClientCount(protocol);
	while (current > target_count)
	{
		bool removed = false;
		for (std::vector<eLive555StreamClient>::iterator it = m_live555Clients.begin(); it != m_live555Clients.end(); ++it)
		{
			if (it->protocol != protocol || it->count <= 0)
				continue;
			std::string event_ref = serviceref.empty() ? it->serviceref : serviceref;
			if (!event_ref.empty() && std::find(removed_refs.begin(), removed_refs.end(), event_ref) == removed_refs.end())
				removed_refs.push_back(event_ref);
			streamStatusChanged(streamStatusChangedClientDisconnected, event_ref.c_str(), it->remotehost.c_str());
			--it->count;
			--current;
			removed = true;
			if (it->count <= 0)
				m_live555Clients.erase(it);
			break;
		}
		if (!removed)
			break;
	}
	if (!live555ClientCount())
	{
		for (std::vector<std::string>::const_iterator it = removed_refs.begin(); it != removed_refs.end(); ++it)
			eNavigation::getInstance()->removeStreamService(*it);
	}
}

PyObject *eStreamServer::getConnectedClientDetails(int index)
{
	ePyObject ret;

	eUsePtr<iDVBChannel> stream_channel;
	eServiceReferenceDVB dvbservice;

	int idx = 0;
	for (eSmartPtrList<eStreamClient>::iterator it = clients.begin(); it != clients.end(); ++it)
	{
		if(idx == index)
		{
			dvbservice = it->getDVBService();
			break;
		}
	}

	if(dvbservice)
	{
		std::list<eDVBResourceManager::active_channel> list;
		ePtr<eDVBResourceManager> res_mgr;
		if ( !eDVBResourceManager::getInstance( res_mgr ) )
		{
			res_mgr->getActiveChannels(list);
		}

		if(list.size()) {
		
			eDVBChannelID channel;
			dvbservice.getChannelID(channel);

			for (std::list<eDVBResourceManager::active_channel>::iterator i(list.begin()); i != list.end(); ++i)
			{
				std::string channelid = i->m_channel_id.toString();
				if (channelid == channel.toString().c_str())
				{
					stream_channel = i->m_channel;
					break;
				}
			}
				
		}

	}

	ret = PyDict_New();

	if(stream_channel)
	{

		ePtr<iDVBFrontend> fe;
		if(!stream_channel->getFrontend(fe))
		{

			ePtr<iDVBFrontendData> fdata;
			fe->getFrontendData(fdata);
			if (fdata)
			{
				ePyObject fret = PyDict_New();;
				frontendDataToDict(fret, fdata);
				PutToDict(ret, "frontend", fret);
			}


			ePtr<iDVBTransponderData> tdata;
			fe->getTransponderData(tdata, true);
			if (tdata)
			{
				ePyObject tret = PyDict_New();;
				transponderDataToDict(tret, tdata);
				PutToDict(ret, "transponder", tret);
			}

		}

	}

	return ret;

}

PyObject *eStreamServer::getConnectedClients()
{
	ePyObject ret;
	int idx = 0;
	int cnt = clients.size() + live555ClientCount();
	ret = PyList_New(cnt);
	for (eSmartPtrList<eStreamClient>::iterator it = clients.begin(); it != clients.end(); ++it)
	{
		ePyObject tuple = PyTuple_New(3);
		PyTuple_SET_ITEM(tuple, 0, PyUnicode_FromString((char *)it->getRemoteHost().c_str()));
		PyTuple_SET_ITEM(tuple, 1, PyUnicode_FromString((char *)it->getServiceref().c_str()));
		PyTuple_SET_ITEM(tuple, 2, PyLong_FromLong(it->isUsingEncoder()));
		PyList_SET_ITEM(ret, idx++, tuple);
	}
	std::string live_serviceref = live555ServiceRef();
	for (std::vector<eLive555StreamClient>::const_iterator it = m_live555Clients.begin(); it != m_live555Clients.end(); ++it)
	{
		std::string serviceref = live_serviceref.empty() ? it->serviceref : live_serviceref;
		for (int i = 0; i < it->count; ++i)
		{
			ePyObject tuple = PyTuple_New(3);
			PyTuple_SET_ITEM(tuple, 0, PyUnicode_FromString((char *)it->remotehost.c_str()));
			PyTuple_SET_ITEM(tuple, 1, PyUnicode_FromString((char *)serviceref.c_str()));
			PyTuple_SET_ITEM(tuple, 2, PyLong_FromLong(1));
			PyList_SET_ITEM(ret, idx++, tuple);
		}
	}
	return ret;
}

bool eStreamServer::isRTSPEnabled()
{
	return rtspState() != RTSP_STATE_DISABLED;
}

bool eStreamServer::isHLSEnabled()
{
	return hlsState() != HLS_STATE_DISABLED;
}

bool eStreamServer::isUpstreamEnabled()
{
	return upstreamState() != UPSTREAM_STATE_DISABLED;
}

int eStreamServer::rtspClientCount()
{
	return m_dbus ? m_dbus->getInt("rtspClientCount", 0) : 0;
}

int eStreamServer::hlsClientCount()
{
	return m_dbus ? m_dbus->getInt("hlsClientCount", 0) : 0;
}

int eStreamServer::sourceState()
{
	return m_dbus ? m_dbus->getInt("sourceState", 0) : 0;
}

int eStreamServer::upstreamState()
{
	return m_dbus ? m_dbus->getInt("upstreamState", UPSTREAM_STATE_DISABLED) : UPSTREAM_STATE_DISABLED;
}

int eStreamServer::rtspState()
{
	return m_dbus ? m_dbus->getInt("rtspState", RTSP_STATE_DISABLED) : RTSP_STATE_DISABLED;
}

int eStreamServer::hlsState()
{
	return m_dbus ? m_dbus->getInt("hlsState", HLS_STATE_DISABLED) : HLS_STATE_DISABLED;
}

int eStreamServer::width()
{
	return m_dbus ? m_dbus->getInt("width", 720) : 720;
}

int eStreamServer::height()
{
	return m_dbus ? m_dbus->getInt("height", 576) : 576;
}

std::string eStreamServer::rtspUsername()
{
	return m_dbus ? m_dbus->getString("rtspUsername", m_dbus->rtsp_user) : "";
}

std::string eStreamServer::rtspPassword()
{
	return m_dbus ? m_dbus->getString("rtspPassword", m_dbus->rtsp_pass) : "";
}

std::string eStreamServer::rtspPath()
{
	return m_dbus ? m_dbus->getString("rtspPath", m_dbus->rtsp_path) : "";
}

std::string eStreamServer::hlsUsername()
{
	return m_dbus ? m_dbus->getString("hlsUsername", m_dbus->hls_user) : "";
}

std::string eStreamServer::hlsPassword()
{
	return m_dbus ? m_dbus->getString("hlsPassword", m_dbus->hls_pass) : "";
}

std::string eStreamServer::hlsPath()
{
	return m_dbus ? m_dbus->getString("hlsPath", m_dbus->hls_path) : "";
}

std::string eStreamServer::serviceRef()
{
	return m_dbus ? m_dbus->getString("serviceRef", "") : "";
}

void eStreamServer::setServiceRef(const std::string &value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("serviceRef", g_variant_new_string(value.c_str()));
}

std::string eStreamServer::uriParameters()
{
	return m_dbus ? m_dbus->getString("uriParameters", "") : "";
}

int eStreamServer::inputMode()
{
	return m_dbus ? m_dbus->getInt("inputMode", INPUT_MODE_LIVE) : INPUT_MODE_LIVE;
}

void eStreamServer::setInputMode(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("inputMode", g_variant_new_int32(value));
}

int eStreamServer::audioBitrate()
{
	return m_dbus ? m_dbus->getInt("audioBitrate", 96) : 96;
}

void eStreamServer::setAudioBitrate(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("audioBitrate", g_variant_new_int32(value));
}

int eStreamServer::videoBitrate()
{
	return m_dbus ? m_dbus->getInt("videoBitrate", 1500) : 1500;
}

void eStreamServer::setVideoBitrate(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("videoBitrate", g_variant_new_int32(value));
}

std::string eStreamServer::videoCodec()
{
	return m_dbus ? m_dbus->getString("videoCodec", "h264") : "h264";
}

void eStreamServer::setVideoCodec(const std::string &value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("videoCodec", g_variant_new_string(value.c_str()));
}

bool eStreamServer::autoBitrate()
{
	return m_dbus ? m_dbus->getBool("autoBitrate", false) : false;
}

void eStreamServer::setAutoBitrate(bool value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("autoBitrate", g_variant_new_boolean(value));
}

int eStreamServer::gopLength()
{
	return m_dbus ? m_dbus->getInt("gopLength", GOP_LENGTH_DEFAULT) : GOP_LENGTH_DEFAULT;
}

void eStreamServer::setGopLength(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("gopLength", g_variant_new_int32(value));
}

bool eStreamServer::gopOnSceneChange()
{
	return m_dbus ? m_dbus->getBool("gopOnSceneChange", false) : false;
}

void eStreamServer::setGopOnSceneChange(bool enabled)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("gopOnSceneChange", g_variant_new_boolean(enabled));
}

bool eStreamServer::openGop()
{
	if (!m_dbus || !m_dbus->ensureBackend())
		return false;
	return m_dbus->getBool("openGOP", false);
}

void eStreamServer::setOpenGop(bool enabled)
{
	if (!m_dbus || !m_dbus->ensureBackend())
		return;
	m_dbus->setPropertyVariant("openGOP", g_variant_new_boolean(enabled));
}

int eStreamServer::bFrames()
{
	return m_dbus ? m_dbus->getInt("bFrames", BFRAMES_DEFAULT) : BFRAMES_DEFAULT;
}

void eStreamServer::setBFrames(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("bFrames", g_variant_new_int32(value));
}

int eStreamServer::pFrames()
{
	return m_dbus ? m_dbus->getInt("pFrames", PFRAMES_DEFAULT) : PFRAMES_DEFAULT;
}

void eStreamServer::setPFrames(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("pFrames", g_variant_new_int32(value));
}

int eStreamServer::slices()
{
	return m_dbus ? m_dbus->getInt("slices", SLICES_DEFAULT) : SLICES_DEFAULT;
}

void eStreamServer::setSlices(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("slices", g_variant_new_int32(value));
}

int eStreamServer::level()
{
	return m_dbus ? m_dbus->getInt("level", LEVEL_DEFAULT) : LEVEL_DEFAULT;
}

void eStreamServer::setLevel(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("level", g_variant_new_int32(value));
}

int eStreamServer::profile()
{
	return m_dbus ? m_dbus->getInt("profile", PROFILE_DEFAULT) : PROFILE_DEFAULT;
}

void eStreamServer::setProfile(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("profile", g_variant_new_int32(value));
}

int eStreamServer::framerate()
{
	return m_dbus ? m_dbus->getInt("framerate", 23) : 23;
}

void eStreamServer::setFramerate(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("framerate", g_variant_new_int32(value));
}

int eStreamServer::aspectRatio()
{
	return m_dbus ? m_dbus->getInt("aspectRatio", 2) : 2;
}

void eStreamServer::setAspectRatio(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("aspectRatio", g_variant_new_int32(value));
}

int eStreamServer::interlaced()
{
	return m_dbus ? m_dbus->getInt("interlaced", 0) : 0;
}

void eStreamServer::setInterlaced(int value)
{
	if (m_dbus)
		m_dbus->setPropertyVariant("interlaced", g_variant_new_int32(value));
}

bool eStreamServer::enableRTSP(bool state, const std::string &path, unsigned int port, const std::string &user, const std::string &password)
{
	if (!m_dbus || !m_dbus->ensureBackend())
		return false;
	m_dbus->rtsp_path = path;
	m_dbus->rtsp_user = user;
	m_dbus->rtsp_pass = password;
	return m_dbus->callBoolMethod("enableRTSP", g_variant_new("(bsuss)", (gboolean)state, path.c_str(), (guint32)port, user.c_str(), password.c_str()));
}

bool eStreamServer::enableHLS(bool state, const std::string &path, unsigned int port, const std::string &user, const std::string &password)
{
	if (!m_dbus || !m_dbus->ensureBackend())
		return false;
	m_dbus->hls_path = path;
	m_dbus->hls_user = user;
	m_dbus->hls_pass = password;
	return m_dbus->callBoolMethod("enableHLS", g_variant_new("(bsuss)", (gboolean)state, path.c_str(), (guint32)port, user.c_str(), password.c_str()));
}

void eStreamServer::setResolution(int width, int height)
{
	if (m_dbus)
		m_dbus->callVoidMethod("setResolution", g_variant_new("(ii)", width, height));
}

eAutoInitPtr<eStreamServer> init_eStreamServer(eAutoInitNumbers::service + 1, "Stream server");
