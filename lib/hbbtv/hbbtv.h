#ifndef __lib_hbbtv_hbbtv_h
#define __lib_hbbtv_hbbtv_h

#include <lib/hbbtv/oipfapplication.h>

#include <lib/base/ebase.h>
#include <lib/python/connections.h>

typedef struct _object PyObject;

#include <lib/service/event.h>
#include <lib/service/iservice.h>

#include <list>
#include <map>
#include <string>
#include <vector>

#if defined(__aarch64__)
#define HBBTV_USER_AGENT "Mozilla/5.0 (Linux aarch64; U;HbbTV/1.2.1 (+RTSP;Dream Property GmbH;Dreambox;1.5;1.0;) CE-HTML/1.0; en) WebKit QtWebkit OIPF/1.1 "
#define HBBTV_USER_AGENT_ARD_REPLAY "Mozilla/5.0 (Linux aarch64; U;HbbTV/2.0.0 (+RTSP;Dream Property GmbH;Dreambox;1.5;1.0;) CE-HTML/1.0; en) WebKit QtWebkit OIPF/1.1 "
#elif defined(__arm__)
#define HBBTV_USER_AGENT "Mozilla/5.0 (Linux armv7l; U;HbbTV/1.2.1 (+RTSP;Dream Property GmbH;Dreambox;1.5;1.0;) CE-HTML/1.0; en) WebKit QtWebkit OIPF/1.1 "
#define HBBTV_USER_AGENT_ARD_REPLAY HBBTV_USER_AGENT
#else
#define HBBTV_USER_AGENT "Mozilla/5.0 (Linux mipsel; U;HbbTV/1.2.1 (+RTSP;Dream Property GmbH;Dreambox;1.5;1.0;) CE-HTML/1.0; en) WebKit QtWebkit OIPF/1.1 "
#define HBBTV_USER_AGENT_ARD_REPLAY HBBTV_USER_AGENT
#endif

extern std::string hbbtvUserAgent;
extern std::string hbbtvUserAgentArdReplay;

class eDVBServicePMTHandler;
class HbbTVApplicationInfo;
class eNavigation;

class eHbbtv: public sigc::trackable
{
	static eHbbtv *instance;

public:
	eHbbtv();
	~eHbbtv();

	static const int VERSION_MAJOR = 1;
	static const int VERSION_MINOR = 1;
	static const int VERSION_MICRO = 1;

	enum EventTypes {
		EVENT_NOW = 0,
		EVENT_NEXT = 1,
	};

	enum PlayStates {
		BROADCAST_STATE_UNREALIZED = 0,
		BROADCAST_STATE_CONNECTING,
		BROADCAST_STATE_PRESENTING,
	};

	enum ChannelErrors {
		CHANNEL_ERROR_NOT_SUPPORTED = 0,
		CHANNEL_ERROR_TUNE_FAILED,
		CHANNEL_ERROR_TUNER_FOREIGN_LOCK,
		CHANNEL_ERROR_PARENTAL_LOCK,
		CHANNEL_ERROR_CANNOT_DECRYPT,
		CHANNEL_ERROR_UNKNOWN,
		CHANNEL_ERROR_SWITCH_INTERRUPTED,
		CHANNEL_ERROR_LOCKED_BY_RECORD,
		CHANNEL_ERROR_RESOLVE_FAILED,
		CHANNEL_ERROR_BANDWITH_INSUFFICIENT,
		CHANNEL_ERROR_CANNOT_ZAP,
	};

	enum StreamPlayStates {
		STREAM_STATE_STOPPED = 0,
		STREAM_STATE_PLAYING,
		STREAM_STATE_PAUSED,
		STREAM_STATE_CONNECTING,
		STREAM_STATE_BUFFERING,
		STREAM_STATE_FINISHED,
		STREAM_STATE_ERROR,
	};

	enum StreamErrors {
		STREAM_ERROR_NONE = -1,
		STREAM_ERROR_UNSUPPORTED = 0,
		STREAM_ERROR_CONNECTING,
		STREAM_ERROR_UNKNOWN,
		STREAM_ERROR_NO_RESOURCES,
		STREAM_ERROR_CORRUPT,
		STREAM_ERROR_UNAVAILABLE,
		STREAM_ERROR_UNAVAILABLE_POS,
	};

	static eHbbtv *getInstance();

