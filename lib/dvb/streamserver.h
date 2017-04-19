#ifndef __DVB_STREAMSERVER_H_
#define __DVB_STREAMSERVER_H_

#include <lib/network/serversocket.h>
#include <lib/service/servicedvbstream.h>
#include <lib/nav/core.h>

#ifndef SWIG
class eStreamServer;

class eStreamClient: public eDVBServiceStream
{
	private:
	static void set_socket_option(int fd, int optid, int option);
	static void set_tcp_option(int fd, int optid, int option);

protected:
	eStreamServer *parent;
	int encoderFd;
	int streamFd;
	eDVBRecordStreamThread *streamThread;
	std::string m_remotehost;
	std::string m_serviceref;
	bool m_useencoder;

	bool running;

	void notifier(int);
	ePtr<eSocketNotifier> rsn;

	std::string request;

	ePtr<eTimer> m_timeout;

	void streamStopped() { stopStream(); }
	void tuneFailed() { stopStream(); }

public:
	void stopStream();
	eStreamClient(eStreamServer *handler, int socket, const std::string remotehost);
	~eStreamClient();

	void start();
	std::string getRemoteHost();
	std::string getServiceref();
	bool isUsingEncoder();
};
#endif

class eStreamServer: public eServerSocket
{
	DECLARE_REF(eStreamServer);
	static eStreamServer *m_instance;

	eSmartPtrList<eStreamClient> clients;

	void newConnection(int socket);

#ifdef SWIG
	eStreamServer();
	~eStreamServer();
#endif
public:
#ifndef SWIG
	eStreamServer();
	~eStreamServer();

	void connectionLost(eStreamClient *client);
#endif

	static eStreamServer *getInstance();
	void stopStream();
	bool stopStreamClient(const std::string remotehost, const std::string serviceref);
	PyObject *getConnectedClients();
};

#endif /* __DVB_STREAMSERVER_H_ */
