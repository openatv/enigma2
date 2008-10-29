#ifndef __socket_h
#define __socket_h

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <fcntl.h>

#include <lib/base/ebase.h>
#include <lib/base/eerror.h>
#include <string>
#include <libsig_comp.h>
#include <lib/base/buffer.h>

class eSocket: public Object
{
	int mystate;
	int issocket;
	unsigned int last_break;
private:
	int socketdesc;
	eIOBuffer readbuffer;
	eIOBuffer writebuffer;
	int writebusy;
	sockaddr_in  serv_addr;
protected:
	ePtr<eSocketNotifier> rsn;
	virtual void notifier(int);
public:
	eSocket(eMainloop *ml);
	eSocket(int socket, int issocket, eMainloop *ml);
	~eSocket();
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
	
	enum State {	Idle, HostLookup, Connecting,
			Listening, Connection, Closing };
	int state();
	
	Signal0<void> connectionClosed_;
	Signal0<void> connected_;
	Signal0<void> readyRead_;
	Signal0<void> hangup;
	Signal1<void,int> bytesWritten_;
	Signal1<void,int> error_;
};

#endif /* __socket_h */
