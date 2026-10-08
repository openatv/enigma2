#include <Python.h>
#include <lib/hbbtv/hbbtv.h>

#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/nav/core.h>
#include <lib/service/service.h>

#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

std::string hbbtvUserAgent = HBBTV_USER_AGENT;
std::string hbbtvUserAgentArdReplay = HBBTV_USER_AGENT_ARD_REPLAY;

eHbbtv *eHbbtv::instance = 0;

eHbbtv::eHbbtv()
	: m_aitSignalsEnabled(false),
	  m_streamState(STREAM_STATE_STOPPED),
	  m_streamError(STREAM_ERROR_NONE),
	  m_videoWindowValid(false),
	  m_debugEnabled(false),
	  m_lastChannelError(CHANNEL_ERROR_UNKNOWN)
{
	m_videoWindow[0] = m_videoWindow[1] = m_videoWindow[2] = m_videoWindow[3] = 0;
	const char *debugEnv = getenv("HBBTV_BACKEND_DEBUG");
	m_debugEnabled = debugEnv && debugEnv[0] && strcmp(debugEnv, "0");
}

void eHbbtv::debug(const char *fmt, ...) const
{
	if (!m_debugEnabled)
		return;
	char buffer[512] = {0};
	va_list args;
	va_start(args, fmt);
	vsnprintf(buffer, sizeof(buffer), fmt, args);
	va_end(args);
	eDebug("[eHbbtv] %s", buffer);
}

eHbbtv::~eHbbtv()
{
	if (instance == this)
		instance = 0;
}

eHbbtv *eHbbtv::getInstance()
{
	if (!instance)
		instance = new eHbbtv();
	return instance;
}

void eHbbtv::setAitSignalsEnabled(bool enabled)
{
	m_aitSignalsEnabled = enabled;
	debug("AIT signals enabled=%d", enabled ? 1 : 0);
	if (m_aitSignalsEnabled)
		emitApplicationSignals();
}

void eHbbtv::setServiceList(std::string sref)
{
	m_serviceList = sref;
	m_serviceReferences.clear();
	debug("service list root set to %s", sref.c_str());
	serviceListChanged();
}

void eHbbtv::setStreamState(int state, int error)
{
	m_streamState = state;
	m_streamError = error;
	debug("stream state=%d error=%d", state, error);
	streamPlayStateChanged(state, error);
}

const eOipfApplication eHbbtv::getApplication(const std::string &id)
{
	std::map<std::string, eOipfApplication>::const_iterator it = m_applications.find(id);
	if (it != m_applications.end())
		return it->second;
	return eOipfApplication::getById(id);
}

const std::string eHbbtv::resolveApplicationLocator(const std::string &dvbUrl)
{
	if (dvbUrl.compare(0, 6, "dvb://"))
		return dvbUrl;

	std::string id;
	const std::string currentAitMarker = "dvb://current.ait/";
	const std::string currentMarker = "dvb://current/";
	if (!dvbUrl.compare(0, currentAitMarker.size(), currentAitMarker))
		id = dvbUrl.substr(currentAitMarker.size());
	else if (!dvbUrl.compare(0, currentMarker.size(), currentMarker))
		id = dvbUrl.substr(currentMarker.size());

	if (id.empty() && !m_redButtonApp.empty())
		id = m_redButtonApp;

	if (!id.empty())
	{
		eOipfApplication app = getApplication(id);
		if (app.isValid())
			return app.getUrl();
		// Never resolve an unknown or ambiguous ID to a different application.
		debug("could not resolve application ID '%s'", id.c_str());
		return "";
	}

	if (!m_applications.empty())
		return m_applications.begin()->second.getUrl();

	debug("could not resolve application locator '%s'", dvbUrl.c_str());
	return "";
}

std::list<std::pair<std::string, std::string> > eHbbtv::getApplicationIdsAndName()
{
	return m_applicationList;
}

