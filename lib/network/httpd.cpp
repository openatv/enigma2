// #define DEBUG_HTTPD
#include <lib/network/httpd.h>

#include <sys/socket.h>
#include <lib/base/smartptr.h>
#include <lib/base/estring.h>
#include <error.h>
#include <errno.h>
#include <time.h>
#include <ctype.h>

#include <lib/network/http_dyn.h>
#include <lib/network/http_file.h>

eHTTPDataSource::eHTTPDataSource(eHTTPConnection *c): connection(c)
{
}

eHTTPDataSource::~eHTTPDataSource()
{
}

void eHTTPDataSource::haveData(void *data, int len)
{
}

int eHTTPDataSource::doWrite(int)
{
	return 0;
}

DEFINE_REF(eHTTPError);

eHTTPError::eHTTPError(eHTTPConnection *c, int errcode): eHTTPDataSource(c), errcode(errcode)
{
	std::string error="unknown error";
	switch (errcode)
	{
	case 400: error="Bad Request"; break;
	case 401: error="Unauthorized"; break;
	case 403: error="Forbidden"; break;
	case 404: error="Not found"; break;
	case 405: error="Method not allowed"; break;
	case 500: error="Internal server error"; break;
	}
	connection->code_descr=error;
	connection->code=errcode;
	
	connection->local_header["Content-Type"]=std::string("text/html");
}

int eHTTPError::doWrite(int w)
{
	std::string html;
	html+="<html><head><title>Error " + getNum(connection->code) + "</title></head>"+
		"<body><h1>Error " + getNum(errcode) + ": " + connection->code_descr + "</h1></body></html>\n";
	connection->writeBlock(html.c_str(), html.length());
	return -1;
}

eHTTPConnection::eHTTPConnection(int socket, int issocket, eHTTPD *parent, int persistent): eSocket(socket, issocket, parent->ml), parent(parent), persistent(persistent)
{
#ifdef DEBUG_HTTPD
	eDebug("eHTTPConnection");
#endif
	CONNECT(this->readyRead_ , eHTTPConnection::readData);
	CONNECT(this->bytesWritten_ , eHTTPConnection::bytesWritten);
	CONNECT(this->error_ , eHTTPConnection::gotError);
	CONNECT(this->connectionClosed_ , eHTTPConnection::destruct);
	CONNECT(this->hangup , eHTTPConnection::gotHangup);

	buffersize=128*1024;
	localstate=stateWait;
	remotestate=stateRequest;
	data=0;
}

void eHTTPConnection::destruct()
{
	eDebug("destruct, this %p!", this);
	gotHangup();
	delete this;
}

eHTTPConnection::eHTTPConnection(eMainloop *ml): eSocket(ml), parent(0), persistent(0)
{
	CONNECT(this->readyRead_ , eHTTPConnection::readData);
	CONNECT(this->bytesWritten_ , eHTTPConnection::bytesWritten);
	CONNECT(this->error_ , eHTTPConnection::gotError);
	CONNECT(this->connected_ , eHTTPConnection::hostConnected);	
	CONNECT(this->connectionClosed_ , eHTTPConnection::destruct);

	localstate=stateWait;
	remotestate=stateWait;
	
	buffersize=64*1024;
	data=0;
}

void eHTTPConnection::hostConnected()
{
	processLocalState();
}

void eHTTPConnection::start()
{
	if (localstate==stateWait)
	{
		localstate=stateRequest;
		processLocalState();
	}
}

void eHTTPConnection::gotHangup()
{
	if (data && remotestate == stateData)
		data->haveData(0, 0);
	data = 0;
	transferDone(0);

	localstate=stateWait;
	remotestate=stateRequest;
	
	remote_header.clear();
	local_header.clear();
}

eHTTPConnection *eHTTPConnection::doRequest(const char *uri, eMainloop *ml, int *error)
{
	if (error)
		*error=0;

	char *defaultproto="http";
	std::string proto, host, path;
	int port=80;
	
	int state=0; // 0 proto, 1 host, 2 port 3 path
	
	while (*uri)
	{
		switch (state)
		{
		case 0:
			if (!strncmp(uri, "://", 3))
			{
				state=1;
				uri+=3;
			} else if ((*uri=='/') || (*uri==':'))
			{
				host=proto;
				state=1;
				proto=defaultproto;
			} else
				proto.push_back(*uri++);
			break;
		case 1:
			if (*uri=='/')
				state=3;
			else if (*uri==':')
			{
				state=2;
				port=0;
				uri++;
			} else
				host.push_back(*uri++);
			break;
		case 2:
			if (*uri=='/')
				state=3;
			else
			{
				if (!isdigit(*uri))
				{
					port=-1;
					state=3;
				} else
				{
					port*=10;
					port+=*uri++-'0';
				}
			}
			break;
		case 3:
			path.push_back(*uri++);
		}
	}
	
	if (state==0)
	{
		path=proto;
		proto=defaultproto;
	}

#ifdef DEBUG_HTTPD
	eDebug("proto: '%s', host '%s', path '%s', port '%d'", proto.c_str(), host.c_str(), path.c_str(), port);
#endif

	if (!host.size())
	{
		eDebug("no host given");
		if (error)
			*error=ENOENT;
		return 0;
	}
	
	if (strcmp(proto.c_str(), "http"))
	{
		eDebug("invalid protocol (%s)", proto.c_str());
		if (error)
			*error=EINVAL;
		return 0;
	}
	
	if (port == -1)
	{
		eDebug("invalid port");
		if (error)
			*error=EINVAL;
		return 0;
	}
	
	if (!path.size())
		path="/";

	eHTTPConnection *c=new eHTTPConnection(ml);
	c->request="GET";
	c->requestpath=path.c_str();
	c->httpversion="HTTP/1.0";
	c->local_header["Host"]=host;
	if ((*error=c->connectToHost(host, port))) // already deleted by error
		return 0;
	return c;
}

