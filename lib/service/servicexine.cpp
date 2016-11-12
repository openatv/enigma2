#define HAVE_XINE
#ifdef HAVE_XINE

/* yes, it's xine, not Xine. But eServicexine looks odd. */

#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <string>
#include <lib/service/servicexine.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>

static xine_t *xine; /* TODO: move this into a static class */

// eServiceFactoryXine

eServiceFactoryXine::eServiceFactoryXine()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->addServiceFactory(eServiceFactoryXine::id, this);

	m_service_info = new eStaticServiceXineInfo();
}

eServiceFactoryXine::~eServiceFactoryXine()
{
	ePtr<eServiceCenter> sc;

	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryXine::id);
}

DEFINE_REF(eServiceFactoryXine)

	// iServiceHandler
RESULT eServiceFactoryXine::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
		// check resources...
	ptr = new eServiceXine(ref.path.c_str());
	return 0;
}

RESULT eServiceFactoryXine::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryXine::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryXine::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_info;
	return 0;
}

RESULT eServiceFactoryXine::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
}


// eStaticServiceXineInfo


DEFINE_REF(eStaticServiceXineInfo)

eStaticServiceXineInfo::eStaticServiceXineInfo()
{
}

RESULT eStaticServiceXineInfo::getName(const eServiceReference &ref, std::string &name)
{
	size_t last = ref.path.rfind('/');
	if (last != std::string::npos)
		name = ref.path.substr(last+1);
	else
		name = ref.path;
	return 0;
}

int eStaticServiceXineInfo::getLength(const eServiceReference &ref)
{
	return -1;
}

// eServiceXine

eServiceXine::eServiceXine(const char *filename): m_filename(filename), m_pump(eApp, 1)
{
	m_state = stError;
	stream = 0;
	event_queue = 0;
	ao_port = 0;
	vo_port = 0;


//	if ((vo_port = xine_open_video_driver(xine, "fb", XINE_VISUAL_TYPE_FB, NULL)) == NULL)
	if ((vo_port = xine_open_video_driver(xine, "none", XINE_VISUAL_TYPE_NONE, NULL)) == NULL)
	{
		eWarning("cannot open xine video driver");
	}

	if ((ao_port = xine_open_audio_driver(xine , "alsa", NULL)) == NULL)
	{
		eWarning("cannot open xine audio driver");
	}
	stream = xine_stream_new(xine, ao_port, vo_port);
	event_queue = xine_event_new_queue(stream);
	xine_event_create_listener_thread(event_queue, eventListenerWrap, this);

//	CONNECT(m_pump.recv_msg, eServiceXine::gstPoll);
	m_state = stIdle;
}

eServiceXine::~eServiceXine()
{
	if (m_state == stRunning)
		stop();

	eDebug("close stream");
	if (stream)
		xine_close(stream);
	eDebug("dispose queue");
	if (event_queue)
		xine_event_dispose_queue(event_queue);
	eDebug("dispose stream");
	if (stream)
		xine_dispose(stream);
	eDebug("dispose ao_port");
	if (ao_port)
		xine_close_audio_driver(xine, ao_port);
	eDebug("dispose vo port");
	if (vo_port)
		xine_close_video_driver(xine, vo_port);
	eDebug("done.");
}

DEFINE_REF(eServiceXine);

void eServiceXine::eventListenerWrap(void *user_data, const xine_event_t *event)
{
	eServiceXine *e = (eServiceXine*)user_data;
	e->eventListener(event);
}

void eServiceXine::eventListener(const xine_event_t *event)
{
	eDebug("handle %d", event->type);
	switch(event->type) {
	case XINE_EVENT_UI_PLAYBACK_FINISHED:
		break;
	}
}

RESULT eServiceXine::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceXine::start()
{
	if (m_state == stError)
		return -1;

	ASSERT(m_state == stIdle);
	ASSERT(stream);

	if (!xine_open(stream, m_filename.c_str()))
	{
		eWarning("xine_open failed!");
		return -1;
	}

	if (!xine_play(stream, 0, 0))
	{
		eWarning("xine_play failed!");
		return -1;
	}

	m_state = stRunning;

	m_event(this, evStart);
	return 0;
}