PyObject *eHbbtv::getApplicationIdsAndNamePy()
{
	PyObject *list = PyList_New(0);
	if (!list)
		return NULL;

	for (std::list<std::pair<std::string, std::string> >::const_iterator it = m_applicationList.begin(); it != m_applicationList.end(); ++it)
	{
		PyObject *tuple = Py_BuildValue("(ss)", it->first.c_str(), it->second.c_str());
		if (!tuple)
		{
			Py_DECREF(list);
			return NULL;
		}
		PyList_Append(list, tuple);
		Py_DECREF(tuple);
	}

	return list;
}

void eHbbtv::pageLoadFinished()
{
	loadFinished();
}

void eHbbtv::setCurrentServiceReference(const eServiceReference &service)
{
	const bool changed = m_currentService != service;
	m_currentService = service;
	debug("current service reference=%s", service.toString().c_str());
	if (changed)
		clearApplications();
	currentServiceChanged();
}

const std::string eHbbtv::getCurrentServiceReferenceString() const
{
	return m_currentService.toString();
}

const std::string eHbbtv::getVersionString() const
{
	char buffer[32] = {0};
	snprintf(buffer, sizeof(buffer), "%d.%d.%d", VERSION_MAJOR, VERSION_MINOR, VERSION_MICRO);
	return std::string(buffer);
}

const std::string eHbbtv::getUserAgent() const
{
	return hbbtvUserAgent;
}

const std::string eHbbtv::getArdReplayUserAgent() const
{
	return hbbtvUserAgentArdReplay;
}

void eHbbtv::setUserAgent(const std::string &userAgent)
{
	if (!userAgent.empty())
		hbbtvUserAgent = userAgent;
}

void eHbbtv::setArdReplayUserAgent(const std::string &userAgent)
{
	if (!userAgent.empty())
		hbbtvUserAgentArdReplay = userAgent;
}

void eHbbtv::setDebugEnabled(bool enabled)
{
	m_debugEnabled = enabled;
}

const std::string eHbbtv::getVideoWindowString() const
{
	if (!m_videoWindowValid)
		return "";
	char buffer[96] = {0};
	snprintf(buffer, sizeof(buffer), "%u,%u,%u,%u", m_videoWindow[0], m_videoWindow[1], m_videoWindow[2], m_videoWindow[3]);
	return std::string(buffer);
}

const std::string eHbbtv::getRuntimeStatus() const
{
	char buffer[1024] = {0};
	snprintf(buffer, sizeof(buffer),
		"version=%d.%d.%d;ait=%d;apps=%zu;red=%s;text=%s;streamState=%d;streamError=%d;channelError=%d;service=%s;videoWindow=%s;debug=%d",
		VERSION_MAJOR, VERSION_MINOR, VERSION_MICRO,
		m_aitSignalsEnabled ? 1 : 0,
		m_applicationList.size(),
		m_redButtonApp.c_str(),
		m_textApp.c_str(),
		m_streamState,
		m_streamError,
		m_lastChannelError,
		m_currentService.toString().c_str(),
		getVideoWindowString().c_str(),
		m_debugEnabled ? 1 : 0);
	return std::string(buffer);
}

void eHbbtv::notifyAitInvalidated()
{
	clearApplications(true);
}

void eHbbtv::debugEmitPlayServiceRequest(const std::string &sref)
{
	debug("debugEmitPlayServiceRequest=%s", sref.c_str());
	playService(sref);
}

void eHbbtv::debugEmitPlayStreamRequest(const std::string &uri)
{
	debug("debugEmitPlayStreamRequest=%s", uri.c_str());
	playStream(uri);
}

void eHbbtv::debugEmitPauseStreamRequest()
{
	debug("debugEmitPauseStreamRequest");
	pauseStream();
}

void eHbbtv::debugEmitStopStreamRequest()
{
	debug("debugEmitStopStreamRequest");
	stopStream();
}

