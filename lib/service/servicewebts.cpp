#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string>
#include <sys/socket.h>
#include <netdb.h>
#include <signal.h>
#include <time.h>
#include "servicewebts.h"
#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/dvb/decoder.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/pmt.h>

#define MAX(a,b) ((a) > (b) ? (a) : (b))

/* TODO: Get rid of these statics */
static int VPID = 0;
static int PID_SET = 0;
static int APID = 0;
static int H264=0;

eServiceFactoryWebTS::eServiceFactoryWebTS()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		sc->addServiceFactory(eServiceFactoryWebTS::id, this, extensions);
	}

	m_service_info = new eStaticServiceWebTSInfo();
}

eServiceFactoryWebTS::~eServiceFactoryWebTS()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryWebTS::id);
}

DEFINE_REF(eServiceFactoryWebTS)

// iServiceHandler
RESULT eServiceFactoryWebTS::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
	ptr = new eServiceWebTS(ref);
	return 0;
}

RESULT eServiceFactoryWebTS::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryWebTS::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryWebTS::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_info;
	return -1;
}

RESULT eServiceFactoryWebTS::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
}

/*
 * eStaticServiceWebTSInfo
 * required to in order to display name in bouquets instead of n/a
 */
DEFINE_REF(eStaticServiceWebTSInfo)

eStaticServiceWebTSInfo::eStaticServiceWebTSInfo()
{
}

RESULT eStaticServiceWebTSInfo::getName(const eServiceReference &ref, std::string &name)
{
	name = ref.name;
	if (name.empty())
	{
		name = ref.path;
		size_t n = name.rfind('/');
		if (n != std::string::npos)
			name = name.substr(n + 1);
	}
	return 0;
}

int eStaticServiceWebTSInfo::getLength(const eServiceReference &ref)
{
	return -1;
}

int eStaticServiceWebTSInfo::getInfo(const eServiceReference &ref, int w)
{
	switch (w)
	{
	case iServiceInformation::sTimeCreate:
	{
		struct stat s;
		if (!stat(ref.path.c_str(), &s))
			return s.st_mtime;
	}
	break;
	case iServiceInformation::sFileSize:
	{
		struct stat s;
		if (!stat(ref.path.c_str(), &s))
			return s.st_size;
	}
	break;
	}
	return iServiceInformation::resNA;
}

long long eStaticServiceWebTSInfo::getFileSize(const eServiceReference &ref)
{
	struct stat s;
	if (!stat(ref.path.c_str(), &s))
		return s.st_size;
	return 0;
}

RESULT eStaticServiceWebTSInfo::getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &evt, time_t start_time)
{
	evt = 0;
	return -1;
}

/********************************************************************/
/* TSAudioInfoWeb                                            */
/********************************************************************/
DEFINE_REF(TSAudioInfoWeb);

void TSAudioInfoWeb::addAudio(int pid, std::string lang, std::string desc, int type) {
	StreamInfo as;
	as.description = desc;
	as.language = lang;
	as.pid = pid;
	as.type = type;
	audioStreams.push_back(as);
}


/********************************************************************/
/* eServiceWebTS                                                       */
/********************************************************************/

eServiceWebTS::eServiceWebTS(const eServiceReference &url): m_reference(url), m_pump(eApp, 1)
{
	eDebug("ServiceWebTS construct!");
	m_filename = url.path.c_str();
	m_vpid = url.getData(0) == 0 ? 0x44 : url.getData(0);
	m_apid = url.getData(1) == 0 ? 0x45 : url.getData(1);
	m_audioInfo = 0;
	m_destfd = -1;
}

eServiceWebTS::~eServiceWebTS()
{
	eDebug("ServiceWebTS destruct!");
	stop();
}

DEFINE_REF(eServiceWebTS);

static size_t crop(char *buf)
{
	size_t len = strlen(buf) - 1;
	while (len > 0 && (buf[len] == '\r' || buf[len] == '\n')) {
		buf[len--] = '\0';
	}
	return len;
}