void eHTTPConnection::readData()
{
	processRemoteState();
}

void eHTTPConnection::bytesWritten(int)
{
	processLocalState();
}

int eHTTPConnection::processLocalState()
{
	switch (state())
	{
	case Connection:
		break;
	default:
		return 0;
	}
	int done=0;
	while (!done)
	{
#ifdef DEBUG_HTTPD
		eDebug("processing local state %d", localstate);
#endif
		switch (localstate)
		{
		case stateWait:
#ifdef DEBUG_HTTPD
			eDebug("local wait");
#endif
			done=1;
			break;
		case stateRequest:
		{
#ifdef DEBUG_HTTPD
			eDebug("local request");
#endif
			std::string req=request+" "+requestpath+" "+httpversion+"\r\n";
			writeBlock(req.c_str(), req.length());
			localstate=stateHeader;
			remotestate=stateResponse;
			break;
		}
		case stateResponse:
		{
#ifdef DEBUG_HTTPD
			eDebug("local Response");
#endif
			writeString( (httpversion + " " + getNum(code) + " " + code_descr + "\r\n").c_str() );
			localstate=stateHeader;
			local_header["Connection"]="close";
			break;
		}
		case stateHeader:
#ifdef DEBUG_HTTPD
			eDebug("local header");
#endif
			for (std::map<std::string,std::string>::iterator cur=local_header.begin(); cur!=local_header.end(); ++cur)
			{
				writeString(cur->first.c_str());
				writeString(": ");
				writeString(cur->second.c_str());
				writeString("\r\n");
			}
			writeString("\r\n");
			if (request=="HEAD")
				localstate=stateDone;
			else
				localstate=stateData;
			break;
		case stateData:
#ifdef DEBUG_HTTPD
			eDebug("local data");
#endif
			if (data)
			{
				int btw=buffersize-bytesToWrite();
				if (btw>0)
				{
					if (data->doWrite(btw)<0)
					{
						localstate=stateDone;
					} else
						done=1;
				} else
					done=1;
			} else
				done=1; // wait for remote response
			break;
		case stateDone:
#if 0
			// move to stateClose
			if (remote_header.find("Connection") != remote_header.end())
			{
				std::string &connection=remote_header["Connection"];
				if (connection == "keep-alive")
					localstate=stateWait;
				else
					localstate=stateClose;
			}
#endif
#ifdef DEBUG_HTTPD
			eDebug("locate state done");
#endif
			if (!persistent)
				localstate=stateClose;
			else
				localstate=stateWait;
			break;
		case stateClose:
#ifdef DEBUG_HTTPD
			eDebug("closedown");
#endif
			if (persistent)
			{
				data = 0;
				localstate = stateWait;
			} else
				close();		// bye, bye, remote
			return 1;
		}
	}
#ifdef DEBUG_HTTPD
 	eDebug("end local");
#endif
	return 0;
}