void eHbbtv::debugEmitSetVideoWindowRequest(int x, int y, int w, int h)
{
	if (x < 0)
		x = 0;
	if (y < 0)
		y = 0;
	if (w < 0)
		w = 0;
	if (h < 0)
		h = 0;
	debug("debugEmitSetVideoWindowRequest=%d,%d,%d,%d", x, y, w, h);
	setVideoWindow((unsigned int)x, (unsigned int)y, (unsigned int)w, (unsigned int)h);
}

void eHbbtv::debugEmitUnsetVideoWindowRequest()
{
	debug("debugEmitUnsetVideoWindowRequest");
	unsetVideoWindow();
}

void eHbbtv::debugEmitShow()
{
	debug("debugEmitShow");
	showCurrent();
}

void eHbbtv::debugEmitHide()
{
	debug("debugEmitHide");
	hideCurrent();
}

void eHbbtv::debugEmitCreateApplicationRequest(const std::string &uri)
{
	debug("debugEmitCreateApplicationRequest=%s", uri.c_str());
	createApplication(uri);
}

void eHbbtv::clearApplications(bool notify)
{
	const bool hadApplications = !m_applications.empty() || !m_applicationList.empty() || !m_redButtonApp.empty() || !m_textApp.empty();
	m_applications.clear();
	m_applicationList.clear();
	m_redButtonApp.clear();
	m_textApp.clear();
	eOipfApplication::clearRegistry();
	if (notify && hadApplications && m_aitSignalsEnabled)
		aitInvalidated();
}

std::string eHbbtv::makeApplicationId(int organisationId, int applicationId) const
{
	char buffer[64] = {0};
	snprintf(buffer, sizeof(buffer), "%08x.%04x", (unsigned int)organisationId, (unsigned int)applicationId);
	return std::string(buffer);
}

void eHbbtv::addApplicationFromInfo(const HbbTVApplicationInfo &info)
{
	if (info.m_HbbTVUrl.empty())
		return;

	const std::string id = makeApplicationId(info.m_OrgId, info.m_AppId);
	if (m_applications.find(id) != m_applications.end())
		return;
	const std::string name = info.m_ApplicationName.empty() ? std::string("HbbTV") : info.m_ApplicationName;
	const int controlCode = info.m_ControlCode < 0 ? -info.m_ControlCode : info.m_ControlCode;

	eOipfApplication application(id, name, info.m_HbbTVUrl, "", controlCode, 0, info.m_ProfileCode, info.m_OrgId, info.m_AppId);
	m_applications[id] = application;
	eOipfApplication::registerApplication(application);

	m_applicationList.push_back(std::pair<std::string, std::string>(name, id));
	debug("registered app id=%s org=%d app=%d name=%s url=%s control=%d profile=%d", id.c_str(), info.m_OrgId, info.m_AppId, name.c_str(), info.m_HbbTVUrl.c_str(), controlCode, info.m_ProfileCode);

	if (controlCode == eOipfApplication::CONTROL_CODE_AUTOSTART && m_redButtonApp.empty())
		m_redButtonApp = id;

	// Legacy OpenATV PMT data does not always expose APPLICATION_USAGE_DESCRIPTOR.
	// Keep a conservative text-app fallback by name until the parser extension is wired.
	if (m_textApp.empty() && (name.find("Text") != std::string::npos || name.find("text") != std::string::npos || name.find("Teletext") != std::string::npos))
		m_textApp = id;
}

void eHbbtv::updateApplicationsFromPMTHandler(eDVBServicePMTHandler *handler)
{
	if (!handler)
	{
		clearApplications();
		return;
	}

	std::vector<HbbTVApplicationInfo> infos;
	handler->getHbbTVApplicationInfos(infos);
	updateApplications(infos);
}

void eHbbtv::updateApplications(const std::vector<HbbTVApplicationInfo> &applications)
{
	if (applications.empty())
	{
		clearApplications();
		return;
	}

	clearApplications(false);
	debug("updating %zu HbbTV applications", applications.size());
	for (std::vector<HbbTVApplicationInfo>::const_iterator it = applications.begin(); it != applications.end(); ++it)
		addApplicationFromInfo(*it);

	if (m_redButtonApp.empty() && !m_applicationList.empty())
		m_redButtonApp = m_applicationList.front().second;

	emitApplicationSignals();
}