static int getline(char** pbuffer, size_t* pbufsize, int fd)
{
	size_t i = 0;
	int rc;
	while (true) {
		if (i >= *pbufsize) {
			char *newbuf = (char*)realloc(*pbuffer, (*pbufsize)+1024);
			if (newbuf == NULL)
				return -ENOMEM;
			*pbuffer = newbuf;
			*pbufsize = (*pbufsize)+1024;
		}
		rc = ::read(fd, (*pbuffer)+i, 1);
		if (rc <= 0 || (*pbuffer)[i] == '\n')
		{
			(*pbuffer)[i] = '\0';
			return rc <= 0 ? -1 : i;
		}
		if ((*pbuffer)[i] != '\r') i++;
	}
}



int eServiceWebTS::openHttpConnection(std::string url)
{
	std::string host;
	int port = 80;
	std::string uri;

	int slash = url.find("/", 7);
	if (slash > 0) {
		host = url.substr(7, slash-7);
		uri = url.substr(slash, url.length()-slash);
	} else {
		host = url.substr(7, url.length()-7);
		uri = "";
	}
	int dp = host.find(":");
	if (dp == 0) {
		port = atoi(host.substr(1, host.length()-1).c_str());
		host = "localhost";
	} else if (dp > 0) {
		port = atoi(host.substr(dp+1, host.length()-dp-1).c_str());
		host = host.substr(0, dp);
	}

	struct hostent* h = gethostbyname(host.c_str());
	if (h == NULL || h->h_addr_list == NULL)
		return -1;
	int fd = socket(PF_INET, SOCK_STREAM, 0);
	if (fd == -1)
		return -1;

	struct sockaddr_in addr;
	addr.sin_family = AF_INET;
	addr.sin_addr.s_addr = *((in_addr_t*)h->h_addr_list[0]);
	addr.sin_port = htons(port);

	eDebug("connecting to %s", url.c_str());

	if (connect(fd, (sockaddr*)&addr, sizeof(addr)) == -1) {
		std::string msg = "connect failed for: " + url;
		eDebug(msg.c_str());
		return -1;
	}

	std::string request = "GET ";
	request.append(uri).append(" HTTP/1.1\r\n");
	request.append("Host: ").append(host).append("\r\n");
	request.append("Accept: */*\r\n");
	request.append("Connection: close\r\n");
	request.append("\r\n");
	//eDebug(request.c_str());
	write(fd, request.c_str(), request.length());

	int rc;
	size_t buflen = 1000;
	char* linebuf = (char*)malloc(1000);

	rc = getline(&linebuf, &buflen, fd);
	//eDebug("RECV(%d): %s", rc, linebuf);
	if (rc <= 0)
	{
		close(fd);
		free(linebuf);
		return -1;
	}

	char proto[100];
	int statuscode = 0;
	char statusmsg[100];
	rc = sscanf(linebuf, "%99s %d %99s", proto, &statuscode, statusmsg);
	if (rc != 3 || statuscode != 200) {
		eDebug("wrong response: \"200 OK\" expected.\n %d --- %d",rc,statuscode);
		free(linebuf);
		close(fd);
		return -1;
	}
	eDebug("proto=%s, code=%d, msg=%s", proto, statuscode, statusmsg);
	while (rc > 0)
	{
		rc = getline(&linebuf, &buflen, fd);
		//eDebug("RECV(%d): %s", rc, linebuf);
	}
	free(linebuf);

	return fd;
}

