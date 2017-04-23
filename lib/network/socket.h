#ifndef __socket_h
#define __socket_h

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/un.h>
#include <netdb.h>
#include <fcntl.h>

#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <libsig_comp.h>
#include <lib/base/buffer.h>

class eSocket: public sigc::trackable
{
private:
	int issocket;
	int last_break;
	eIOBuffer readbuffer;
	eIOBuffer writebuffer;
	int writebusy;
protected:
	int socketdesc;
	int mystate;
	ePtr<eSocketNotifier> rsn;
	eMainloop *mainloop;
	virtual void notifier(int);
public:
	eSocket(eMainloop *ml, int domain = AF_INET);
	eSocket(int socket, int issocket, eMainloop *ml);
	virtual ~eSocket();
	int connectToHost(std::string hostname, int port);
	int getDescriptor();
	int writeBlock(const char *data, unsigned int len);
	int setSocket(int socketfd, int issocket, eMainloop *ml);
	int bytesToWrite();
	int readBlock(char *data, unsigned int maxlen);
	int bytesAvailable();
	bool canReadLine();
	std::string readLine();
	void close();
			// flow control: start/stop data delivery into read buffer.
	void enableRead();
	void disableRead();

	void inject(const char *data, int len);

	enum State { Invalid, Idle, HostLookup, Connecting,
			Listening, Connection, Closing };
	int state();

	sigc::signal0<void> connectionClosed_;
	sigc::signal0<void> connected_;
	sigc::signal0<void> readyRead_;
	sigc::signal0<void> hangup;
	sigc::signal1<void,int> bytesWritten_;
	sigc::signal1<void,int> error_;
};

class eUnixDomainSocket: public eSocket
{
public:
	eUnixDomainSocket(eMainloop *ml);
	eUnixDomainSocket(int socket, int issocket, eMainloop *ml);
	~eUnixDomainSocket();
	int connectToPath(std::string path);
};

#endif /* __socket_h */
