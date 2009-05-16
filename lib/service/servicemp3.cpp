#ifdef HAVE_GSTREAMER

	/* note: this requires gstreamer 0.10.x and a big list of plugins. */
	/* it's currently hardcoded to use a big-endian alsasink as sink. */
#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <string>
#include <lib/service/servicemp3.h>
#include <lib/service/service.h>
#include <lib/components/file_eraser.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <gst/gst.h>
#include <gst/pbutils/missing-plugins.h>
#include <sys/stat.h>
/* for subtitles */
#include <lib/gui/esubtitle.h>

#ifndef GST_SEEK_FLAG_SKIP
#warning Compiling for legacy gstreamer, things will break
#define GST_SEEK_FLAG_SKIP 0
#define GST_TAG_HOMEPAGE ""
#endif

// eServiceFactoryMP3

eServiceFactoryMP3::eServiceFactoryMP3()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		extensions.push_back("mp2");
		extensions.push_back("mp3");
		extensions.push_back("ogg");
		extensions.push_back("mpg");
		extensions.push_back("vob");
		extensions.push_back("wav");
		extensions.push_back("wave");
		extensions.push_back("mkv");
		extensions.push_back("avi");
		extensions.push_back("divx");
		extensions.push_back("dat");
		extensions.push_back("flac");
		extensions.push_back("mp4");
		extensions.push_back("mov");
		extensions.push_back("m4a");
		sc->addServiceFactory(eServiceFactoryMP3::id, this, extensions);
	}

	m_service_info = new eStaticServiceMP3Info();
}

eServiceFactoryMP3::~eServiceFactoryMP3()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
		sc->removeServiceFactory(eServiceFactoryMP3::id);
}

DEFINE_REF(eServiceFactoryMP3)

	// iServiceHandler
RESULT eServiceFactoryMP3::play(const eServiceReference &ref, ePtr<iPlayableService> &ptr)
{
		// check resources...
	ptr = new eServiceMP3(ref.path.c_str(),ref.getName().c_str());
	return 0;
}

RESULT eServiceFactoryMP3::record(const eServiceReference &ref, ePtr<iRecordableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryMP3::list(const eServiceReference &, ePtr<iListableService> &ptr)
{
	ptr=0;
	return -1;
}

RESULT eServiceFactoryMP3::info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr)
{
	ptr = m_service_info;
	return 0;
}

class eMP3ServiceOfflineOperations: public iServiceOfflineOperations
{
	DECLARE_REF(eMP3ServiceOfflineOperations);
	eServiceReference m_ref;
public:
	eMP3ServiceOfflineOperations(const eServiceReference &ref);
	
	RESULT deleteFromDisk(int simulate);
	RESULT getListOfFilenames(std::list<std::string> &);
};

DEFINE_REF(eMP3ServiceOfflineOperations);

eMP3ServiceOfflineOperations::eMP3ServiceOfflineOperations(const eServiceReference &ref): m_ref((const eServiceReference&)ref)
{
}

RESULT eMP3ServiceOfflineOperations::deleteFromDisk(int simulate)
{
	if (simulate)
		return 0;
	else
	{
		std::list<std::string> res;
		if (getListOfFilenames(res))
			return -1;
		
		eBackgroundFileEraser *eraser = eBackgroundFileEraser::getInstance();
		if (!eraser)
			eDebug("FATAL !! can't get background file eraser");
		
		for (std::list<std::string>::iterator i(res.begin()); i != res.end(); ++i)
		{
			eDebug("Removing %s...", i->c_str());
			if (eraser)
				eraser->erase(i->c_str());
			else
				::unlink(i->c_str());
		}
		
		return 0;
	}
}

RESULT eMP3ServiceOfflineOperations::getListOfFilenames(std::list<std::string> &res)
{
	res.clear();
	res.push_back(m_ref.path);
	return 0;
}


RESULT eServiceFactoryMP3::offlineOperations(const eServiceReference &ref, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = new eMP3ServiceOfflineOperations(ref);
	return 0;
}

// eStaticServiceMP3Info


// eStaticServiceMP3Info is seperated from eServiceMP3 to give information
// about unopened files.

// probably eServiceMP3 should use this class as well, and eStaticServiceMP3Info
// should have a database backend where ID3-files etc. are cached.
// this would allow listing the mp3 database based on certain filters.

DEFINE_REF(eStaticServiceMP3Info)

eStaticServiceMP3Info::eStaticServiceMP3Info()
{
}

RESULT eStaticServiceMP3Info::getName(const eServiceReference &ref, std::string &name)
{
	if ( ref.name.length() )
		name = ref.name;
	else
	{
		size_t last = ref.path.rfind('/');
		if (last != std::string::npos)
			name = ref.path.substr(last+1);
		else
			name = ref.path;
	}
	return 0;
}

int eStaticServiceMP3Info::getLength(const eServiceReference &ref)
{
	return -1;
}

// eServiceMP3