void eHbbtv::emitApplicationSignals()
{
	if (!m_aitSignalsEnabled)
		return;
	if (!m_redButtonApp.empty())
		redButtonAppplicationReady(m_redButtonApp.c_str());
	if (!m_textApp.empty())
		textApplicationReady(m_textApp.c_str());
}

void eHbbtv::updateFromNavigation(eNavigation *navigation)
{
	if (!navigation)
		return;

	eServiceReference service;
	navigation->getCurrentServiceReference(service);
	ePtr<iPlayableService> playableService;
	navigation->getCurrentService(playableService);
	setCurrentService(service, playableService);
}

const std::string eHbbtv::getCurrentServiceTriplet()
{
	return m_currentService.toString();
}

const eServiceReference &eHbbtv::getCurrentService()
{
	return m_currentService;
}

void eHbbtv::setCurrentService(const eServiceReference &service, const ePtr<iPlayableService> &playableService)
{
	const bool changed = m_currentService != service || m_playableService.operator->() != playableService.operator->();
	m_currentService = service;
	m_playableService = playableService;
	debug("current service=%s playable=%d", service.toString().c_str(), playableService ? 1 : 0);
	if (changed)
		clearApplications();
	currentServiceChanged();
}

void eHbbtv::setPlayableService(const ePtr<iPlayableService> &playableService)
{
	m_playableService = playableService;
}

void eHbbtv::playService(const std::string &sref)
{
	debug("playService request=%s", sref.c_str());
	playServiceRequest(sref.c_str());
}

bool eHbbtv::isLikelyServiceReference(const std::string &value) const
{
	if (value.empty())
		return false;
	if (value.find("://") != std::string::npos)
		return false;
	const size_t firstColon = value.find(':');
	if (firstColon == std::string::npos)
		return false;
	for (size_t i = 0; i < firstColon; ++i)
	{
		if (!isdigit((unsigned char)value[i]))
			return false;
	}
	return true;
}

bool eHbbtv::isLikelyUrl(const std::string &value) const
{
	return !value.compare(0, 7, "http://") || !value.compare(0, 8, "https://") || !value.compare(0, 7, "rtsp://") || !value.compare(0, 7, "rtmp://");
}

const std::string eHbbtv::normalizeStreamReference(const std::string &uri) const
{
	if (uri.empty() || isLikelyServiceReference(uri))
		return uri;
	if (isLikelyUrl(uri))
	{
		eServiceReference reference(eServiceReference::idServiceMP3, 0, 1);
		reference.setPath(uri);
		reference.setName("HbbTV");
		return reference.toString();
	}
	return uri;
}

void eHbbtv::playStream(const std::string &uri)
{
	const std::string sref = normalizeStreamReference(uri);
	setStreamState(STREAM_STATE_CONNECTING, STREAM_ERROR_CONNECTING);
	debug("playStream request input=%s normalized=%s", uri.c_str(), sref.c_str());
	playStreamRequest(sref.c_str());
}

void eHbbtv::pauseStream()
{
	debug("pauseStream request");
	pauseStreamRequest();
}

bool eHbbtv::seekStream(pts_t to)
{
	if (!m_playableService)
		return false;

	ePtr<iSeekableService> seek;
	if (m_playableService->seek(seek) || !seek)
		return false;
	return !seek->seekTo(to);
}

void eHbbtv::stopStream()
{
	debug("stopStream request");
	stopStreamRequest();
}

void eHbbtv::nextService()
{
	nextServiceRequest();
}

void eHbbtv::prevService()
{
	prevServiceRequest();
}

void eHbbtv::onCurrentServiceStop()
{
	m_playableService = 0;
	m_currentService = eServiceReference();
	clearApplications();
	setStreamState(STREAM_STATE_STOPPED, STREAM_ERROR_NONE);
	currentServiceChanged();
}