int eHTTPConnection::processRemoteState()
{
	int abort=0, done=0;
#ifdef DEBUG_HTTPD
	eDebug("%d bytes avail", bytesAvailable());
#endif
	while (((!done) || bytesAvailable()) && !abort)
	{
		switch (remotestate)
		{
		case stateWait:
		{
			int i=0;
#ifdef DEBUG_HTTPD
			eDebug("remote stateWait");
#endif
			char buffer[1024];
			while (bytesAvailable()) {
				i=readBlock(buffer, 1024);
			}
			done=1;
			break;
		}
		case stateRequest:
		{
#ifdef DEBUG_HTTPD
			eDebug("stateRequest");
#endif
			std::string line;
			if (!getLine(line))
			{
				done=1;
				abort=1;
				break;
			}
	
			int del[2];
			del[0]=line.find(" ");
			del[1]=line.find(" ", del[0]+1);
			if (del[0]==-1)
			{
				data = 0;
				eDebug("request buggy");
				httpversion="HTTP/1.0";
				data=new eHTTPError(this, 400);
				done=0;
				localstate=stateResponse;
				remotestate=stateDone;
				if (processLocalState())
					return -1;
				break;
			}
			request=line.substr(0, del[0]);
			requestpath=line.substr(del[0]+1, (del[1]==-1)?-1:(del[1]-del[0]-1));
			if (del[1]!=-1)
			{
				is09=0;
				httpversion=line.substr(del[1]+1);
			} else
				is09=1;

			if (is09 || (httpversion.substr(0, 7) != "HTTP/1.") || httpversion.size()!=8)
			{
				remotestate=stateData;
				done=0;
				httpversion="HTTP/1.0";
				content_length_remaining=content_length_remaining=0;
				data=new eHTTPError(this, 400);	// bad request - not supporting version 0.9 yet
			} else
				remotestate=stateHeader;
			break;
		}
		case stateResponse:
		{
#ifdef DEBUG_HTTPD
			eDebug("state response..");
#endif
			std::string line;
			if (!getLine(line))
			{
				done=1;
				abort=1;
				break;
			}
#ifdef DEBUG_HTTPD
			eDebug("line: %s", line.c_str());
#endif
			int del[2];
			del[0]=line.find(" ");
			del[1]=line.find(" ", del[0]+1);
			if (del[0]==-1)
				code=-1;
			else
			{
				httpversion=line.substr(0, del[0]);
				code=atoi(line.substr(del[0]+1, (del[1]==-1)?-1:(del[1]-del[0]-1)).c_str());
				if (del[1] != -1)
					code_descr=line.substr(del[1]+1);
				else
					code_descr="";
			}
			
			remotestate=stateHeader;
			break;
		}
		case stateHeader:
		{
#ifdef DEBUG_HTTPD
			eDebug("remote stateHeader");
#endif
			std::string line;
			if (!getLine(line))
			{
				done=1;
				abort=1;
				break;
			}
			if (!line.length())
			{
				content_length=0;
				content_length_remaining=-1;
				if (remote_header.count("Content-Length"))
				{
					content_length=atoi(remote_header["Content-Length"].c_str());
					content_length_remaining=content_length;
				}

				if (parent)
				{
					for (eSmartPtrList<iHTTPPathResolver>::iterator i(parent->resolver); i != parent->resolver.end(); ++i)
						if (!(i->getDataSource(data, request, requestpath, this)))
							break;
					localstate=stateResponse;		// can be overridden by dataSource
				} else
					data=createDataSource(this);

				if (!data)
				{
					data = 0;
					data = new eHTTPError(this, 404);
				}

				if (content_length || 		// if content-length is set, we have content
						remote_header.count("Content-Type") || 		// content-type - the same
						(localstate != stateResponse))	// however, if we are NOT in response-state, so we are NOT server, there's ALWAYS more data to come. (exception: http/1.1 persistent)
					remotestate=stateData;
				else
				{
					data->haveData(0, 0);
					remotestate=stateDone;
				}
				if (processLocalState())
					return -1;
			} else
			{
				int del=line.find(":");
				std::string name=line.substr(0, del), value=line.substr(del+1);
				if (value[0]==' ')
					value=value.substr(1);
				remote_header[std::string(name)]=std::string(value);
			}
			done=1;
			break;
		}
		case stateData:
		{
#ifdef DEBUG_HTTPD
			eDebug("remote stateData");
#endif
			ASSERT(data);
			char buffer[16284];
			int len;
			while (bytesAvailable())
			{
				int tr=sizeof(buffer);
				if (content_length_remaining != -1)
					if (tr>content_length_remaining)
						tr=content_length_remaining;
				len=readBlock(buffer, tr);
				data->haveData(buffer, len);
				if (content_length_remaining != -1)
					content_length_remaining-=len;
				if (!content_length_remaining)
				{
					data->haveData(0, 0);
					remotestate=stateDone;
					break;
				}
			}
			done=1;
			if (processLocalState())
				return -1;
			break;
		}
		case stateDone:
			remotestate=stateClose;
			break;
		case stateClose:
//			if (!persistent)
				remotestate=stateWait;
//			else
//				remotestate=stateRequest;
			abort=1;
			break;
		default:
			eDebug("HTTP: invalid state %d", remotestate);
			done=1;
		}
	}
#ifdef DEBUG_HTTPD
	eDebug("end remote");
#endif
	return 0;
}

void eHTTPConnection::writeString(const char *data)
{
	writeBlock(data, strlen(data));
}

int eHTTPConnection::getLine(std::string &line)
{
	if (!canReadLine())
		return 0;

	line = readLine();
	line.erase(line.length()-1);

	if (line[(line.length()-1)] == '\r')
		line.erase(line.length()-1);
	
	return 1;
}

void eHTTPConnection::gotError(int err)
{
	data = 0;
	transferDone(err);
	delete this;
}

eHTTPD::eHTTPD(int port, eMainloop *ml): eServerSocket(port, ml), ml(ml)
{
	if (!ok())
		eDebug("[NET] httpd server FAILED on port %d", port);
	else
		eDebug("[NET] httpd server started on port %d", port);
}

eHTTPConnection::~eHTTPConnection()
{
	eDebug("HTTP connection destruct");
	if ((!persistent) && (state()!=Idle))
		eWarning("~eHTTPConnection, status still %d", state());
}

void eHTTPD::newConnection(int socket)
{
	new eHTTPConnection(socket, 1, this);
}