eServiceMP3::eServiceMP3(const char *filename, const char *title): m_filename(filename), m_title(title), m_pump(eApp, 1)
{
	m_seekTimeout = eTimer::create(eApp);
	m_subtitle_sync_timer = eTimer::create(eApp);
	m_stream_tags = 0;
	m_currentAudioStream = 0;
	m_currentSubtitleStream = 0;
	m_subtitle_widget = 0;
	m_currentTrickRatio = 0;
	CONNECT(m_seekTimeout->timeout, eServiceMP3::seekTimeoutCB);
	CONNECT(m_subtitle_sync_timer->timeout, eServiceMP3::pushSubtitles);
	CONNECT(m_pump.recv_msg, eServiceMP3::gstPoll);
	m_aspect = m_width = m_height = m_framerate = m_progressive = -1;

	m_state = stIdle;
	eDebug("eServiceMP3::construct!");
	
	const char *ext = strrchr(filename, '.');
	if (!ext)
		ext = filename;

	sourceStream sourceinfo;
	sourceinfo.is_video = FALSE;
	sourceinfo.audiotype = atUnknown;
	if ( (strcasecmp(ext, ".mpeg") && strcasecmp(ext, ".mpg") && strcasecmp(ext, ".vob") && strcasecmp(ext, ".bin") && strcasecmp(ext, ".dat") ) == 0 )
	{
		sourceinfo.containertype = ctMPEGPS;
		sourceinfo.is_video = TRUE;
	}
	else if ( strcasecmp(ext, ".ts") == 0 )
	{
		sourceinfo.containertype = ctMPEGTS;
		sourceinfo.is_video = TRUE;
	}
	else if ( strcasecmp(ext, ".mkv") == 0 )
	{
		sourceinfo.containertype = ctMKV;
		sourceinfo.is_video = TRUE;
	}
	else if ( strcasecmp(ext, ".avi") == 0 || strcasecmp(ext, ".divx") == 0)
	{
		sourceinfo.containertype = ctAVI;
		sourceinfo.is_video = TRUE;
	}
	else if ( strcasecmp(ext, ".mp4") == 0 || strcasecmp(ext, ".mov") == 0)
	{
		sourceinfo.containertype = ctMP4;
		sourceinfo.is_video = TRUE;
	}
	else if ( strcasecmp(ext, ".m4a") == 0 )
	{
		sourceinfo.containertype = ctMP4;
		sourceinfo.audiotype = atAAC;
	}
	else if ( strcasecmp(ext, ".mp3") == 0 )
		sourceinfo.audiotype = atMP3;
	else if ( (strncmp(filename, "/autofs/", 8) || strncmp(filename+strlen(filename)-13, "/track-", 7) || strcasecmp(ext, ".wav")) == 0 )
		sourceinfo.containertype = ctCDA;
	if ( strcasecmp(ext, ".dat") == 0 )
	{
		sourceinfo.containertype = ctVCD;
		sourceinfo.is_video = TRUE;
	}
	if ( (strncmp(filename, "http://", 7)) == 0 || (strncmp(filename, "udp://", 6)) == 0 || (strncmp(filename, "rtsp://", 7)) == 0 )
		sourceinfo.is_streaming = TRUE;

	gchar *uri;

	if ( sourceinfo.is_streaming )
	{
		uri = g_strdup_printf ("%s", filename);
	}
	else if ( sourceinfo.containertype == ctCDA )
	{
		int i_track = atoi(filename+18);
		uri = g_strdup_printf ("cdda://%i", i_track);
	}
	else if ( sourceinfo.containertype == ctVCD )
	{
		int fd = open(filename,O_RDONLY);
		char tmp[128*1024];
		int ret = read(fd, tmp, 128*1024);
		close(fd);
		if ( ret == -1 ) // this is a "REAL" VCD
			uri = g_strdup_printf ("vcd://");
		else
			uri = g_strdup_printf ("file://%s", filename);
	}
	else

		uri = g_strdup_printf ("file://%s", filename);

	eDebug("eServiceMP3::playbin2 uri=%s", uri);

	m_gst_playbin = gst_element_factory_make("playbin2", "playbin");
	if (!m_gst_playbin)
		m_error_message = "failed to create GStreamer pipeline!\n";

	g_object_set (G_OBJECT (m_gst_playbin), "uri", uri, NULL);

	int flags = 0x47; // ( == GST_PLAY_FLAG_VIDEO | GST_PLAY_FLAG_AUDIO | GST_PLAY_FLAG_NATIVE_VIDEO | GST_PLAY_FLAG_TEXT )
	g_object_set (G_OBJECT (m_gst_playbin), "flags", flags, NULL);

	g_free(uri);

	GstElement *subsink = gst_element_factory_make("appsink", "subtitle_sink");
	if (!subsink)
		eDebug("eServiceMP3::sorry, can't play: missing gst-plugin-appsink");
	else
	{
		g_object_set (G_OBJECT (subsink), "emit-signals", TRUE, NULL);
		g_signal_connect (subsink, "new-buffer", G_CALLBACK (gstCBsubtitleAvail), this);
		g_object_set (G_OBJECT (m_gst_playbin), "text-sink", subsink, NULL);
	}

	if ( m_gst_playbin )
	{
		gst_bus_set_sync_handler(gst_pipeline_get_bus (GST_PIPELINE (m_gst_playbin)), gstBusSyncHandler, this);
		char srt_filename[strlen(filename)+1];
		strncpy(srt_filename,filename,strlen(filename)-3);
		srt_filename[strlen(filename)-3]='\0';
		strcat(srt_filename, "srt");
		struct stat buffer;
		if (stat(srt_filename, &buffer) == 0)
		{
			std::string suburi = "file://" + (std::string)srt_filename;
			eDebug("eServiceMP3::subtitle uri: %s",suburi.c_str());
			g_object_set (G_OBJECT (m_gst_playbin), "suburi", suburi.c_str(), NULL);
			subtitleStream subs;
			subs.type = stSRT;
			subs.language_code = std::string("und");
			m_subtitleStreams.push_back(subs);
		}
	} else
	{
		m_event((iPlayableService*)this, evUser+12);

		if (m_gst_playbin)
			gst_object_unref(GST_OBJECT(m_gst_playbin));

		eDebug("eServiceMP3::sorry, can't play: %s",m_error_message.c_str());
		m_gst_playbin = 0;
	}

	gst_element_set_state (m_gst_playbin, GST_STATE_PLAYING);
}