void eHbbtv::onCurrentServiceEvent(iPlayableService *playableService, int what)
{
	if (!m_playableService || playableService != m_playableService)
		return;

	if (what == iPlayableService::evEOF)
		setStreamState(STREAM_STATE_FINISHED, STREAM_ERROR_NONE);
	else if (what == iPlayableService::evStopped || what == iPlayableService::evEnd)
		setStreamState(STREAM_STATE_STOPPED, STREAM_ERROR_NONE);
	else if (what == iPlayableService::evGstreamerPlayStarted || what == iPlayableService::evStart)
		setStreamState(STREAM_STATE_PLAYING, STREAM_ERROR_NONE);
	else if (what == iPlayableService::evBuffering)
		setStreamState(STREAM_STATE_BUFFERING, STREAM_ERROR_NONE);
}

ePtr<iPlayableService> eHbbtv::getPlayableService()
{
	return m_playableService;
}

int eHbbtv::getPlayTime()
{
	if (!m_playableService)
		return 0;
	ePtr<iSeekableService> seek;
	if (m_playableService->seek(seek) || !seek)
		return 0;
	pts_t length = 0;
	if (!seek->getLength(length))
		return (int)(length / 90000);
	return 0;
}

int eHbbtv::getPlayPosition()
{
	if (!m_playableService)
		return 0;
	ePtr<iSeekableService> seek;
	if (m_playableService->seek(seek) || !seek)
		return 0;
	pts_t position = 0;
	if (!seek->getPlayPosition(position))
		return (int)(position / 90000);
	return 0;
}

void eHbbtv::setVolume(int volume)
{
	if (volume < 0)
		volume = 0;
	if (volume > 100)
		volume = 100;
	setVolumeRequest(volume);
}

const std::list<eServiceReference> eHbbtv::getServiceList()
{
	m_serviceReferences.clear();
	if (m_serviceList.empty())
	{
		if (m_currentService.valid())
			m_serviceReferences.push_back(m_currentService);
		return m_serviceReferences;
	}

	ePtr<iServiceHandler> serviceHandler;
	ePtr<iListableService> services;
	eServiceCenter::getInstance(serviceHandler);
	if (serviceHandler && !serviceHandler->list(eServiceReference(m_serviceList), services) && services)
	{
		std::list<eServiceReference> references;
		if (!services->getContent(references))
		{
			for (std::list<eServiceReference>::const_iterator it = references.begin(); it != references.end(); ++it)
			{
				if (it->valid() && !(it->flags & (eServiceReference::isDirectory | eServiceReference::isMarker | eServiceReference::isInvisible)))
					m_serviceReferences.push_back(*it);
			}
		}
	}
	return m_serviceReferences;
}

ePtr<eServiceEvent> eHbbtv::getEvent(int nownext)
{
	ePtr<eServiceEvent> event;
	if (!m_playableService)
		return event;
	ePtr<iServiceInformation> info;
	if (!m_playableService->info(info) && info)
		info->getEvent(event, nownext);
	return event;
}

void eHbbtv::setVideoWindow(unsigned int x, unsigned int y, unsigned int w, unsigned int h)
{
	m_videoWindow[0] = x;
	m_videoWindow[1] = y;
	m_videoWindow[2] = w;
	m_videoWindow[3] = h;
	m_videoWindowValid = true;
	debug("video window=%u,%u,%u,%u", x, y, w, h);
	setVideoWindowRequest((int)x, (int)y, (int)w, (int)h);
}

void eHbbtv::unsetVideoWindow()
{
	m_videoWindowValid = false;
	debug("unset video window");
	unsetVideoWindowRequest();
}

void eHbbtv::showCurrent()
{
	show();
}

void eHbbtv::hideCurrent()
{
	hide();
}

void eHbbtv::notifyChannelError(int error)
{
	m_lastChannelError = error;
	debug("channel error=%d", error);
	serviceChangeError(error);
}

void eHbbtv::createApplication(const std::string &uri)
{
	debug("createApplication request=%s", uri.c_str());
	createApplicationRequest(uri.c_str());
}
