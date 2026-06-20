#ifndef __DVB_STREAMSERVER_H_
#define __DVB_STREAMSERVER_H_

#include <lib/network/serversocket.h>
#include <lib/service/servicedvbstream.h>
#include <lib/nav/core.h>
#include <lib/python/connections.h>

#ifndef SWIG
#include <string>
#include <vector>
#endif

#ifndef SWIG
class eStreamServer;
struct eStreamServerDBus;

class eStreamClient: public eDVBServiceStream
{
private:
	static void set_socket_option(int fd, int optid, int option);
	static void set_tcp_option(int fd, int optid, int option);

protected:
	eStreamServer *parent;
	int encoderFd;
	int streamFd;
	eDVBRecordStreamThread *streamThread;
	std::string m_remotehost;
	std::string m_serviceref;
	bool m_useencoder;
	bool m_live555Upstream;

	bool running;

	void notifier(int);
	ePtr<eSocketNotifier> rsn;

	std::string request;

	ePtr<eTimer> m_timeout;

	void streamStopped() { stopStream(); }
	void tuneFailed() { stopStream(); }

public:
	void stopStream();
	eStreamClient(eStreamServer *handler, int socket, const std::string remotehost);
	~eStreamClient();

	void start();
	std::string getRemoteHost();
	std::string getServiceref();
	eServiceReferenceDVB getDVBService() { return m_ref; }
	bool isUsingEncoder();
	bool isLive555Upstream();
};
#endif

class eStreamServer: public eServerSocket
{
	DECLARE_REF(eStreamServer);
	static eStreamServer *m_instance;
#ifndef SWIG
	friend class eStreamClient;
#endif

	eSmartPtrList<eStreamClient> clients;

	void newConnection(int socket);

#ifndef SWIG
	struct eLive555StreamClient
	{
		std::string protocol;
		std::string remotehost;
		std::string serviceref;
		int count;
	};

	std::vector<eLive555StreamClient> m_live555Clients;
	eStreamServerDBus *m_dbus;
	friend struct eStreamServerDBus;

	int live555ClientCount(const std::string &protocol = "") const;
	std::string live555ServiceRef();
	void updateLive555ClientCount(const std::string &protocol, int count, const std::string &remotehost);
	void clearLive555Clients(const std::string &protocol = "");
	void pruneLive555Clients(const std::string &protocol, int target_count);
	void updateClassicEncoderLock();
#endif

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
	void stopStream();
	void startStream(const std::string serviceref, const std::string remotehost);
	bool stopStreamClient(const std::string remotehost, const std::string serviceref);
	bool hasExternalEncoderClients();
	bool hasLive555EncoderClients();
	bool canStartEncoderClient(const std::string remotehost, bool live555Upstream = false);
	PyObject *getConnectedClients();
	PyObject *getConnectedClientDetails(int index);

	enum
	{
		INPUT_MODE_LIVE = 0,
		INPUT_MODE_HDMI_IN = 1,
		INPUT_MODE_BACKGROUND = 2
	};

	enum
	{
		UPSTREAM_STATE_DISABLED = 0,
		UPSTREAM_STATE_CONNECTING = 1,
		UPSTREAM_STATE_WAITING = 2,
		UPSTREAM_STATE_TRANSMITTING = 3,
		UPSTREAM_STATE_OVERLOAD = 4,
		UPSTREAM_STATE_ADJUSTING = 5,
		UPSTREAM_STATE_FAILED = 9
	};

	enum
	{
		RTSP_STATE_DISABLED = 0,
		RTSP_STATE_IDLE = 1,
		RTSP_STATE_RUNNING = 2
	};

	enum
	{
		HLS_STATE_DISABLED = 0,
		HLS_STATE_IDLE = 1,
		HLS_STATE_RUNNING = 2
	};

	enum
	{
		PROFILE_MAIN = 0,
		PROFILE_HIGH = 1,
		PROFILE_DEFAULT = PROFILE_MAIN
	};