	void setAitSignalsEnabled(bool enabled);
	void setServiceList(std::string sref);
	void setStreamState(int state, int error=STREAM_ERROR_UNKNOWN);
	int getStreamState() const { return m_streamState; };
	int getStreamError() const { return m_streamError; };
	const eOipfApplication getApplication(const std::string &id);
	const std::string resolveApplicationLocator(const std::string &dvbUrl);
	std::list<std::pair<std::string, std::string> > getApplicationIdsAndName();
	PyObject *getApplicationIdsAndNamePy();
	void pageLoadFinished();
	void setCurrentServiceReference(const eServiceReference &service);
	const std::string getCurrentServiceReferenceString() const;
	const std::string getVersionString() const;
	const std::string getRuntimeStatus() const;
	bool isAitSignalsEnabled() const { return m_aitSignalsEnabled; };
	bool hasApplications() const { return !m_applicationList.empty(); };
	const std::string getRedButtonApplicationId() const { return m_redButtonApp; };
	const std::string getTextApplicationId() const { return m_textApp; };
	const std::string getUserAgent() const;
	const std::string getArdReplayUserAgent() const;
	void setUserAgent(const std::string &userAgent);
	void setArdReplayUserAgent(const std::string &userAgent);
	void setDebugEnabled(bool enabled);
	bool getDebugEnabled() const { return m_debugEnabled; };
	bool hasVideoWindow() const { return m_videoWindowValid; };
	const std::string getVideoWindowString() const;
	void notifyAitInvalidated();

	// Python-visible backend bring-up helpers.
	// They exercise the same signals that the Dream/OIPF bridge will call later.
	void debugEmitPlayServiceRequest(const std::string &sref);
	void debugEmitPlayStreamRequest(const std::string &uri);
	void debugEmitPauseStreamRequest();
	void debugEmitStopStreamRequest();
	void debugEmitSetVideoWindowRequest(int x, int y, int w, int h);
	void debugEmitUnsetVideoWindowRequest();
	void debugEmitShow();
	void debugEmitHide();
	void debugEmitCreateApplicationRequest(const std::string &uri);

#ifndef SWIG
	void updateApplicationsFromPMTHandler(eDVBServicePMTHandler *handler);
	void updateApplications(const std::vector<HbbTVApplicationInfo> &applications);
	void clearApplications(bool notify=true);

	void updateFromNavigation(eNavigation *navigation);
	const std::string getCurrentServiceTriplet();
	const eServiceReference &getCurrentService();
	void setCurrentService(const eServiceReference &service, const ePtr<iPlayableService> &playableService);
	void setPlayableService(const ePtr<iPlayableService> &playableService);
	void playService(const std::string &sref);
	void playStream(const std::string &uri);
	void pauseStream();
	bool seekStream(pts_t to);
	void stopStream();
	void nextService();
	void prevService();
	void onCurrentServiceStop();
	void onCurrentServiceEvent(iPlayableService *playableService, int what);
	ePtr<iPlayableService> getPlayableService();
	int getPlayTime();
	int getPlayPosition();
	void setVolume(int volume);
	const std::list<eServiceReference> getServiceList();
	ePtr<eServiceEvent> getEvent(int nownext);
	void setVideoWindow(unsigned int x, unsigned int y, unsigned int w, unsigned int h);
	void unsetVideoWindow();
	void showCurrent();
	void hideCurrent();
	void createApplication(const std::string &uri);
	void notifyChannelError(int error);
	const std::string normalizeStreamReference(const std::string &uri) const;

	PSignal0<void> currentServiceChanged;
	PSignal1<void, int> serviceChangeError;
	PSignal2<void, int, int> streamPlayStateChanged;
	PSignal0<void> serviceListChanged;
	PSignal0<void> loadFinished;
#endif

	PSignal1<void, const char *> playServiceRequest;
	PSignal1<void, const char *> playStreamRequest;
	PSignal0<void> pauseStreamRequest;
	PSignal0<void> stopStreamRequest;
	PSignal0<void> nextServiceRequest;
	PSignal0<void> prevServiceRequest;
	PSignal1<void, int> setVolumeRequest;
	PSignal4<void, int, int, int, int> setVideoWindowRequest;
	PSignal0<void> unsetVideoWindowRequest;
	PSignal0<void> aitInvalidated;
	PSignal1<void, const char *> redButtonAppplicationReady;
	PSignal1<void, const char *> textApplicationReady;
	PSignal1<void, const char *> createApplicationRequest;
	PSignal0<void> show;
	PSignal0<void> hide;

private:
	void addApplicationFromInfo(const HbbTVApplicationInfo &info);
	std::string makeApplicationId(int organisationId, int applicationId) const;
	bool isLikelyServiceReference(const std::string &value) const;
	bool isLikelyUrl(const std::string &value) const;
	void emitApplicationSignals();
	void debug(const char *fmt, ...) const;

	bool m_aitSignalsEnabled;
	int m_streamState;
	int m_streamError;
	std::string m_serviceList;
	std::string m_redButtonApp;
	std::string m_textApp;
	std::map<std::string, eOipfApplication> m_applications;
	std::list<std::pair<std::string, std::string> > m_applicationList;
	std::list<eServiceReference> m_serviceReferences;
	eServiceReference m_currentService;
	ePtr<iPlayableService> m_playableService;
	unsigned int m_videoWindow[4];
	bool m_videoWindowValid;
	bool m_debugEnabled;
	int m_lastChannelError;
};

#endif
