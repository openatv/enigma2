#ifndef __DVB_STREAMSERVER_H_
#define __DVB_STREAMSERVER_H_

#include <lib/network/serversocket.h>
#include <lib/service/servicedvbstream.h>
#include <lib/nav/core.h>

#ifndef SWIG
class eStreamServer;

class eStreamClient: public eDVBServiceStream
{
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

	void streamStopped();
	void tuneFailed();

public:
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
	PyObject *getConnectedClients();
};

#endif /* __DVB_STREAMSERVER_H_ */
