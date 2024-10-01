
#include <lib/base/wrappers.h>
#include <lib/base/internetcheck.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <net/if.h>

#include <curl/curl.h>
#include <curl/easy.h>

DEFINE_REF(eInternetCheck);

std::string getActiveAdapter()
{
	std::string ret = "";
	struct ifaddrs *ifaddr, *ifa;
	int status;
	// Get the list of network interfaces
	status = getifaddrs(&ifaddr);
	if (status != 0)
	{
		eDebug("[Enigma] getActiveAdapter: Failed to get network interfaces.");
		return "";
	}
	// Iterate through the network interfaces
	for (ifa = ifaddr; ifa != nullptr; ifa = ifa->ifa_next)
	{
		if (ifa->ifa_addr == nullptr)
			continue;
		if (ifa->ifa_flags & IFF_LOOPBACK) // ignore loopback
			continue;
		// Check if the interface is active and has an IP address
		if ((ifa->ifa_flags & IFF_UP) && (ifa->ifa_addr->sa_family == AF_INET ||
										  ifa->ifa_addr->sa_family == AF_INET6))
		{

			if (strstr(ifa->ifa_name, "eth") || strstr(ifa->ifa_name, "wlan"))
			{
				eDebug("[Enigma] getActiveAdapter: Active network interface: %s.", ifa->ifa_name);
				ret = ifa->ifa_name;
				break;
			}
		}
	}
	freeifaddrs(ifaddr);
	return ret;
}

int checkLinkStatus()
{
	std::string interface = getActiveAdapter();
	if (interface.empty())
	{
		eDebug("[Enigma] checkLinkStatus: No valid active network adapter.");
		return 4;
	}

	int sock;
	struct ifreq ifr = {};
	// Create a socket
	sock = socket(AF_INET, SOCK_DGRAM, 0);
	if (sock < 0)
	{
		eDebug("[Enigma] checkLinkStatus: Failed to create socket.");
		return 3;
	}
	// Set the interface name
	strncpy(ifr.ifr_name, interface.c_str(), IFNAMSIZ);
	// Get the interface flags
	if (ioctl(sock, SIOCGIFFLAGS, &ifr) < 0)
	{
		eDebug("[Enigma] checkLinkStatus: Failed to get interface flags.");
		close(sock);
		return 3;
	}
	int ret = (ifr.ifr_flags & IFF_RUNNING) ? 0 : 3;
	close(sock);
	return ret;
}


size_t curl_ignore_output(void *ptr, size_t size, size_t nmemb, void *stream) // NOSONAR
{
	(void)ptr;
	(void)stream;
	return size * nmemb;
}

int checkInternetAccess(const char *host, int timeout = 3)
{

	int link = checkLinkStatus();
	if (link != 0)
	{
		eDebug("[Enigma] checkInternetAccess: No Active link.");
		return link;
	}

	CURL *curl;
	CURLcode res;
	int ret = 0; // SUCCESS
	curl = curl_easy_init();
	if (curl)
	{
		eDebug("[Enigma] checkInternetAccess: Check host:'%s' with timeout:%d.", host, timeout);
		curl_easy_setopt(curl, CURLOPT_URL, host);
		curl_easy_setopt(curl, CURLOPT_SSLVERSION, CURL_SSLVERSION_TLSv1_2);
		curl_easy_setopt(curl, CURLOPT_NOBODY, 1);
		curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT, timeout);
		curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, &curl_ignore_output);
		while ((res = curl_easy_perform(curl)) != CURLE_OK)
		{
			switch (res)
			{
			case CURLE_COULDNT_RESOLVE_HOST:
				eDebug("[Enigma] checkInternetAccess: Failed to resolve host.");
				ret = 1;
				break;
			case CURLE_COULDNT_CONNECT:
			case CURLE_COULDNT_RESOLVE_PROXY:
				eDebug("[Enigma] checkInternetAccess: Failed.");
				ret = 2;
				break;
			default:
				eDebug("[Enigma] checkInternetAccess: Failed with error (%s).", curl_easy_strerror(res));
				ret = 2;
				break;
			}
			if (ret > 0)
				break;
		}
		curl_easy_cleanup(curl);
	}
	else
	{
		eDebug("[Enigma] checkInternetAccess: Failed to init curl.");
		return 2;
	}
	if (ret == 0)
		eDebug("[Enigma] checkInternetAccess: Success.");
	return ret;
}


//---------------------------------------------------------------------------------------------

eInternetCheck::eInternetCheck():
	m_callback(false),
	m_result(-1),
	m_threadrunning(false),
	msg_thread(this,1,"eInternetCheck_thread"),
	msg_main(eApp,1,"eInternetCheck_main")
{
	CONNECT(msg_thread.recv_msg, eInternetCheck::gotMessage);
	CONNECT(msg_main.recv_msg, eInternetCheck::gotMessage);
}

eInternetCheck::~eInternetCheck()
{
	if (m_threadrunning)
	{
		msg_thread.send(2);
		kill();
	}
}

void eInternetCheck::thread_finished()
{
	m_threadrunning=false;
}

void eInternetCheck::thread()
{
	m_threadrunning=true;
	hasStarted();
	[[maybe_unused]] int ret = nice(4);
	runLoop();
}

void eInternetCheck::gotMessage(const int &msg)
{
	switch (msg)
	{
		case 1:
			m_result = checkInternetAccess(m_host.c_str(), m_timeout);
			msg_main.send(0);
			break;
		case 0:
			if(m_callback)
				callback(m_result);
			break;
		case 2:
			quit(0);
			break;
		default:
			eDebug("[eInternetCheck] unhandled thread message");
	}
}

RESULT eInternetCheck::startThread(const char *host, int timeout, bool async)
{
	m_callback = false;
	if(async && m_threadrunning)
	{
		return 1;
	}
	if(async)
	{
		m_callback = true;
		m_timeout = timeout;
		m_host = host;
		msg_thread.send(1);
		run();
		return 0;
	}
	else
		return checkInternetAccess(host, timeout);
}