RESULT eServiceWebTS::connectEvent(const sigc::slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceWebTS::start()
{
	ePtr<eDVBResourceManager> rmgr;
	eDVBResourceManager::getInstance(rmgr);
	eDVBChannel dvbChannel(rmgr, 0);
	if (dvbChannel.getDemux(m_decodedemux, iDVBChannel::capDecode) != 0) {
		eDebug("Cannot allocate decode-demux");
		return -1;
	}
	if (m_decodedemux->getMPEGDecoder(m_decoder) != 0) {
		eDebug("Cannot allocate MPEGDecoder");
		return -1;
	}
	if (m_destfd == -1)
	{
		m_destfd = m_decodedemux->openDVR(O_WRONLY);
		if (m_destfd < 0)
		{
			eDebug("openDVR failed!");
			return -1;
		}
	}
	//m_decoder->setVideoPID(m_vpid, eDVBVideo::MPEG2);
	//m_decoder->setAudioPID(m_apid, eDVBAudio::aMPEG);
	m_streamthread = new eStreamThreadWeb();
	CONNECT(m_streamthread->m_event, eServiceWebTS::recv_event);
	//m_decoder->freeze(0);
	//m_decoder->preroll();
	if (unpause() != 0)
		return -1;
	//m_event(this, evStart);
	return 0;
}

RESULT eServiceWebTS::stop()
{
	if (m_destfd >= 0)
	{
		::close(m_destfd);
		m_destfd = -1;
	}
	printf("TS: %s stop\n", m_filename.c_str());
	m_streamthread->stop();
	m_decodedemux->flush();
	m_audioInfo = 0;
	APID = 0;
	VPID = 0;
	PID_SET = 0;
	H264 = 0;
	return 0;
}

void eServiceWebTS::recv_event(int evt)
{
	eDebug("eServiceWebTS::recv_event: %d", evt);
	switch (evt) {
	case eStreamThreadWeb::evtEOS:
		m_decodedemux->flush();
		m_event((iPlayableService*)this, evEOF);
		break;
	case eStreamThreadWeb::evtReadError:
	case eStreamThreadWeb::evtWriteError:
		m_decoder->pause();
		m_event((iPlayableService*)this, evEOF);
		break;
	case eStreamThreadWeb::evtSOS:
		m_event((iPlayableService*)this, evSOF);
		break;
	case eStreamThreadWeb::evtStreamInfo:
		if (VPID != 0 && PID_SET == 0 && APID != 0)
		{
			PID_SET = 1;
			m_decodedemux->flush();
			if (H264)
				m_decoder->setVideoPID(VPID, eDVBVideo::MPEG4_H264);
			else
				m_decoder->setVideoPID(VPID, eDVBVideo::MPEG2);
			m_decoder->setAudioPID(APID, eDVBAudio::aMPEG);
			m_decoder->pause();
			m_event(this, evStart);
			m_decoder->play();
			
		}
		bool wasnull = !m_audioInfo;
		m_streamthread->getAudioInfo(m_audioInfo);
		//if (m_audioInfo)
		//	eDebug("[ServiceWebTS] %d audiostreams found", m_audioInfo->audioStreams.size());
		if (m_audioInfo && wasnull) {
			eDebug("[ServiceWebTS] %d audiostreams found", m_audioInfo->audioStreams.size());
			int sel = getCurrentTrack();
			if (sel < 0)
				selectTrack(0);
			else if (m_audioInfo->audioStreams[sel].type != eDVBAudio::aMPEG)
				selectTrack(sel);
		}
		break;
	}
}

RESULT eServiceWebTS::pause(ePtr<iPauseableService> &ptr)
{
	ptr = this;
	return 0;
}

// iPausableService
RESULT eServiceWebTS::pause()
{
	m_streamthread->stop();
	m_decoder->pause();
	return 0;
}

RESULT eServiceWebTS::unpause()
{
	if (!m_streamthread->running())
	{
		int is_streaming = !strncmp(m_filename.c_str(), "http://", 7);
		int srcfd = -1;
		if (is_streaming)
			srcfd = openHttpConnection(m_filename);
		else
			srcfd = ::open(m_filename.c_str(), O_RDONLY);
		if (srcfd < 0) {
			eDebug("Cannot open source stream: %s", m_filename.c_str());
			return 1;
		}
		//m_decodedemux->flush();
		m_streamthread->start(srcfd, m_destfd);
		//m_decoder->unfreeze();
	}
	else
		eDebug("unpause but thread already running!");
	return 0;
}

// iSeekableService
RESULT eServiceWebTS::seek(ePtr<iSeekableService> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eServiceWebTS::getLength(pts_t &pts)
{
	return 0;
}

RESULT eServiceWebTS::seekTo(pts_t to)
{
	return 0;
}

RESULT eServiceWebTS::seekRelative(int direction, pts_t to)
{
	return 0;
}

RESULT eServiceWebTS::getPlayPosition(pts_t &pts)
{
	return 0;
}

RESULT eServiceWebTS::setTrickmode(int trick)
{
	return -1;
}

RESULT eServiceWebTS::isCurrentlySeekable()
{
	return 1;
}

RESULT eServiceWebTS::info(ePtr<iServiceInformation>&i)
{
	i = this;
	return 0;
}

RESULT eServiceWebTS::getName(std::string &name)
{
	name = m_reference.name;
	if (name.empty())
	{
		name = m_reference.path;
		size_t n = name.rfind('/');
		if (n != std::string::npos)
			name = name.substr(n + 1);
	}
	return 0;
}

int eServiceWebTS::getInfo(int w)
{
	return resNA;
}

std::string eServiceWebTS::getInfoString(int w)
{
	switch (w)
	{
	case sProvider:
		return "IPTV";
	case sServiceref:
	{
		eServiceReference ref(m_reference);
		ref.type = eServiceFactoryWebTS::id;
		ref.path.clear();
		return ref.toString();
	}
	default:
		break;
	}
	return "";
}

int eServiceWebTS::getNumberOfTracks() {
	if (m_audioInfo)
		return (int)m_audioInfo->audioStreams.size();
	else
		return 0;
}

RESULT eServiceWebTS::selectTrack(unsigned int i) {
	if (m_audioInfo) {
		m_apid = m_audioInfo->audioStreams[i].pid;
		eDebug("[ServiceWebTS] audio track %d PID 0x%02x type %d\n", i, m_apid, m_audioInfo->audioStreams[i].type);
		m_decoder->setAudioPID(m_apid, m_audioInfo->audioStreams[i].type);
		m_decoder->set();
		return 0;
	} else {
		return -1;
	}
}

RESULT eServiceWebTS::getTrackInfo(struct iAudioTrackInfo &info, unsigned int n) {
	if (m_audioInfo) {
		info.m_pid = m_audioInfo->audioStreams[n].pid;
		info.m_description = m_audioInfo->audioStreams[n].description;
		info.m_language = m_audioInfo->audioStreams[n].language;
		return 0;
	} else {
		return -1;
	}
}

int eServiceWebTS::getCurrentTrack() {
	if (m_audioInfo) {
		for (size_t i = 0; i < m_audioInfo->audioStreams.size(); i++) {
			if (m_apid == m_audioInfo->audioStreams[i].pid) {
				return i;
			}
		}
	}
	return -1;
}

/********************************************************************/
/* eStreamThreadWeb                                                       */
/********************************************************************/

DEFINE_REF(eStreamThreadWeb)

eStreamThreadWeb::eStreamThreadWeb(): m_messagepump(eApp, 0) {
	CONNECT(m_messagepump.recv_msg, eStreamThreadWeb::recvEvent);
	m_running = false;
}

eStreamThreadWeb::~eStreamThreadWeb() {
}

void eStreamThreadWeb::start(int srcfd, int destfd) {
	m_srcfd = srcfd;
	m_destfd = destfd;
	m_stop = false;
	m_audioInfo = 0;
	run(IOPRIO_CLASS_RT);
}

void eStreamThreadWeb::stop() {
	m_stop = true;
	kill();
}

void eStreamThreadWeb::recvEvent(const int &evt)
{
	m_event(evt);
}

RESULT eStreamThreadWeb::getAudioInfo(ePtr<TSAudioInfoWeb> &ptr)
{
	ptr = m_audioInfo;
	return 0;
}

#define REGISTRATION_DESCRIPTOR 5
#define LANGUAGE_DESCRIPTOR 10

std::string eStreamThreadWeb::getDescriptor(unsigned char buf[], int buflen, int type)
{
	int desc_len;
	while (buflen > 1) {
		desc_len = buf[1];
		if (buf[0] == type) {
			char str[21];
			if (desc_len > 20) desc_len = 20;
			strncpy(str, (char*)buf+2, desc_len);
			str[desc_len] = '\0';
			return std::string(str);
		} else {
			buflen -= desc_len+2;
			buf += desc_len+2;
		}
	}
	return "";
}

bool eStreamThreadWeb::scanAudioInfo(unsigned char buf[], int len)
{
	if (len < 1880)
		return false;

	int adaptfield, offset;
	unsigned char pmt[1188];
	int pmtsize = 0;

	for (int a=0; a < len - 188*4; a++) {
		if ( buf[a] != 0x47 || buf[a + 188] != 0x47 || buf[a + 376] != 0x47 )
			continue; // TS Header

		if ((0x40 & buf[a + 1]) == 0) // start
			continue;

		if ((0xC0 & buf[a + 3]) != 0) // scrambling
			continue;

		adaptfield = (0x30 & buf[a + 3]) >> 4;

		if ((adaptfield & 1) == 0) // adapt - no payload
			continue;

		offset = adaptfield == 3 ? 1 + (0xFF & buf[a + 4]) : 0; //adaptlength

		if (buf[a + offset + 4] != 0 || buf[a + offset + 5] != 2 || (0xF0 & buf[a + offset + 6]) != 0xB0)
		{
			a += 187;
			continue;
		}

		memcpy(pmt + pmtsize, buf + a + 4 + offset, 184 - offset);
		pmtsize += 184 - offset;

		if (pmtsize >= 1000)
			break;
	}

	if (pmtsize == 0) return false;

	int pmtlen = (0x0F & pmt[2]) << 8 | (0xFF & pmt[3]);
	std::string lang;
	std::string pd_type;
	ePtr<TSAudioInfoWeb> ainfo = new TSAudioInfoWeb();

	for (int b=8; b < pmtlen-4 && b < pmtsize-6; b++)
	{
		if ( (0xe0 & pmt[b+1]) != 0xe0 )
			continue;

		int pid = (0x1F & pmt[b+1])<<8 | (0xFF & pmt[b+2]);
		switch(pmt[b])
		{
		case 1:
		case 2: // MPEG Video
			//addVideo(pid, "MPEG2");
			H264 = 0;
			if (VPID == 0)
				VPID= pid;
			break;

		case 0x1B: // H.264 Video
			//addVideo(pid, "H.264");
			H264 = 1;
			if (VPID == 0)
				VPID= pid;
			break;
		case 3:
		case 4: // MPEG Audio
			if (APID == 0)
				APID =pid;
			lang = getDescriptor(pmt+b+5, pmt[b+4], LANGUAGE_DESCRIPTOR);
			ainfo->addAudio(pid, lang, "MPEG", eDVBAudio::aMPEG);
			break;

		case 0x80:
		case 0x81:  //private data of AC3 in ATSC
		case 0x82:
		case 0x83:
		case 6:
			lang = getDescriptor(pmt+b+5, pmt[b+4], LANGUAGE_DESCRIPTOR);
			pd_type = getDescriptor(pmt+b+5, pmt[b+4], REGISTRATION_DESCRIPTOR);
			//if (pd_type == "AC-3")
			// dirty dirty :-) Aber es funktioniert...
			if (lang.length() != 0)
			{
				ainfo->addAudio(pid, lang, "AC-3", eDVBAudio::aAC3);
				if (APID == 0)
					APID =pid;
			}
			break;
		case 0x0f:
			if (APID == 0)
				APID =pid;
			lang = getDescriptor(pmt+b+5, pmt[b+4], LANGUAGE_DESCRIPTOR);
			ainfo->addAudio(pid, lang, "AAC", eDVBAudio::aAAC);
			break;
		case 0x11:
			if (APID == 0)
				APID =pid;
			lang = getDescriptor(pmt+b+5, pmt[b+4], LANGUAGE_DESCRIPTOR);
			ainfo->addAudio(pid, lang, "AACHE", eDVBAudio::aAACHE);
			break;
		}
		b += 4 + pmt[b+4];
	}
	if (ainfo->audioStreams.size() > 0) {
		m_audioInfo = ainfo;
		return true;
	} else {
		return false;
	}
}

void eStreamThreadWeb::thread() {
	const int bufsize = 40000;
	unsigned char buf[bufsize];
	bool eof = false;
	fd_set rfds;
	fd_set wfds;
	struct timeval timeout;
	int rc,r,w,maxfd;
	time_t next_scantime = 0;
	bool sosSend = false;
	m_running = true;

	r = w = 0;
	hasStarted();
	eDebug("eStreamThreadWeb started");
	while (!m_stop) {
		pthread_testcancel();
		FD_ZERO(&rfds);
		FD_ZERO(&wfds);
		maxfd = 0;
		timeout.tv_sec = 1;
		timeout.tv_usec = 0;
		if (r < bufsize) {
			FD_SET(m_srcfd, &rfds);
			maxfd = MAX(maxfd, m_srcfd);
		}
		if (w < r) {
			FD_SET(m_destfd, &wfds);
			maxfd = MAX(maxfd, m_destfd);
		}
		rc = select(maxfd+1, &rfds, &wfds, NULL, &timeout);
		if (rc == 0) {
			eDebug("eStreamThreadWeb::thread: timeout!");
			continue;
		}
		if (rc < 0) {
			eDebug("eStreamThreadWeb::thread: error in select (%d)", errno);
			break;
		}
		if (FD_ISSET(m_srcfd, &rfds)) {
			rc = ::read(m_srcfd, buf+r, bufsize - r);
			if (rc < 0) {
				eDebug("eStreamThreadWeb::thread: error in read (%d)", errno);
				m_messagepump.send(evtReadError);
				break;
			} else if (rc == 0) {
				eof = true;
			} else {
				if (!sosSend) {
					sosSend = true;
					m_messagepump.send(evtSOS);
				}
				r += rc;
				if (r == bufsize) eDebug("eStreamThreadWeb::thread: buffer full");
			}
		}
		if (FD_ISSET(m_destfd, &wfds) && (w < r) && ((r > bufsize/4) || eof)) {
			rc = ::write(m_destfd, buf+w, r-w);
			if (rc < 0) {
				eDebug("eStreamThreadWeb::thread: error in write (%d)", errno);
				m_messagepump.send(evtWriteError);
				break;
			}
			w += rc;
			//eDebug("eStreamThreadWeb::thread: buffer r=%d w=%d",r,w);
			if (w == r) {
				if (time(0) >= next_scantime) {
					if (scanAudioInfo(buf, r)) {
						m_messagepump.send(evtStreamInfo);
						next_scantime = time(0) + 1;
					}
				}
				w = r = 0;
			}
		}
		if (eof && (r==w)) {
			m_messagepump.send(evtEOS);
			break;
		}
	}
	eDebug("eStreamThreadWeb end");
}

void eStreamThreadWeb::thread_finished() {
	if (m_srcfd >= 0)
		::close(m_srcfd);
	eDebug("eStreamThreadWeb closed");
	m_running = false;
}

eAutoInitPtr<eServiceFactoryWebTS> init_eServiceFactoryWebTS(eAutoInitNumbers::service+1, "eServiceFactoryWebTS");