eServiceMP3::~eServiceMP3()
{
	delete m_subtitle_widget;
	if (m_state == stRunning)
		stop();
	
	if (m_stream_tags)
		gst_tag_list_free(m_stream_tags);
	
	if (m_gst_playbin)
	{
		gst_object_unref (GST_OBJECT (m_gst_playbin));
		eDebug("eServiceMP3::destruct!");
	}
}

DEFINE_REF(eServiceMP3);	

RESULT eServiceMP3::connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iPlayableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceMP3::start()
{
	ASSERT(m_state == stIdle);
	
	m_state = stRunning;
	if (m_gst_playbin)
	{
		eDebug("eServiceMP3::starting pipeline");
		gst_element_set_state (m_gst_playbin, GST_STATE_PLAYING);
	}
	m_event(this, evStart);
	return 0;
}

RESULT eServiceMP3::stop()
{
	ASSERT(m_state != stIdle);
	if (m_state == stStopped)
		return -1;
	eDebug("eServiceMP3::stop %s", m_filename.c_str());
	gst_element_set_state(m_gst_playbin, GST_STATE_NULL);
	m_state = stStopped;
	return 0;
}

RESULT eServiceMP3::setTarget(int target)
{
	return -1;
}

RESULT eServiceMP3::pause(ePtr<iPauseableService> &ptr)
{
	ptr=this;
	return 0;
}

RESULT eServiceMP3::setSlowMotion(int ratio)
{
	if (!ratio)
		return 0;
	eDebug("eServiceMP3::setSlowMotion ratio=%f",1/(float)ratio);
	return trickSeek(1/(float)ratio);
}

RESULT eServiceMP3::setFastForward(int ratio)
{
	eDebug("eServiceMP3::setFastForward ratio=%i",ratio);
	return trickSeek(ratio);
}

void eServiceMP3::seekTimeoutCB()
{
	pts_t ppos, len;
	getPlayPosition(ppos);
	getLength(len);
	ppos += 90000*m_currentTrickRatio;
	
	if (ppos < 0)
	{
		ppos = 0;
		m_seekTimeout->stop();
	}
	if (ppos > len)
	{
		ppos = 0;
		stop();
		m_seekTimeout->stop();
		return;
	}
	seekTo(ppos);
}

		// iPausableService
RESULT eServiceMP3::pause()
{
	if (!m_gst_playbin || m_state != stRunning)
		return -1;
	GstStateChangeReturn res = gst_element_set_state(m_gst_playbin, GST_STATE_PAUSED);
	if (res == GST_STATE_CHANGE_ASYNC)
	{
		pts_t ppos;
		getPlayPosition(ppos);
		seekTo(ppos);
	}
	return 0;
}

RESULT eServiceMP3::unpause()
{
	m_subtitle_pages.clear();
	if (!m_gst_playbin || m_state != stRunning)
		return -1;

	GstStateChangeReturn res;
	res = gst_element_set_state(m_gst_playbin, GST_STATE_PLAYING);
	return 0;
}

	/* iSeekableService */