RESULT eServiceXine::stop()
{
	if (m_state == stError)
		return -1;

	ASSERT(m_state != stIdle);
	ASSERT(stream);
	if (m_state == stStopped)
		return -1;
	printf("Xine: %s stop\n", m_filename.c_str());
	xine_stop(stream);
	// STOP
	m_state = stStopped;
	return 0;
}

RESULT eServiceXine::pause(ePtr<iPauseableService> &ptr)
{
	ptr=this;
	return 0;
}

RESULT eServiceXine::setSlowMotion(int ratio)
{
	return -1;
}

RESULT eServiceXine::setFastForward(int ratio)
{
	return -1;
}

		// iPausableService
RESULT eServiceXine::pause()
{
	//SPEED_PAUSE
	return 0;
}

RESULT eServiceXine::unpause()
{
	//SPEED_NORMAL
	// PLAY
	return 0;
}

	/* iSeekableService */
RESULT eServiceXine::seek(ePtr<iSeekableService> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eServiceXine::getLength(pts_t &pts)
{
	pts = -1;
	if (m_state == stError)
		return 1;
	ASSERT(stream);

	int pos_stream, pos_time, length_time;

	if (!xine_get_pos_length(stream, &pos_stream, &pos_time, &length_time))
	{
		eDebug("xine_get_pos_length failed!");
		return 1;
	}

	eDebug("length: %d ms", length_time);

	pts = length_time * 90;

	return 0;
}

RESULT eServiceXine::seekTo(pts_t to)
{
		// SEEK
	return 0;
}

RESULT eServiceXine::seekRelative(int direction, pts_t to)
{
		// SEEK RELATIVE
	return 0;
}

RESULT eServiceXine::getPlayPosition(pts_t &pts)
{
	pts = -1;
	if (m_state == stError)
		return 1;
	ASSERT(stream);

	int pos_stream, pos_time, length_time;

	if (!xine_get_pos_length(stream, &pos_stream, &pos_time, &length_time))
		return 1;

	eDebug("pos_time: %d", pos_time);
	pts = pos_time * 90;

		// GET POSITION
	return 0;
}

RESULT eServiceXine::setTrickmode(int trick)
{
		/* trickmode currently doesn't make any sense for us. */
	return -1;
}

RESULT eServiceXine::isCurrentlySeekable()
{
	return 3;
}

RESULT eServiceXine::info(ePtr<iServiceInformation>&i)
{
	i = this;
	return 0;
}

RESULT eServiceXine::getName(std::string &name)
{
	name = "xine File: " + m_filename;
	return 0;
}

int eServiceXine::getInfo(int w)
{
	switch (w)
	{
	case sTitle:
	case sArtist:
	case sAlbum:
	case sComment:
	case sTracknumber:
	case sGenre:
		return resIsString;

	default:
		return resNA;
	}
}

std::string eServiceXine::getInfoString(int w)
{
	return "";
}

class eXine
{
public:
	eXine()
	{
			/* this should be done once. */

		if(!xine_check_version(1, 1, 0))
		{
			int major, minor, sub;
			xine_get_version (&major, &minor, &sub);
			eWarning("Require xine library version 1.1.0, found %d.%d.%d.\n",
						major, minor,sub);
			return;
		} else {
			int major, minor, sub;
			eDebug("Built with xine library %d.%d.%d (%s)\n",
						 XINE_MAJOR_VERSION, XINE_MINOR_VERSION, XINE_SUB_VERSION, XINE_VERSION);

			xine_get_version (&major, &minor, &sub);

			eDebug("Found xine library version: %d.%d.%d (%s).\n",
						 major, minor, sub, xine_get_version_string());
		}

		xine = xine_new();
		xine_engine_set_param(xine, XINE_ENGINE_PARAM_VERBOSITY, 1);
		xine_init(xine);
	}
	~eXine()
	{
		if (xine)
			xine_exit(xine);
	}
};

eAutoInitP0<eXine> init_eXine(eAutoInitNumbers::service, "libxine");
eAutoInitPtr<eServiceFactoryXine> init_eServiceFactoryXine(eAutoInitNumbers::service+1, "eServiceFactoryXine");
#else
#warning xine not available
#endif
