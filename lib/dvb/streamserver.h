#ifndef __DVB_STREAMSERVER_H_
#define __DVB_STREAMSERVER_H_

#include <vector>

#include <lib/network/serversocket.h>
#include <lib/service/servicedvbstream.h>
#include <lib/nav/core.h>

class eStreamServer;

class eStreamClient: public eDVBServiceStream
{
protected:
	eStreamServer *parent;
	int encoderFd;
	int streamFd;
	eDVBRecordStreamThread *streamThread;

	bool running;

	void notifier(int);
	ePtr<eSocketNotifier> rsn;

	std::string request;

	void streamStopped();
	void tuneFailed();

public:
	eStreamClient(eStreamServer *handler, int socket);
	~eStreamClient();

	void start();
};

class eStreamServer: public eServerSocket
{
	DECLARE_REF(eStreamServer);

	eSmartPtrList<eStreamClient> clients;
	std::vector<eNavigation *> navigationInstances;
	std::vector<const eStreamClient *> encoderUser;

	void newConnection(int socket);

public:
	eStreamServer();
	~eStreamServer();

	void connectionLost(eStreamClient *client);

	int allocateEncoder(const eStreamClient *client, const std::string &serviceref, const int bitrate, const int width, const int height, const int framerate, const int interlaced, const int aspectratio);
	void freeEncoder(const eStreamClient *client, int encoderfd);
};

#endif /* __DVB_STREAMSERVER_H_ */