RESULT eServiceMP3::seek(ePtr<iSeekableService> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eServiceMP3::getLength(pts_t &pts)
{
	if (!m_gst_playbin)
		return -1;
	if (m_state != stRunning)
		return -1;
	
	GstFormat fmt = GST_FORMAT_TIME;
	gint64 len;
	
	if (!gst_element_query_duration(m_gst_playbin, &fmt, &len))
		return -1;
		/* len is in nanoseconds. we have 90 000 pts per second. */
	
	pts = len / 11111;
	return 0;
}

RESULT eServiceMP3::seekTo(pts_t to)
{
	m_subtitle_pages.clear();

	if (!m_gst_playbin)
		return -1;

		/* convert pts to nanoseconds */
	gint64 time_nanoseconds = to * 11111LL;
	if (!gst_element_seek (m_gst_playbin, 1.0, GST_FORMAT_TIME, GST_SEEK_FLAG_FLUSH,
		GST_SEEK_TYPE_SET, time_nanoseconds,
		GST_SEEK_TYPE_NONE, GST_CLOCK_TIME_NONE))
	{
		eDebug("eServiceMP3::seekTo failed");
		return -1;
	}
	return 0;
}

RESULT eServiceMP3::trickSeek(gdouble ratio)
{
	if (!m_gst_playbin)
		return -1;
	if (!ratio)
		return seekRelative(0, 0);

	GstEvent *s_event;
	GstSeekFlags flags;
	flags = GST_SEEK_FLAG_NONE;
	flags |= GstSeekFlags (GST_SEEK_FLAG_FLUSH);
// 	flags |= GstSeekFlags (GST_SEEK_FLAG_ACCURATE);
	flags |= GstSeekFlags (GST_SEEK_FLAG_KEY_UNIT);
// 	flags |= GstSeekFlags (GST_SEEK_FLAG_SEGMENT);
// 	flags |= GstSeekFlags (GST_SEEK_FLAG_SKIP);

	GstFormat fmt = GST_FORMAT_TIME;
	gint64 pos, len;
	gst_element_query_duration(m_gst_playbin, &fmt, &len);
	gst_element_query_position(m_gst_playbin, &fmt, &pos);

	if ( ratio >= 0 )
	{
		s_event = gst_event_new_seek (ratio, GST_FORMAT_TIME, flags, GST_SEEK_TYPE_SET, pos, GST_SEEK_TYPE_SET, len);

		eDebug("eServiceMP3::trickSeek with rate %lf to %" GST_TIME_FORMAT " ", ratio, GST_TIME_ARGS (pos));
	}
	else
	{
		s_event = gst_event_new_seek (ratio, GST_FORMAT_TIME, GST_SEEK_FLAG_SKIP|GST_SEEK_FLAG_FLUSH, GST_SEEK_TYPE_NONE, -1, GST_SEEK_TYPE_NONE, -1);
	}

	if (!gst_element_send_event ( GST_ELEMENT (m_gst_playbin), s_event))
	{
		eDebug("eServiceMP3::trickSeek failed");
		return -1;
	}

	return 0;
}


RESULT eServiceMP3::seekRelative(int direction, pts_t to)
{
	if (!m_gst_playbin)
		return -1;

	pts_t ppos;
	getPlayPosition(ppos);
	ppos += to * direction;
	if (ppos < 0)
		ppos = 0;
	seekTo(ppos);
	
	return 0;
}

RESULT eServiceMP3::getPlayPosition(pts_t &pts)
{
	if (!m_gst_playbin)
		return -1;
	if (m_state != stRunning)
		return -1;

	GstFormat fmt = GST_FORMAT_TIME;
	gint64 len;
	
	if (!gst_element_query_position(m_gst_playbin, &fmt, &len))
		return -1;

		/* len is in nanoseconds. we have 90 000 pts per second. */
	pts = len / 11111;
	return 0;
}

RESULT eServiceMP3::setTrickmode(int trick)
{
		/* trickmode is not yet supported by our dvbmediasinks. */
	return -1;
}

RESULT eServiceMP3::isCurrentlySeekable()
{
	return 1;
}

RESULT eServiceMP3::info(ePtr<iServiceInformation>&i)
{
	i = this;
	return 0;
}

RESULT eServiceMP3::getName(std::string &name)
{
	if (m_title.empty())
	{
		name = m_filename;
		size_t n = name.rfind('/');
		if (n != std::string::npos)
			name = name.substr(n + 1);
	}
	else
		name = m_title;
	return 0;
}


int eServiceMP3::getInfo(int w)
{
	const gchar *tag = 0;

	switch (w)
	{
	case sVideoHeight: return m_height;
	case sVideoWidth: return m_width;
	case sFrameRate: return m_framerate;
	case sProgressive: return m_progressive;
	case sAspect: return m_aspect;
	case sTagTitle:
	case sTagArtist:
	case sTagAlbum:
	case sTagTitleSortname:
	case sTagArtistSortname:
	case sTagAlbumSortname:
	case sTagDate:
	case sTagComposer:
	case sTagGenre:
	case sTagComment:
	case sTagExtendedComment:
	case sTagLocation:
	case sTagHomepage:
	case sTagDescription:
	case sTagVersion:
	case sTagISRC:
	case sTagOrganization:
	case sTagCopyright:
	case sTagCopyrightURI:
	case sTagContact:
	case sTagLicense:
	case sTagLicenseURI:
	case sTagCodec:
	case sTagAudioCodec:
	case sTagVideoCodec:
	case sTagEncoder:
	case sTagLanguageCode:
	case sTagKeywords:
	case sTagChannelMode:
	case sUser+12:
		return resIsString;
	case sTagTrackGain:
	case sTagTrackPeak:
	case sTagAlbumGain:
	case sTagAlbumPeak:
	case sTagReferenceLevel:
	case sTagBeatsPerMinute:
	case sTagImage:
	case sTagPreviewImage:
	case sTagAttachment:
		return resIsPyObject;
	case sTagTrackNumber:
		tag = GST_TAG_TRACK_NUMBER;
		break;
	case sTagTrackCount:
		tag = GST_TAG_TRACK_COUNT;
		break;
	case sTagAlbumVolumeNumber:
		tag = GST_TAG_ALBUM_VOLUME_NUMBER;
		break;
	case sTagAlbumVolumeCount:
		tag = GST_TAG_ALBUM_VOLUME_COUNT;
		break;
	case sTagBitrate:
		tag = GST_TAG_BITRATE;
		break;
	case sTagNominalBitrate:
		tag = GST_TAG_NOMINAL_BITRATE;
		break;
	case sTagMinimumBitrate:
		tag = GST_TAG_MINIMUM_BITRATE;
		break;
	case sTagMaximumBitrate:
		tag = GST_TAG_MAXIMUM_BITRATE;
		break;
	case sTagSerial:
		tag = GST_TAG_SERIAL;
		break;
	case sTagEncoderVersion:
		tag = GST_TAG_ENCODER_VERSION;
		break;
	case sTagCRC:
		tag = "has-crc";
		break;
	default:
		return resNA;
	}

	if (!m_stream_tags || !tag)
		return 0;
	
	guint value;
	if (gst_tag_list_get_uint(m_stream_tags, tag, &value))
		return (int) value;

	return 0;
}

std::string eServiceMP3::getInfoString(int w)
{
	if ( !m_stream_tags )
		return "";
	const gchar *tag = 0;
	switch (w)
	{
	case sTagTitle:
		tag = GST_TAG_TITLE;
		break;
	case sTagArtist:
		tag = GST_TAG_ARTIST;
		break;
	case sTagAlbum:
		tag = GST_TAG_ALBUM;
		break;
	case sTagTitleSortname:
		tag = GST_TAG_TITLE_SORTNAME;
		break;
	case sTagArtistSortname:
		tag = GST_TAG_ARTIST_SORTNAME;
		break;
	case sTagAlbumSortname:
		tag = GST_TAG_ALBUM_SORTNAME;
		break;
	case sTagDate:
		GDate *date;
		if (gst_tag_list_get_date(m_stream_tags, GST_TAG_DATE, &date))
		{
			gchar res[5];
 			g_date_strftime (res, sizeof(res), "%Y-%M-%D", date); 
			return (std::string)res;
		}
		break;
	case sTagComposer:
		tag = GST_TAG_COMPOSER;
		break;
	case sTagGenre:
		tag = GST_TAG_GENRE;
		break;
	case sTagComment:
		tag = GST_TAG_COMMENT;
		break;
	case sTagExtendedComment:
		tag = GST_TAG_EXTENDED_COMMENT;
		break;
	case sTagLocation:
		tag = GST_TAG_LOCATION;
		break;
	case sTagHomepage:
		tag = GST_TAG_HOMEPAGE;
		break;
	case sTagDescription:
		tag = GST_TAG_DESCRIPTION;
		break;
	case sTagVersion:
		tag = GST_TAG_VERSION;
		break;
	case sTagISRC:
		tag = GST_TAG_ISRC;
		break;
	case sTagOrganization:
		tag = GST_TAG_ORGANIZATION;
		break;
	case sTagCopyright:
		tag = GST_TAG_COPYRIGHT;
		break;
	case sTagCopyrightURI:
		tag = GST_TAG_COPYRIGHT_URI;
		break;
	case sTagContact:
		tag = GST_TAG_CONTACT;
		break;
	case sTagLicense:
		tag = GST_TAG_LICENSE;
		break;
	case sTagLicenseURI:
		tag = GST_TAG_LICENSE_URI;
		break;
	case sTagCodec:
		tag = GST_TAG_CODEC;
		break;
	case sTagAudioCodec:
		tag = GST_TAG_AUDIO_CODEC;
		break;
	case sTagVideoCodec:
		tag = GST_TAG_VIDEO_CODEC;
		break;
	case sTagEncoder:
		tag = GST_TAG_ENCODER;
		break;
	case sTagLanguageCode:
		tag = GST_TAG_LANGUAGE_CODE;
		break;
	case sTagKeywords:
		tag = GST_TAG_KEYWORDS;
		break;
	case sTagChannelMode:
		tag = "channel-mode";
		break;

	case sUser+12:
		return m_error_message;
	default:
		return "";
	}
	if ( !tag )
		return "";
	gchar *value;
	if (gst_tag_list_get_string(m_stream_tags, tag, &value))
	{
		std::string res = value;
		g_free(value);
		return res;
	}
	return "";
}

PyObject *eServiceMP3::getInfoObject(int w)
{
	const gchar *tag = 0;
	bool isBuffer = false;
	switch (w)
	{
		case sTagTrackGain:
			tag = GST_TAG_TRACK_GAIN;
			break;
		case sTagTrackPeak:
			tag = GST_TAG_TRACK_PEAK;
			break;
		case sTagAlbumGain:
			tag = GST_TAG_ALBUM_GAIN;
			break;
		case sTagAlbumPeak:
			tag = GST_TAG_ALBUM_PEAK;
			break;
		case sTagReferenceLevel:
			tag = GST_TAG_REFERENCE_LEVEL;
			break;
		case sTagBeatsPerMinute:
			tag = GST_TAG_BEATS_PER_MINUTE;
			break;
		case sTagImage:
			tag = GST_TAG_IMAGE;
			isBuffer = true;
			break;
		case sTagPreviewImage:
			tag = GST_TAG_PREVIEW_IMAGE;
			isBuffer = true;
			break;
		case sTagAttachment:
			tag = GST_TAG_ATTACHMENT;
			isBuffer = true;
			break;
		default:
			break;
	}
	gdouble value;
	if ( !tag || !m_stream_tags )
		value = 0.0;
	PyObject *pyValue;
	if ( isBuffer )
	{
		const GValue *gv_buffer = gst_tag_list_get_value_index(m_stream_tags, tag, 0);
		if ( gv_buffer )
		{
			GstBuffer *buffer;
			buffer = gst_value_get_buffer (gv_buffer);
			pyValue = PyBuffer_FromMemory(GST_BUFFER_DATA(buffer), GST_BUFFER_SIZE(buffer));
		}
	}
	else
	{
		gst_tag_list_get_double(m_stream_tags, tag, &value);
		pyValue = PyFloat_FromDouble(value);
	}

	return pyValue;
}

RESULT eServiceMP3::audioChannel(ePtr<iAudioChannelSelection> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eServiceMP3::audioTracks(ePtr<iAudioTrackSelection> &ptr)
{
	ptr = this;
	return 0;
}

RESULT eServiceMP3::subtitle(ePtr<iSubtitleOutput> &ptr)
{
	ptr = this;
	return 0;
}

int eServiceMP3::getNumberOfTracks()
{
 	return m_audioStreams.size();
}

int eServiceMP3::getCurrentTrack()
{
	return m_currentAudioStream;
}

RESULT eServiceMP3::selectTrack(unsigned int i)
{
	int ret = selectAudioStream(i);
	/* flush */
	pts_t ppos;
	getPlayPosition(ppos);
	seekTo(ppos);

	return ret;
}

int eServiceMP3::selectAudioStream(int i)
{
	int current_audio;
	g_object_set (G_OBJECT (m_gst_playbin), "current-audio", i, NULL);
	g_object_get (G_OBJECT (m_gst_playbin), "current-audio", &current_audio, NULL);
	if ( current_audio == i )
	{
		eDebug ("eServiceMP3::switched to audio stream %i", current_audio);
		m_currentAudioStream = i;
		return 0;
	}
	return -1;
}

int eServiceMP3::getCurrentChannel()
{
	return STEREO;
}

RESULT eServiceMP3::selectChannel(int i)
{
	eDebug("eServiceMP3::selectChannel(%i)",i);
	return 0;
}

RESULT eServiceMP3::getTrackInfo(struct iAudioTrackInfo &info, unsigned int i)
{
 	if (i >= m_audioStreams.size())
		return -2;
		info.m_description = m_audioStreams[i].codec;
/*	if (m_audioStreams[i].type == atMPEG)
		info.m_description = "MPEG";
	else if (m_audioStreams[i].type == atMP3)
		info.m_description = "MP3";
	else if (m_audioStreams[i].type == atAC3)
		info.m_description = "AC3";
	else if (m_audioStreams[i].type == atAAC)
		info.m_description = "AAC";
	else if (m_audioStreams[i].type == atDTS)
		info.m_description = "DTS";
	else if (m_audioStreams[i].type == atPCM)
		info.m_description = "PCM";
	else if (m_audioStreams[i].type == atOGG)
		info.m_description = "OGG";
	else if (m_audioStreams[i].type == atFLAC)
		info.m_description = "FLAC";
	else
		info.m_description = "???";*/
	if (info.m_language.empty())
		info.m_language = m_audioStreams[i].language_code;
	return 0;
}

void eServiceMP3::gstBusCall(GstBus *bus, GstMessage *msg)
{
	if (!msg)
		return;
	gchar *sourceName;
	GstObject *source;

	source = GST_MESSAGE_SRC(msg);
	sourceName = gst_object_get_name(source);
#if 0
	if (gst_message_get_structure(msg))
	{
		gchar *string = gst_structure_to_string(gst_message_get_structure(msg));
		eDebug("eServiceMP3::gst_message from %s: %s", sourceName, string);
		g_free(string);
	}
	else
		eDebug("eServiceMP3::gst_message from %s: %s (without structure)", sourceName, GST_MESSAGE_TYPE_NAME(msg));
#endif
	if ( GST_MESSAGE_TYPE (msg) == GST_MESSAGE_STATE_CHANGED )
		return;
	switch (GST_MESSAGE_TYPE (msg))
	{
		case GST_MESSAGE_EOS:
			m_event((iPlayableService*)this, evEOF);
			break;
		case GST_MESSAGE_ERROR:
		{
			gchar *debug;
			GError *err;
	
			gst_message_parse_error (msg, &err, &debug);
			g_free (debug);
			eWarning("Gstreamer error: %s (%i) from %s", err->message, err->code, sourceName );
			if ( err->domain == GST_STREAM_ERROR )
			{
				if ( err->code == GST_STREAM_ERROR_CODEC_NOT_FOUND )
				{
					if ( g_strrstr(sourceName, "videosink") )
						m_event((iPlayableService*)this, evUser+11);
					else if ( g_strrstr(sourceName, "audiosink") )
						m_event((iPlayableService*)this, evUser+10);
				}
			}
			g_error_free(err);
			break;
		}
		case GST_MESSAGE_INFO:
		{
			gchar *debug;
			GError *inf;
	
			gst_message_parse_info (msg, &inf, &debug);
			g_free (debug);
			if ( inf->domain == GST_STREAM_ERROR && inf->code == GST_STREAM_ERROR_DECODE )
			{
				if ( g_strrstr(sourceName, "videosink") )
					m_event((iPlayableService*)this, evUser+14);
			}
			g_error_free(inf);
			break;
		}
		case GST_MESSAGE_TAG:
		{
			GstTagList *tags, *result;
			gst_message_parse_tag(msg, &tags);
	
			result = gst_tag_list_merge(m_stream_tags, tags, GST_TAG_MERGE_PREPEND);
			if (result)
			{
				if (m_stream_tags)
					gst_tag_list_free(m_stream_tags);
				m_stream_tags = result;
			}
	
			const GValue *gv_image = gst_tag_list_get_value_index(tags, GST_TAG_IMAGE, 0);
			if ( gv_image )
			{
				GstBuffer *buf_image;
				buf_image = gst_value_get_buffer (gv_image);
				int fd = open("/tmp/.id3coverart", O_CREAT|O_WRONLY|O_TRUNC, 0644);
				int ret = write(fd, GST_BUFFER_DATA(buf_image), GST_BUFFER_SIZE(buf_image));
				close(fd);
				eDebug("eServiceMP3::/tmp/.id3coverart %d bytes written ", ret);
				m_event((iPlayableService*)this, evUser+13);
			}
	
			gst_tag_list_free(tags);
			m_event((iPlayableService*)this, evUpdatedInfo);
			break;
		}
		case GST_MESSAGE_ASYNC_DONE:
		{
			GstTagList *tags;
			gint i, active_idx, n_video = 0, n_audio = 0, n_text = 0;

			g_object_get (m_gst_playbin, "n-video", &n_video, NULL);
			g_object_get (m_gst_playbin, "n-audio", &n_audio, NULL);
			g_object_get (m_gst_playbin, "n-text", &n_text, NULL);

			eDebug("eServiceMP3::async-done - %d video, %d audio, %d subtitle", n_video, n_audio, n_text);

			active_idx = 0;

			m_audioStreams.clear();
			m_subtitleStreams.clear();

			for (i = 0; i < n_audio; i++)
			{
				audioStream audio;
				gchar *g_codec, *g_lang;
				GstPad* pad = 0;
				g_signal_emit_by_name (m_gst_playbin, "get-audio-pad", i, &pad);
				GstCaps* caps = gst_pad_get_negotiated_caps(pad);
				GstStructure* str = gst_caps_get_structure(caps, 0);
gchar *g_type;
g_type = gst_structure_get_name(str);
eDebug("AUDIO STRUCT=%s", g_type);
				audio.type = gstCheckAudioPad(str);
				g_codec = g_strdup(g_type);
				g_lang = g_strdup_printf ("und");
				g_signal_emit_by_name (m_gst_playbin, "get-audio-tags", i, &tags);
				if ( tags && gst_is_tag_list(tags) )
				{
					gst_tag_list_get_string(tags, GST_TAG_AUDIO_CODEC, &g_codec);
					gst_tag_list_get_string(tags, GST_TAG_LANGUAGE_CODE, &g_lang);
				}
				audio.language_code = std::string(g_lang);
				audio.codec = std::string(g_codec);
				eDebug("eServiceMP3::audio stream=%i codec=%s language=%s", i, g_codec, g_lang);
				m_audioStreams.push_back(audio);
				g_free (g_lang);
				g_free (g_codec);
			}

			for (i = 0; i < n_text; i++)
			{	
				gchar *g_lang;
// 				gchar *g_type;
// 				GstPad* pad = 0;
// 				g_signal_emit_by_name (m_gst_playbin, "get-text-pad", i, &pad);
// 				GstCaps* caps = gst_pad_get_negotiated_caps(pad);
// 				GstStructure* str = gst_caps_get_structure(caps, 0);
// 				g_type = gst_structure_get_name(str);
// 				g_signal_emit_by_name (m_gst_playbin, "get-text-tags", i, &tags);
				subtitleStream subs;
				subs.type = stPlainText;
				g_lang = g_strdup_printf ("und");
				if ( tags && gst_is_tag_list(tags) )
					gst_tag_list_get_string(tags, GST_TAG_LANGUAGE_CODE, &g_lang);
				subs.language_code = std::string(g_lang);
				eDebug("eServiceMP3::subtitle stream=%i language=%s"/* type=%s*/, i, g_lang/*, g_type*/);
				m_subtitleStreams.push_back(subs);
				g_free (g_lang);
// 				g_free (g_type);
			}
		}
		case GST_MESSAGE_ELEMENT:
		{
			if ( gst_is_missing_plugin_message(msg) )
			{
				gchar *description = gst_missing_plugin_message_get_description(msg);
				if ( description )
				{
					m_error_message = "GStreamer plugin " + (std::string)description + " not available!\n";
					g_free(description);
					m_event((iPlayableService*)this, evUser+12);
				}
			}
			else if (const GstStructure *msgstruct = gst_message_get_structure(msg))
			{
				const gchar *eventname = gst_structure_get_name(msgstruct);
				if ( eventname )
				{
					if (!strcmp(eventname, "eventSizeChanged") || !strcmp(eventname, "eventSizeAvail"))
					{
						gst_structure_get_int (msgstruct, "aspect_ratio", &m_aspect);
						gst_structure_get_int (msgstruct, "width", &m_width);
						gst_structure_get_int (msgstruct, "height", &m_height);
						if (strstr(eventname, "Changed"))
							m_event((iPlayableService*)this, evVideoSizeChanged);
					}
					else if (!strcmp(eventname, "eventFrameRateChanged") || !strcmp(eventname, "eventFrameRateAvail"))
					{
						gst_structure_get_int (msgstruct, "frame_rate", &m_framerate);
						if (strstr(eventname, "Changed"))
							m_event((iPlayableService*)this, evVideoFramerateChanged);
					}
					else if (!strcmp(eventname, "eventProgressiveChanged") || !strcmp(eventname, "eventProgressiveAvail"))
					{
						gst_structure_get_int (msgstruct, "progressive", &m_progressive);
						if (strstr(eventname, "Changed"))
							m_event((iPlayableService*)this, evVideoProgressiveChanged);
					}
				}
			}
		}
		default:
			break;
	}
	g_free (sourceName);
}

GstBusSyncReply eServiceMP3::gstBusSyncHandler(GstBus *bus, GstMessage *message, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	_this->m_pump.send(1);
		/* wake */
	return GST_BUS_PASS;
}

audiotype_t eServiceMP3::gstCheckAudioPad(GstStructure* structure)
{
	if (!structure)
		return atUnknown;

	if ( gst_structure_has_name (structure, "audio/mpeg"))
	{
    		gint mpegversion, layer = -1;
		if (!gst_structure_get_int (structure, "mpegversion", &mpegversion))
			return atUnknown;

		switch (mpegversion) {
      			case 1:
				{
					gst_structure_get_int (structure, "layer", &layer);
					if ( layer == 3 )
						return atMP3;
					else
						return atMPEG;
					break;
				}
			case 2:
				return atAAC;
			case 4:
				return atAAC;
			default:
				return atUnknown;
		}
	}

	else if ( gst_structure_has_name (structure, "audio/x-ac3") || gst_structure_has_name (structure, "audio/ac3") )
		return atAC3;
	else if ( gst_structure_has_name (structure, "audio/x-dts") || gst_structure_has_name (structure, "audio/dts") )
		return atDTS;
	else if ( gst_structure_has_name (structure, "audio/x-raw-int") )
		return atPCM;

	return atUnknown;
}

void eServiceMP3::gstPoll(const int&)
{
		/* ok, we have a serious problem here. gstBusSyncHandler sends 
		   us the wakup signal, but likely before it was posted.
		   the usleep, an EVIL HACK (DON'T DO THAT!!!) works around this.
		   
		   I need to understand the API a bit more to make this work 
		   proplerly. */
	usleep(1);
	
	GstBus *bus = gst_pipeline_get_bus (GST_PIPELINE (m_gst_playbin));
	GstMessage *message;
	while ((message = gst_bus_pop (bus)))
	{
		gstBusCall(bus, message);
		gst_message_unref (message);
	}
}

eAutoInitPtr<eServiceFactoryMP3> init_eServiceFactoryMP3(eAutoInitNumbers::service+1, "eServiceFactoryMP3");

void eServiceMP3::gstCBsubtitleAvail(GstElement *appsink, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	GstBuffer *buffer;
	g_signal_emit_by_name (appsink, "pull-buffer", &buffer);
	if (buffer)
	{
		GstFormat fmt = GST_FORMAT_TIME;
		gint64 buf_pos = GST_BUFFER_TIMESTAMP(buffer);
		gint64 duration_ns = GST_BUFFER_DURATION(buffer);
		size_t len = GST_BUFFER_SIZE(buffer);
		unsigned char line[len+1];
		memcpy(line, GST_BUFFER_DATA(buffer), len);
		line[len] = 0;
// 		eDebug("got new subtitle @ buf_pos = %lld ns (in pts=%lld): '%s' ", buf_pos, buf_pos/11111, line);
		if ( _this->m_subtitle_widget )
		{
			ePangoSubtitlePage page;
			gRGB rgbcol(0xD0,0xD0,0xD0);
			page.m_elements.push_back(ePangoSubtitlePageElement(rgbcol, (const char*)line));
			page.show_pts = buf_pos / 11111L;
			page.m_timeout = duration_ns / 1000000;
			_this->m_subtitle_pages.push_back(page);
			_this->pushSubtitles();
		}
	}
}

void eServiceMP3::pushSubtitles()
{
	ePangoSubtitlePage page;
	GstClockTime base_time;
	pts_t running_pts;
	GstElement *appsink = gst_bin_get_by_name(GST_BIN(m_gst_playbin),"subtitle_sink");
	GstClock *clock;
	clock = gst_element_get_clock (appsink);
	while ( !m_subtitle_pages.empty() )
	{
		page = m_subtitle_pages.front();

		base_time = gst_element_get_base_time (appsink);
		running_pts = ( gst_clock_get_time (clock) - base_time ) / 11111L;
		gint64 diff_ms = ( page.show_pts - running_pts ) / 90;
// 		eDebug("eServiceMP3::pushSubtitles show_pts = %lld  running_pts = %lld  diff = %lld", page.show_pts, running_pts, diff_ms);
		if ( diff_ms > 20 )
		{
// 			eDebug("m_subtitle_sync_timer->start(%lld,1)", diff_ms);
			m_subtitle_sync_timer->start(diff_ms, 1);
			break;
		}
		else
		{
			m_subtitle_widget->setPage(page);
			m_subtitle_pages.pop_front();
		}
	} ;

	gst_object_unref (clock);
}

RESULT eServiceMP3::enableSubtitles(eWidget *parent, ePyObject tuple)
{
	ePyObject entry;
	int tuplesize = PyTuple_Size(tuple);
	int pid, type;
	gint text_pid = 0;

	if (!PyTuple_Check(tuple))
		goto error_out;
	if (tuplesize < 1)
		goto error_out;
	entry = PyTuple_GET_ITEM(tuple, 1);
	if (!PyInt_Check(entry))
		goto error_out;
	pid = PyInt_AsLong(entry);
	entry = PyTuple_GET_ITEM(tuple, 2);
	if (!PyInt_Check(entry))
		goto error_out;
	type = PyInt_AsLong(entry);

	g_object_set (G_OBJECT (m_gst_playbin), "current-text", pid, NULL);
 	m_currentSubtitleStream = pid;

	m_subtitle_widget = new eSubtitleWidget(parent);
	m_subtitle_widget->resize(parent->size()); /* full size */

	g_object_get (G_OBJECT (m_gst_playbin), "current-text", &text_pid, NULL);

	eDebug ("eServiceMP3::switched to subtitle stream %i", text_pid);
	m_subtitle_pages.clear();

	return 0;

error_out:
	eDebug("eServiceMP3::enableSubtitles needs a tuple as 2nd argument!\n"
		"for gst subtitles (2, subtitle_stream_count, subtitle_type)");
	return -1;
}

RESULT eServiceMP3::disableSubtitles(eWidget *parent)
{
	eDebug("eServiceMP3::disableSubtitles");
	m_subtitle_pages.clear();
	delete m_subtitle_widget;
	m_subtitle_widget = 0;
	return 0;
}

PyObject *eServiceMP3::getCachedSubtitle()
{
	eDebug("eServiceMP3::getCachedSubtitle");
	Py_RETURN_NONE;
}

PyObject *eServiceMP3::getSubtitleList()
{
	eDebug("eServiceMP3::getSubtitleList");

	ePyObject l = PyList_New(0);
	int stream_count[sizeof(subtype_t)];
	for ( unsigned int i = 0; i < sizeof(subtype_t); i++ )
		stream_count[i] = 0;

	for (std::vector<subtitleStream>::iterator IterSubtitleStream(m_subtitleStreams.begin()); IterSubtitleStream != m_subtitleStreams.end(); ++IterSubtitleStream)
	{
		subtype_t type = IterSubtitleStream->type;
		ePyObject tuple = PyTuple_New(5);
		PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(2));
		PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(stream_count[type]));
		PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(int(type)));
		PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(0));
		PyTuple_SET_ITEM(tuple, 4, PyString_FromString((IterSubtitleStream->language_code).c_str()));
		PyList_Append(l, tuple);
		Py_DECREF(tuple);
		stream_count[type]++;
	}
	return l;
}

#else
#warning gstreamer not available, not building media player
#endif
