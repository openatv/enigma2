#include <sys/select.h>
#include <unistd.h>
#include <string.h>
#include <openssl/evp.h>
#include <sys/types.h>
#include <pwd.h>
#include <shadow.h>
#include <crypt.h>

#include <lib/base/eerror.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/wrappers.h>
#include <lib/base/nconfig.h>
#include <lib/base/cfile.h>

#include <lib/dvb/streamserver.h>
#include <lib/dvb/encoder.h>

eStreamClient::eStreamClient(eStreamServer *handler, int socket)
 : parent(handler), encoderFd(-1), streamFd(socket), streamThread(NULL)
{
	running = false;
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
}

static void set_tcp_buffer_size(int fd, int optname, int buf_size)
{
	if (::setsockopt(fd, SOL_SOCKET, optname, &buf_size, sizeof(buf_size)))
		eDebug("Failed to set TCP SNDBUF or RCVBUF size: %m");
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
		parent->connectionLost(this);
		return;
	}
	request.append(buf, len);
	if (running || (request.find('\n') == std::string::npos))
		return;

	if (request.substr(0, 5) == "GET /")
	{
		size_t pos;
		if (eConfigManager::getConfigBoolValue("config.streaming.authentication"))
		{
			bool authenticated = false;
			if ((pos = request.find("Authorization: Basic ")) != std::string::npos)
			{
				std::string authentication, username, password;
				std::string hash = request.substr(pos + 21);
				pos = hash.find('\r');
				hash = hash.substr(0, pos);
				hash += "\n";
				{
					char *in, *out;
					in = strdup(hash.c_str());
					out = (char*)calloc(1, hash.size());
					if (in && out)
					{
						BIO *b64, *bmem;
						b64 = BIO_new(BIO_f_base64());
						bmem = BIO_new_mem_buf(in, hash.size());
						bmem = BIO_push(b64, bmem);
						BIO_read(bmem, out, hash.size());
						BIO_free_all(bmem);
						authentication.append(out, hash.size());
					}
					free(in);
					free(out);
				}
				pos = authentication.find(':');
				if (pos != std::string::npos)
				{
					char *buffer = (char*)malloc(4096);
					if (buffer)
					{
						struct passwd pwd;
						struct passwd *pwdresult = NULL;
						std::string crypt;
						username = authentication.substr(0, pos);
						password = authentication.substr(pos + 1);
						getpwnam_r(username.c_str(), &pwd, buffer, 4096, &pwdresult);
						if (pwdresult)
						{
							struct crypt_data cryptdata;
							char *cryptresult = NULL;
							cryptdata.initialized = 0;
							crypt = pwd.pw_passwd;
							if (crypt == "*" || crypt == "x")
							{
								struct spwd spwd;
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
				set_tcp_buffer_size(streamFd, SO_RCVBUF, 1 * 1024);
				 /* We like 188k packets, so set the TCP window size to that */
				set_tcp_buffer_size(streamFd, SO_SNDBUF, 188 * 1024);
				if (serviceref.substr(0, 10) == "file?file=") /* convert openwebif stream reqeust back to serviceref */
					serviceref = "1:0:1:0:0:0:0:0:0:0:" + serviceref.substr(10);
				pos = serviceref.find('?');
				if (pos == std::string::npos)
				{
					if (eDVBServiceStream::start(serviceref.c_str(), streamFd) >= 0)
						running = true;
				}
				else
				{
					request = serviceref.substr(pos);
					serviceref = serviceref.substr(0, pos);
					pos = request.find("?bitrate=");
					if (pos != std::string::npos)
					{
						/* we need to stream transcoded data */
						int bitrate = 1024 * 1024;
						int width = 720;
						int height = 576;
						int framerate = 25000;
						int interlaced = 0;
						int aspectratio = 0;
						sscanf(request.substr(pos).c_str(), "?bitrate=%d", &bitrate);
						pos = request.find("?width=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "?width=%d", &width);
						pos = request.find("?height=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "?height=%d", &height);
						pos = request.find("?framerate=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "?framerate=%d", &framerate);
						pos = request.find("?interlaced=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "?interlaced=%d", &interlaced);
						pos = request.find("?aspectratio=");
						if (pos != std::string::npos)
							sscanf(request.substr(pos).c_str(), "?aspectratio=%d", &aspectratio);
						encoderFd = -1;
						if (eEncoder::getInstance())
							encoderFd = eEncoder::getInstance()->allocateEncoder(serviceref, bitrate, width, height, framerate, !!interlaced, aspectratio);
						if (encoderFd >= 0)
						{
							running = true;
							streamThread = new eDVBRecordStreamThread(188);
							if (streamThread)
							{
								streamThread->setTargetFD(streamFd);
								streamThread->start(encoderFd);
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

void eStreamClient::streamStopped()
{
	ePtr<eStreamClient> ref = this;
	rsn->stop();
	parent->connectionLost(this);
}

void eStreamClient::tuneFailed()
{
	ePtr<eStreamClient> ref = this;
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

eAutoInitPtr<eStreamServer> init_eStreamServer(eAutoInitNumbers::service + 1, "Stream server");
