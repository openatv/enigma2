#ifndef __httpd_h
#define __httpd_h

#include <asm/types.h>
#include <map>

#include <lib/base/eptrlist.h>
#include <lib/base/ebase.h>
#include <lib/base/estring.h>
#include <lib/base/eerror.h>
#include <lib/network/socket.h>
#include <lib/network/serversocket.h>

class eHTTPConnection;
class eHTTPDataSource;
class eHTTPD;

class eHTTPPathResolver
{
public:
	virtual ~eHTTPPathResolver() {}; 
	virtual eHTTPDataSource *getDataSource(eString request, eString path, eHTTPConnection *conn)=0;
};

class eHTTPDataSource
{
protected:
	eHTTPConnection *connection;
public:
	eHTTPDataSource(eHTTPConnection *c);
	virtual ~eHTTPDataSource();
	virtual void haveData(void *data, int len);
	virtual int doWrite(int bytes);	// number of written bytes, -1 for "no more"
};

class eHTTPError: public eHTTPDataSource
{
	int errcode;
public:
	eHTTPError(eHTTPConnection *c, int errcode);
	~eHTTPError() { }
	void haveData();
	int doWrite(int bytes);
};

class eHTTPConnection: public eSocket
{
	void doError(int error);
	
	int getLine(eString &line);
	
	int processLocalState();
	int processRemoteState();
	void writeString(const char *data);
	
	eHTTPDataSource *data;
	eHTTPD *parent;
	
	int buffersize;
private:
	void readData();
	void gotError(int);
	void bytesWritten(int);
	void hostConnected();
	void destruct();
public:
	Signal1<void,int> transferDone;
	Signal1<eHTTPDataSource*,eHTTPConnection*> createDataSource;
	enum
	{
		/*
		
		< GET / HTTP/1.0
		< If-modified-since: bla
		<
		< Data
		> 200 OK HTTP/1.0
		> Content-Type: text/html
		>
		> Data
		*/
	
		stateWait, stateRequest, stateResponse, stateHeader, stateData, stateDone, stateClose
	};
	int localstate, remotestate;
	int persistent;
	
	eHTTPConnection(int socket, int issocket, eHTTPD *parent, int persistent=0);
	eHTTPConnection(eMainloop *ml); // ready to do "connectToHost"
	static eHTTPConnection *doRequest(const char *uri, eMainloop *ml, int *error=0);
	void start();
	void gotHangup();
	~eHTTPConnection();
	
		// stateRequest
	eString request, requestpath, httpversion;
	int is09;
	
		// stateResponse
	
	int code;
	eString code_descr;
	
	std::map<std::string,std::string> remote_header, local_header;
	
		// stateData
	int content_length, content_length_remaining;
};

class eHTTPD: public eServerSocket
{
	friend class eHTTPConnection;
	ePtrList<eHTTPPathResolver> resolver;
	eMainloop *ml;
public:
	eHTTPD(int port, eMainloop *ml);
	void newConnection(int socket);

	void addResolver(eHTTPPathResolver *r) { resolver.push_back(r); }
	void removeResolver(eHTTPPathResolver *r) { resolver.remove(r); }
};

#endif
