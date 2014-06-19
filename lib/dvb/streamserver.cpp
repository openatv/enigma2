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
		parent->freeEncoder(this, encoderFd);
	if (streamFd >= 0) ::close(streamFd);
}

void eStreamClient::start()
{
	rsn = eSocketNotifier::create(eApp, streamFd, eSocketNotifier::Read);
	CONNECT(rsn->activated, eStreamClient::notifier);
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
						encoderFd = parent->allocateEncoder(this, serviceref, bitrate, width, height, framerate, !!interlaced, aspectratio);
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
	ePtr<iServiceHandler> service_center;
	eServiceCenter::getInstance(service_center);
	if (service_center)
	{
		int index = 0;
		while (1)
		{
			int decoderindex;
			FILE *file;
			char filename[256];
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/decoder", index);
			if (CFile::parseInt(&decoderindex, filename) < 0) break;
			navigationInstances.push_back(new eNavigation(service_center, decoderindex));
			encoderUser.push_back(NULL);
			index++;
		}
	}
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

int eStreamServer::allocateEncoder(const eStreamClient *client, const std::string &serviceref, const int bitrate, const int width, const int height, const int framerate, const int interlaced, const int aspectratio)
{
	unsigned int i;
	int encoderfd = -1;
	for (i = 0; i < encoderUser.size(); i++)
	{
		if (!encoderUser[i])
		{
			char filename[128];
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/bitrate", i);
			CFile::writeInt(filename, bitrate);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/width", i);
			CFile::writeInt(filename, width);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/height", i);
			CFile::writeInt(filename, height);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/framerate", i);
			CFile::writeInt(filename, framerate);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/interlaced", i);
			CFile::writeInt(filename, interlaced);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/aspectratio", i);
			CFile::writeInt(filename, aspectratio);
			snprintf(filename, sizeof(filename), "/proc/stb/encoder/%d/apply", i);
			CFile::writeInt(filename, 1);
			if (navigationInstances[i]->playService(serviceref) >= 0)
			{
				snprintf(filename, sizeof(filename), "/dev/encoder%d", i);
				encoderfd = open(filename, O_RDONLY);
				encoderUser[i] = client;
			}
			break;
		}
	}
	return encoderfd;
}

void eStreamServer::freeEncoder(const eStreamClient *client, int encoderfd)
{
	unsigned int i;
	for (i = 0; i < encoderUser.size(); i++)
	{
		if (encoderUser[i] == client)
		{
			encoderUser[i] = NULL;
			if (navigationInstances[i])
			{
				navigationInstances[i]->stopService();
			}
			break;
		}
	}
	if (encoderfd >= 0) ::close(encoderfd);
}

eAutoInitPtr<eStreamServer> init_eStreamServer(eAutoInitNumbers::service + 1, "Stream server");