	enum
	{
		LEVEL1_1 = 0,
		LEVEL1_2,
		LEVEL1_3,
		LEVEL2_0,
		LEVEL2_1,
		LEVEL2_2,
		LEVEL3_0,
		LEVEL3_1,
		LEVEL3_2,
		LEVEL4_0,
		LEVEL4_1,
		LEVEL4_2,
		LEVEL_MIN = LEVEL1_1,
		LEVEL_DEFAULT = LEVEL3_1,
		LEVEL_MAX = LEVEL4_2
	};

	enum
	{
		GOP_LENGTH_AUTO = 0,
		GOP_LENGTH_DEFAULT = GOP_LENGTH_AUTO,
		GOP_LENGTH_MIN = 0,
		GOP_LENGTH_MAX = 15000,
		BFRAMES_MIN = 0,
		BFRAMES_DEFAULT = 0,
		BFRAMES_MAX = 2,
		PFRAMES_MIN = 0,
		PFRAMES_DEFAULT = 4,
		PFRAMES_MAX = 14,
		SLICES_MIN = 0,
		SLICES_DEFAULT = 0,
		SLICES_MAX = 16
	};

	bool isRTSPEnabled();
	bool isHLSEnabled();
	bool isUpstreamEnabled();
	int rtspClientCount();
	int hlsClientCount();
	int sourceState();
	int upstreamState();
	int rtspState();
	int hlsState();
	int width();
	int height();
	std::string rtspUsername();
	std::string rtspPassword();
	std::string rtspPath();
	std::string hlsUsername();
	std::string hlsPassword();
	std::string hlsPath();
	std::string serviceRef();
	void setServiceRef(const std::string &value);
	std::string uriParameters();
	int inputMode();
	void setInputMode(int value);
	int audioBitrate();
	void setAudioBitrate(int value);
	int videoBitrate();
	void setVideoBitrate(int value);
	std::string videoCodec();
	void setVideoCodec(const std::string &value);
	bool autoBitrate();
	void setAutoBitrate(bool value);
	int gopLength();
	void setGopLength(int value);
	bool gopOnSceneChange();
	void setGopOnSceneChange(bool enabled);
	bool openGop();
	void setOpenGop(bool enabled);
	int bFrames();
	void setBFrames(int value);
	int pFrames();
	void setPFrames(int value);
	int slices();
	void setSlices(int value);
	int level();
	void setLevel(int value);
	int profile();
	void setProfile(int value);
	int framerate();
	void setFramerate(int value);
	int aspectRatio();
	void setAspectRatio(int value);
	int interlaced();
	void setInterlaced(int value);
	bool enableRTSP(bool state, const std::string &path = "stream", unsigned int port = 5554, const std::string &user = "", const std::string &password = "");
	bool enableHLS(bool state, const std::string &path = "stream", unsigned int port = 8090, const std::string &user = "", const std::string &password = "");
	void setResolution(int width, int height);

	PSignal1<void, int> availabilityChanged;
	PSignal1<void, int> sourceStateChanged;
	PSignal1<void, int> upstreamStateChanged;
	PSignal1<void, int> upstreamBitrateChanged;
	PSignal2<void, int, const char*> rtspClientCountChanged;
	PSignal2<void, int, const char*> hlsClientCountChanged;
	PSignal1<void, int> rtspStateChanged;
	PSignal1<void, int> hlsStateChanged;
	PSignal1<void, const char*> uriParametersChanged;
	PSignal1<void, const char*> dbusError;
	PSignal0<void> ping;
	PSignal3<void,int,const char *,const char *> streamStatusChanged;

	enum
	{
		streamStatusChangedNewClient,
		streamStatusChangedClientStopped,
		streamStatusChangedClientDisconnected
	};

};

#endif /* __DVB_STREAMSERVER_H_ */
