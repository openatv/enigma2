#include <sys/select.h>
#include <unistd.h>
#include <string.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <lib/dvb/streamserver.h>

eStreamClient::eStreamClient(eStreamServer *handler, int socket)
 : parent(handler), streamFd(socket)
{
	running = false;
}

eStreamClient::~eStreamClient()
{
	rsn->stop();
	stop();
	if (streamFd >= 0) ::close(streamFd);
}

void eStreamClient::start()
{
	rsn = eSocketNotifier::create(eApp, streamFd, eSocketNotifier::Read);
	CONNECT(rsn->activated, eStreamClient::notifier);
}

void eStreamClient::notifier(int what)
{
	if (what & eSocketNotifier::Read)
	{
		char buf[512];
		int len;
		if ((len = singleRead(streamFd, buf, sizeof(buf))) <= 0)
		{
			rsn->stop();
			stop();
			parent->connectionLost(this);
			return;
		}
		request.append(buf, len);
		if (!running)
		{
			if (request.find('\n') != std::string::npos)
			{
				if (request.substr(0, 5) == "GET /")
				{
					std::string serviceref;
					size_t pos = request.find(' ', 5);
					if (pos != std::string::npos)
					{
						serviceref = urlDecode(request.substr(5, pos - 5));
						if (!serviceref.empty())
						{
							const char *reply = "HTTP/1.0 200 OK\r\nConnection: Close\r\nContent-Type: video/mpeg\r\nServer: streamserver\r\n\r\n";
							writeAll(streamFd, reply, strlen(reply));
							if (eDVBServiceStream::start(serviceref.c_str(), streamFd) >= 0)
							{
								running = true;
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
		}
	}
}

void eStreamClient::streamStopped()
{
	rsn->stop();
	parent->connectionLost(this);
}

void eStreamClient::tuneFailed()
{
	rsn->stop();
	parent->connectionLost(this);
}

DEFINE_REF(eStreamServer);

eStreamServer::eStreamServer()
 : eServerSocket(8001, eApp)
{
}

eStreamServer::~eStreamServer()
{
	for (eSmartPtrList<eStreamClient>::iterator it = clients.begin(); it != clients.end(); )
	{
		it = clients.erase(it);
	}
}

void eStreamServer::newConnection(int socket)
{
	ePtr<eStreamClient> client = new eStreamClient(this, socket);
	clients.push_back(client);
	client->start();
}

void eStreamServer::connectionLost(eStreamClient *client)
{
	eSmartPtrList<eStreamClient>::iterator it = std::find(clients.begin(), clients.end(), client );
	if (it != clients.end())
	{
		clients.erase(it);
	}
}

eAutoInitPtr<eStreamServer> init_eStreamServer(eAutoInitNumbers::dvb + 1, "Stream server");
