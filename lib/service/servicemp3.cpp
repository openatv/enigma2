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

// eServiceFactoryMP3

eServiceFactoryMP3::eServiceFactoryMP3()
{
	ePtr<eServiceCenter> sc;
	
	eServiceCenter::getPrivInstance(sc);
	if (sc)
	{
		std::list<std::string> extensions;
		extensions.push_back("mp3");
		extensions.push_back("ogg");
		extensions.push_back("mpg");
		extensions.push_back("vob");
		extensions.push_back("wav");
		extensions.push_back("wave");
		extensions.push_back("mkv");
		extensions.push_back("avi");
		extensions.push_back("dat");
		extensions.push_back("flac");
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
	ptr = new eServiceMP3(ref.path.c_str());
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
	size_t last = ref.path.rfind('/');
	if (last != std::string::npos)
		name = ref.path.substr(last+1);
	else
		name = ref.path;
	return 0;
}

int eStaticServiceMP3Info::getLength(const eServiceReference &ref)
{
	return -1;
}

// eServiceMP3

eServiceMP3::eServiceMP3(const char *filename): m_filename(filename), m_pump(eApp, 1)
{
	m_stream_tags = 0;
	m_audioStreams.clear();
	m_subtitleStreams.clear();
	m_currentAudioStream = 0;
	m_currentSubtitleStream = 0;
	m_subtitle_widget = 0;
	m_currentTrickRatio = 0;
	CONNECT(m_seekTimeout.timeout, eServiceMP3::seekTimeoutCB);
	CONNECT(m_pump.recv_msg, eServiceMP3::gstPoll);
	GstElement *source = 0;
	
	GstElement *decoder = 0, *conv = 0, *flt = 0, *sink = 0; /* for audio */
	
	GstElement *audio = 0, *switch_audio = 0, *queue_audio = 0, *video = 0, *queue_video = 0, *videodemux = 0;
	
	m_state = stIdle;
	eDebug("SERVICEMP3 construct!");
	
		/* FIXME: currently, decodebin isn't possible for 
		   video streams. in that case, make a manual pipeline. */

	const char *ext = strrchr(filename, '.');
	if (!ext)
		ext = filename;

	int is_mpeg_ps = !(strcasecmp(ext, ".mpeg") && strcasecmp(ext, ".mpg") && strcasecmp(ext, ".vob") && strcasecmp(ext, ".bin") && strcasecmp(ext, ".dat"));
	int is_mpeg_ts = !strcasecmp(ext, ".ts");
	int is_matroska = !strcasecmp(ext, ".mkv");
	int is_avi = !strcasecmp(ext, ".avi");
	int is_mp3 = !strcasecmp(ext, ".mp3"); /* force mp3 instead of decodebin */
	int is_video = is_mpeg_ps || is_mpeg_ts || is_matroska || is_avi;
	int is_streaming = !strncmp(filename, "http://", 7);
	int is_AudioCD = !(strncmp(filename, "/autofs/", 8) || strncmp(filename+strlen(filename)-13, "/track-", 7) || strcasecmp(ext, ".wav"));
	int is_VCD = !strcasecmp(ext, ".dat");
	
	eDebug("filename: %s, is_mpeg_ps: %d, is_mpeg_ts: %d, is_video: %d, is_streaming: %d, is_mp3: %d, is_matroska: %d, is_avi: %d, is_AudioCD: %d, is_VCD: %d", filename, is_mpeg_ps, is_mpeg_ts, is_video, is_streaming, is_mp3, is_matroska, is_avi, is_AudioCD, is_VCD);
	
	int is_audio = !is_video;

	int all_ok = 0;

	m_gst_pipeline = gst_pipeline_new ("mediaplayer");
	if (!m_gst_pipeline)
		eWarning("failed to create pipeline");

	if (is_AudioCD)
	{
		source = gst_element_factory_make ("cdiocddasrc", "cda-source");
		if (source)
			g_object_set (G_OBJECT (source), "device", "/dev/cdroms/cdrom0", NULL);
		else
			is_AudioCD = 0;
	}
	if ( !is_streaming && !is_AudioCD )
		source = gst_element_factory_make ("filesrc", "file-source");
	else if ( is_streaming ) 
	{
		source = gst_element_factory_make ("neonhttpsrc", "http-source");
		if (source)
			g_object_set (G_OBJECT (source), "automatic-redirect", TRUE, NULL);
	}

	if (!source)
		eWarning("failed to create %s", is_streaming ? "neonhttpsrc" : "filesrc");
				/* configure source */
	else if (!is_AudioCD)
		g_object_set (G_OBJECT (source), "location", filename, NULL);
	else
	{ 
		int track = atoi(filename+18);
		eDebug("play audio CD track #%i",track);
		if (track > 0)
			g_object_set (G_OBJECT (source), "track", track, NULL);
	}

	if (is_audio)
	{
			/* filesrc -> decodebin -> audioconvert -> capsfilter -> alsasink */
		const char *decodertype = "decodebin";

		decoder = gst_element_factory_make (decodertype, "decoder");
		if (!decoder)
			eWarning("failed to create %s decoder", decodertype);

		conv = gst_element_factory_make ("audioconvert", "converter");
		if (!conv)
			eWarning("failed to create audioconvert");

		flt = gst_element_factory_make ("capsfilter", "flt");
		if (!flt)
			eWarning("failed to create capsfilter");

			/* for some reasons, we need to set the sample format to depth/width=16, because auto negotiation doesn't work. */
			/* endianness, however, is not required to be set anymore. */
		if (flt)
		{
			GstCaps *caps = gst_caps_new_simple("audio/x-raw-int", /* "endianness", G_TYPE_INT, 4321, */ "depth", G_TYPE_INT, 16, "width", G_TYPE_INT, 16, /*"channels", G_TYPE_INT, 2, */(char*)0);
			g_object_set (G_OBJECT (flt), "caps", caps, (char*)0);
			gst_caps_unref(caps);
		}

		sink = gst_element_factory_make ("alsasink", "alsa-output");
		if (!sink)
			eWarning("failed to create osssink");

		if (source && decoder && conv && sink)
			all_ok = 1;
	} else /* is_video */
	{
			/* filesrc -> mpegdemux -> | queue_audio -> dvbaudiosink
			                           | queue_video -> dvbvideosink */

		audio = gst_element_factory_make("dvbaudiosink", "audiosink");
		queue_audio = gst_element_factory_make("queue", "queue_audio");
		
		video = gst_element_factory_make("dvbvideosink", "videosink");
		queue_video = gst_element_factory_make("queue", "queue_video");
		
		if (is_mpeg_ps)
			videodemux = gst_element_factory_make("flupsdemux", "videodemux");
		else if (is_mpeg_ts)
			videodemux = gst_element_factory_make("flutsdemux", "videodemux");
		else if (is_matroska)
			videodemux = gst_element_factory_make("matroskademux", "videodemux");
		else if (is_avi)
			videodemux = gst_element_factory_make("avidemux", "videodemux");

		if (!videodemux)
		{
			eDebug("fluendo mpegdemux not available, falling back to mpegdemux\n");
			videodemux = gst_element_factory_make("mpegdemux", "videodemux");
		}

		eDebug("audio: %p, queue_audio %p, video %p, queue_video %p, videodemux %p", audio, queue_audio, video, queue_video, videodemux);
		if (audio && queue_audio && video && queue_video && videodemux)
		{
			g_object_set (G_OBJECT (queue_audio), "max-size-bytes", 256*1024, NULL);
			g_object_set (G_OBJECT (queue_audio), "max-size-buffers", 0, NULL);
			g_object_set (G_OBJECT (queue_audio), "max-size-time", (guint64)0, NULL);
			g_object_set (G_OBJECT (queue_video), "max-size-buffers", 0, NULL);
			g_object_set (G_OBJECT (queue_video), "max-size-bytes", 2*1024*1024, NULL);
			g_object_set (G_OBJECT (queue_video), "max-size-time", (guint64)0, NULL);
			all_ok = 1;
		}
	}
	
	if (m_gst_pipeline && all_ok)
	{
		gst_bus_set_sync_handler(gst_pipeline_get_bus (GST_PIPELINE (m_gst_pipeline)), gstBusSyncHandler, this);

		if (is_AudioCD)
		{
			queue_audio = gst_element_factory_make("queue", "queue_audio");
			g_object_set (G_OBJECT (sink), "preroll-queue-len", 80, NULL);
			gst_bin_add_many (GST_BIN (m_gst_pipeline), source, queue_audio, conv, sink, NULL);
			gst_element_link_many(source, queue_audio, conv, sink, NULL);
		}
		else if (is_audio)
		{
			queue_audio = gst_element_factory_make("queue", "queue_audio");

			g_signal_connect (decoder, "new-decoded-pad", G_CALLBACK(gstCBnewPad), this);
			g_signal_connect (decoder, "unknown-type", G_CALLBACK(gstCBunknownType), this);

			if (!is_mp3)
				g_object_set (G_OBJECT (sink), "preroll-queue-len", 80, NULL);

				/* gst_bin will take the 'floating references' */
			gst_bin_add_many (GST_BIN (m_gst_pipeline),
						source, queue_audio, decoder, NULL);

				/* in decodebin's case we can just connect the source with the decodebin, and decodebin will take care about id3demux (or whatever is required) */
			gst_element_link_many(source, queue_audio, decoder, NULL);

				/* create audio bin with the audioconverter, the capsfilter and the audiosink */
			audio = gst_bin_new ("audiobin");

			GstPad *audiopad = gst_element_get_static_pad (conv, "sink");
			gst_bin_add_many(GST_BIN(audio), conv, flt, sink, (char*)0);
			gst_element_link_many(conv, flt, sink, (char*)0);
			gst_element_add_pad(audio, gst_ghost_pad_new ("sink", audiopad));
			gst_object_unref(audiopad);
			gst_bin_add (GST_BIN(m_gst_pipeline), audio);
				/* in mad's case, we can directly connect the decoder to the audiobin. otherwise, we do this in gstCBnewPad */
			if (is_mp3)
				gst_element_link(decoder, audio);

		} else /* is_video */
		{
			char srt_filename[strlen(filename)+1];
			strncpy(srt_filename,filename,strlen(filename)-3);
			srt_filename[strlen(filename)-3]='\0';
			strcat(srt_filename, "srt");
			struct stat buffer;
			if (stat(srt_filename, &buffer) == 0)
			{
				eDebug("subtitle file found: %s",srt_filename);
				GstElement *subsource = gst_element_factory_make ("filesrc", "srt_source");
				g_object_set (G_OBJECT (subsource), "location", srt_filename, NULL);
				GstElement *parser = gst_element_factory_make("subparse", "parse_subtitles");
				GstElement *switch_subtitles = gst_element_factory_make ("input-selector", "switch_subtitles");
				GstElement *sink = gst_element_factory_make("fakesink", "sink_subtitles");
				gst_bin_add_many(GST_BIN (m_gst_pipeline), subsource, switch_subtitles, parser, sink, NULL);
				gst_element_link(subsource, switch_subtitles);
				gst_element_link(switch_subtitles, parser);
				gst_element_link(parser, sink);
				g_object_set (G_OBJECT(switch_subtitles), "select-all", TRUE, NULL);
				g_object_set (G_OBJECT(sink), "signal-handoffs", TRUE, NULL);
				g_object_set (G_OBJECT(sink), "sync", TRUE, NULL);
				g_object_set (G_OBJECT(parser), "subtitle-encoding", "ISO-8859-15", NULL);
				g_signal_connect(sink, "handoff", G_CALLBACK(gstCBsubtitleAvail), this);
				subtitleStream subs;
				subs.language_code = std::string(".srt file");
				m_subtitleStreams.push_back(subs);
			}
			gst_bin_add_many(GST_BIN(m_gst_pipeline), source, videodemux, audio, queue_audio, video, queue_video, NULL);
			switch_audio = gst_element_factory_make ("input-selector", "switch_audio");
			if (switch_audio)
			{
				g_object_set (G_OBJECT (switch_audio), "select-all", TRUE, NULL);
				gst_bin_add(GST_BIN(m_gst_pipeline), switch_audio);
				gst_element_link(switch_audio, queue_audio);
			}

			if (is_VCD)
			{
				GstElement *cdxaparse = gst_element_factory_make("cdxaparse", "cdxaparse");
				gst_bin_add(GST_BIN(m_gst_pipeline), cdxaparse);
				gst_element_link(source, cdxaparse);
				gst_element_link(cdxaparse, videodemux);
			}
			else
				gst_element_link(source, videodemux);
			gst_element_link(queue_audio, audio);
			gst_element_link(queue_video, video);
			g_signal_connect(videodemux, "pad-added", G_CALLBACK (gstCBpadAdded), this);
		}
	} else
	{
		if (m_gst_pipeline)
			gst_object_unref(GST_OBJECT(m_gst_pipeline));
		if (source)
			gst_object_unref(GST_OBJECT(source));
		if (decoder)
			gst_object_unref(GST_OBJECT(decoder));
		if (conv)
			gst_object_unref(GST_OBJECT(conv));
		if (sink)
			gst_object_unref(GST_OBJECT(sink));

		if (audio)
			gst_object_unref(GST_OBJECT(audio));
		if (queue_audio)
			gst_object_unref(GST_OBJECT(queue_audio));
		if (video)
			gst_object_unref(GST_OBJECT(video));
		if (queue_video)
			gst_object_unref(GST_OBJECT(queue_video));
		if (videodemux)
			gst_object_unref(GST_OBJECT(videodemux));
		if (switch_audio)
			gst_object_unref(GST_OBJECT(switch_audio));

		eDebug("sorry, can't play.");
		m_gst_pipeline = 0;
	}
	
	gst_element_set_state (m_gst_pipeline, GST_STATE_PLAYING);
}

eServiceMP3::~eServiceMP3()
{
	delete m_subtitle_widget;
	if (m_state == stRunning)
		stop();
	
	if (m_stream_tags)
		gst_tag_list_free(m_stream_tags);
	
	if (m_gst_pipeline)
	{
		gst_object_unref (GST_OBJECT (m_gst_pipeline));
		eDebug("SERVICEMP3 destruct!");
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
	assert(m_state == stIdle);
	
	m_state = stRunning;
	if (m_gst_pipeline)
	{
		eDebug("starting pipeline");
		gst_element_set_state (m_gst_pipeline, GST_STATE_PLAYING);
	}
	m_event(this, evStart);
	return 0;
}

RESULT eServiceMP3::stop()
{
	assert(m_state != stIdle);
	if (m_state == stStopped)
		return -1;
	eDebug("MP3: %s stop\n", m_filename.c_str());
	gst_element_set_state(m_gst_pipeline, GST_STATE_NULL);
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
	/* we can't do slomo yet */
	return -1;
}

RESULT eServiceMP3::setFastForward(int ratio)
{
	m_currentTrickRatio = ratio;
	if (ratio)
		m_seekTimeout.start(1000, 0);
	else
		m_seekTimeout.stop();
	return 0;
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
		m_seekTimeout.stop();
	}
	if (ppos > len)
	{
		ppos = 0;
		stop();
		m_seekTimeout.stop();
		return;
	}
	seekTo(ppos);
}

		// iPausableService
RESULT eServiceMP3::pause()
{
	if (!m_gst_pipeline)
		return -1;
	GstStateChangeReturn res = gst_element_set_state(m_gst_pipeline, GST_STATE_PAUSED);
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
	if (!m_gst_pipeline)
		return -1;

	GstStateChangeReturn res;
	res = gst_element_set_state(m_gst_pipeline, GST_STATE_PLAYING);
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
	if (!m_gst_pipeline)
		return -1;
	if (m_state != stRunning)
		return -1;
	
	GstFormat fmt = GST_FORMAT_TIME;
	gint64 len;
	
	if (!gst_element_query_duration(m_gst_pipeline, &fmt, &len))
		return -1;
	
		/* len is in nanoseconds. we have 90 000 pts per second. */
	
	pts = len / 11111;
	return 0;
}

RESULT eServiceMP3::seekTo(pts_t to)
{
	if (!m_gst_pipeline)
		return -1;

		/* convert pts to nanoseconds */
	gint64 time_nanoseconds = to * 11111LL;
	if (!gst_element_seek (m_gst_pipeline, 1.0, GST_FORMAT_TIME, GST_SEEK_FLAG_FLUSH,
		GST_SEEK_TYPE_SET, time_nanoseconds,
		GST_SEEK_TYPE_NONE, GST_CLOCK_TIME_NONE))
	{
		eDebug("SEEK failed");
		return -1;
	}
	return 0;
}

RESULT eServiceMP3::seekRelative(int direction, pts_t to)
{
	if (!m_gst_pipeline)
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
	if (!m_gst_pipeline)
		return -1;
	if (m_state != stRunning)
		return -1;
	
	GstFormat fmt = GST_FORMAT_TIME;
	gint64 len;
	
	if (!gst_element_query_position(m_gst_pipeline, &fmt, &len))
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
	name = m_filename;
	size_t n = name.rfind('/');
	if (n != std::string::npos)
		name = name.substr(n + 1);
	return 0;
}

int eServiceMP3::getInfo(int w)
{
	gchar *tag = 0;

	switch (w)
	{
	case sTitle:
	case sArtist:
	case sAlbum:
	case sComment:
	case sTracknumber:
	case sGenre:
	case sVideoType:
	case sTimeCreate:
	case sUser+12:
		return resIsString;
	case sCurrentTitle:
		tag = GST_TAG_TRACK_NUMBER;
		break;
	case sTotalTitles:
		tag = GST_TAG_TRACK_COUNT;
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
	gchar *tag = 0;
	switch (w)
	{
	case sTitle:
		tag = GST_TAG_TITLE;
		break;
	case sArtist:
		tag = GST_TAG_ARTIST;
		break;
	case sAlbum:
		tag = GST_TAG_ALBUM;
		break;
	case sComment:
		tag = GST_TAG_COMMENT;
		break;
	case sTracknumber:
		tag = GST_TAG_TRACK_NUMBER;
		break;
	case sGenre:
		tag = GST_TAG_GENRE;
		break;
	case sVideoType:
		tag = GST_TAG_VIDEO_CODEC;
		break;
	case sTimeCreate:
		GDate *date;
		if (gst_tag_list_get_date(m_stream_tags, GST_TAG_DATE, &date))
		{
			gchar res[5];
 			g_date_strftime (res, sizeof(res), "%Y", date); 
			return (std::string)res;
		}
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
	gint nb_sources;
	GstPad *active_pad;
	GstElement *switch_audio = gst_bin_get_by_name(GST_BIN(m_gst_pipeline),"switch_audio");
	if ( !switch_audio )
	{
		eDebug("can't switch audio tracks! gst-plugin-selector needed");
		return -1;
	}
	g_object_get (G_OBJECT (switch_audio), "n-pads", &nb_sources, NULL);
 	if ( (unsigned int)i >= m_audioStreams.size() || i >= nb_sources || (unsigned int)m_currentAudioStream >= m_audioStreams.size() )
		return -2;
	char sinkpad[8];
	sprintf(sinkpad, "sink%d", i);
	g_object_set (G_OBJECT (switch_audio), "active-pad", gst_element_get_pad (switch_audio, sinkpad), NULL);
	g_object_get (G_OBJECT (switch_audio), "active-pad", &active_pad, NULL);
	gchar *name;
	name = gst_pad_get_name (active_pad);
	eDebug ("switched audio to (%s)", name);
	g_free(name);
	m_currentAudioStream = i;
	return 0;
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
// 	eDebug("eServiceMP3::getTrackInfo(&info, %i)",i);
 	if (i >= m_audioStreams.size())
		return -2;
	if (m_audioStreams[i].type == atMPEG)
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
	else
		info.m_description = "???";
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
		eDebug("gst_message from %s: %s", sourceName, string);
		g_free(string);
	}
	else
		eDebug("gst_message from %s: %s (without structure)", sourceName, GST_MESSAGE_TYPE_NAME(msg));
#endif
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
		eWarning("Gstreamer error: %s (%i)", err->message, err->code );
		if ( err->domain == GST_STREAM_ERROR && err->code == GST_STREAM_ERROR_DECODE )
		{
			if ( g_strrstr(sourceName, "videosink") )
				m_event((iPlayableService*)this, evUser+11);
		}
		g_error_free(err);
			/* TODO: signal error condition to user */
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

		gchar *g_audiocodec;
		if ( gst_tag_list_get_string(tags, GST_TAG_AUDIO_CODEC, &g_audiocodec) && m_audioStreams.size() == 0 )
		{
			GstPad* pad = gst_element_get_pad (GST_ELEMENT(source), "src");
			GstCaps* caps = gst_pad_get_caps(pad);
			GstStructure* str = gst_caps_get_structure(caps, 0);
			if ( !str )
				break;
			audioStream audio;
			audio.type = gstCheckAudioPad(str);
			m_audioStreams.push_back(audio);
		}

		gst_tag_list_free(tags);
		m_event((iPlayableService*)this, evUpdatedInfo);
		break;
	}
	case GST_MESSAGE_ASYNC_DONE:
	{
		GstTagList *tags;
		for (std::vector<audioStream>::iterator IterAudioStream(m_audioStreams.begin()); IterAudioStream != m_audioStreams.end(); ++IterAudioStream)
		{
			if ( IterAudioStream->pad )
			{
				g_object_get(IterAudioStream->pad, "tags", &tags, NULL);
				gchar *g_language;
				if ( gst_is_tag_list(tags) && gst_tag_list_get_string(tags, GST_TAG_LANGUAGE_CODE, &g_language) )
				{
					eDebug("found audio language %s",g_language);
					IterAudioStream->language_code = std::string(g_language);
					g_free (g_language);
				}
			}
		}
		for (std::vector<subtitleStream>::iterator IterSubtitleStream(m_subtitleStreams.begin()); IterSubtitleStream != m_subtitleStreams.end(); ++IterSubtitleStream)
		{
			if ( IterSubtitleStream->pad )
			{
				g_object_get(IterSubtitleStream->pad, "tags", &tags, NULL);
				gchar *g_language;
				if ( gst_is_tag_list(tags) && gst_tag_list_get_string(tags, GST_TAG_LANGUAGE_CODE, &g_language) )
				{
					eDebug("found subtitle language %s",g_language);
					IterSubtitleStream->language_code = std::string(g_language);
					g_free (g_language);
				}
			}
		}
	}
        case GST_MESSAGE_ELEMENT:
	{
		if ( gst_is_missing_plugin_message(msg) )
		{
			gchar *description = gst_missing_plugin_message_get_description(msg);			
			if ( description )
			{
				m_error_message = description;
				g_free(description);
				m_event((iPlayableService*)this, evUser+12);
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
	const gchar* type;
	type = gst_structure_get_name(structure);

	if (!strcmp(type, "audio/mpeg")) {
			gint mpegversion, layer = 0;
			gst_structure_get_int (structure, "mpegversion", &mpegversion);
			gst_structure_get_int (structure, "layer", &layer);
			eDebug("mime audio/mpeg version %d layer %d", mpegversion, layer);
			switch (mpegversion) {
				case 1:
				{
					if ( layer == 3 )
						return atMP3;
					else
						return atMPEG;
				}
				case 2:
					return atMPEG;
				case 4:
					return atAAC;
				default:
					return atUnknown;
			}
		}
	else
	{
		eDebug("mime %s", type);
		if (!strcmp(type, "audio/x-ac3") || !strcmp(type, "audio/ac3"))
			return atAC3;
		else if (!strcmp(type, "audio/x-dts") || !strcmp(type, "audio/dts"))
			return atDTS;
		else if (!strcmp(type, "audio/x-raw-int"))
			return atPCM;
	}
	return atUnknown;
}

void eServiceMP3::gstCBpadAdded(GstElement *decodebin, GstPad *pad, gpointer user_data)
{
	const gchar* type;
	GstCaps* caps;
	GstStructure* str;
	caps = gst_pad_get_caps(pad);
	str = gst_caps_get_structure(caps, 0);
	type = gst_structure_get_name(str);

	eDebug("A new pad %s:%s was created", GST_OBJECT_NAME (decodebin), GST_OBJECT_NAME (pad));

	eServiceMP3 *_this = (eServiceMP3*)user_data;
	GstBin *pipeline = GST_BIN(_this->m_gst_pipeline);
	if (g_strrstr(type,"audio"))
	{
		audioStream audio;
		audio.type = _this->gstCheckAudioPad(str);
		GstElement *switch_audio = gst_bin_get_by_name(pipeline , "switch_audio");
		if ( switch_audio )
		{
			GstPad *sinkpad = gst_element_get_request_pad (switch_audio, "sink%d");
			gst_pad_link(pad, sinkpad);
			audio.pad = sinkpad;
			_this->m_audioStreams.push_back(audio);
		
			if ( _this->m_audioStreams.size() == 1 )
			{
				_this->selectAudioStream(0);
				gst_element_set_state (_this->m_gst_pipeline, GST_STATE_PLAYING);
			}
			else
				g_object_set (G_OBJECT (switch_audio), "select-all", FALSE, NULL);
		}
		else
		{
			gst_pad_link(pad, gst_element_get_static_pad(gst_bin_get_by_name(pipeline,"queue_audio"), "sink"));
			_this->m_audioStreams.push_back(audio);
		}
	}
	if (g_strrstr(type,"video"))
	{
		gst_pad_link(pad, gst_element_get_static_pad(gst_bin_get_by_name(pipeline,"queue_video"), "sink"));
	}
	if (g_strrstr(type,"application/x-ssa") || g_strrstr(type,"application/x-ass"))
	{
		GstElement *switch_subtitles = gst_bin_get_by_name(pipeline,"switch_subtitles");
		if ( !switch_subtitles )
		{
			switch_subtitles = gst_element_factory_make ("input-selector", "switch_subtitles");
			if ( !switch_subtitles )
				return;
			GstElement *parser = gst_element_factory_make("ssaparse", "parse_subtitles");
			GstElement *sink = gst_element_factory_make("fakesink", "sink_subtitles");
			gst_bin_add_many(pipeline, switch_subtitles, parser, sink, NULL);
			gst_element_link(switch_subtitles, parser);
			gst_element_link(parser, sink);
			g_object_set (G_OBJECT(sink), "signal-handoffs", TRUE, NULL);
			g_signal_connect(sink, "handoff", G_CALLBACK(gstCBsubtitleAvail), _this);
		}
		GstPad *sinkpad = gst_element_get_request_pad (switch_subtitles, "sink%d");
		gst_pad_link(pad, sinkpad);
		subtitleStream subs;
		subs.pad = sinkpad;
		_this->m_subtitleStreams.push_back(subs);
	}
}

void eServiceMP3::gstCBfilterPadAdded(GstElement *filter, GstPad *pad, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	GstElement *decoder = gst_bin_get_by_name(GST_BIN(_this->m_gst_pipeline),"decoder");
	gst_pad_link(pad, gst_element_get_static_pad (decoder, "sink"));
}

void eServiceMP3::gstCBnewPad(GstElement *decodebin, GstPad *pad, gboolean last, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	GstCaps *caps;
	GstStructure *str;
	GstPad *audiopad;

	/* only link once */
	GstElement *audiobin = gst_bin_get_by_name(GST_BIN(_this->m_gst_pipeline),"audiobin");
	audiopad = gst_element_get_static_pad (audiobin, "sink");
	if ( !audiopad || GST_PAD_IS_LINKED (audiopad)) {
		eDebug("audio already linked!");
		g_object_unref (audiopad);
		return;
	}

	/* check media type */
	caps = gst_pad_get_caps (pad);
	str = gst_caps_get_structure (caps, 0);
	eDebug("gst new pad! %s", gst_structure_get_name (str));

	if (!g_strrstr (gst_structure_get_name (str), "audio")) {
		gst_caps_unref (caps);
		gst_object_unref (audiopad);
		return;
	}
	
	gst_caps_unref (caps);
	gst_pad_link (pad, audiopad);
}

void eServiceMP3::gstCBunknownType(GstElement *decodebin, GstPad *pad, GstCaps *caps, gpointer user_data)
{
	GstStructure *str;

	/* check media type */
	caps = gst_pad_get_caps (pad);
	str = gst_caps_get_structure (caps, 0);
	eDebug("unknown type: %s - this can't be decoded.", gst_structure_get_name (str));
	gst_caps_unref (caps);
}

void eServiceMP3::gstPoll(const int&)
{
		/* ok, we have a serious problem here. gstBusSyncHandler sends 
		   us the wakup signal, but likely before it was posted.
		   the usleep, an EVIL HACK (DON'T DO THAT!!!) works around this.
		   
		   I need to understand the API a bit more to make this work 
		   proplerly. */
	usleep(1);
	
	GstBus *bus = gst_pipeline_get_bus (GST_PIPELINE (m_gst_pipeline));
	GstMessage *message;
	while ((message = gst_bus_pop (bus)))
	{
		gstBusCall(bus, message);
		gst_message_unref (message);
	}
}

eAutoInitPtr<eServiceFactoryMP3> init_eServiceFactoryMP3(eAutoInitNumbers::service+1, "eServiceFactoryMP3");

void eServiceMP3::gstCBsubtitleAvail(GstElement *element, GstBuffer *buffer, GstPad *pad, gpointer user_data)
{
	gint64 duration_ns = GST_BUFFER_DURATION(buffer);
	const unsigned char *text = (unsigned char *)GST_BUFFER_DATA(buffer);
	eDebug("gstCBsubtitleAvail: %s",text);
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	if ( _this->m_subtitle_widget )
	{
		ePangoSubtitlePage page;
		gRGB rgbcol(0xD0,0xD0,0xD0);
		page.m_elements.push_back(ePangoSubtitlePageElement(rgbcol, (const char*)text));
		page.m_timeout = duration_ns / 1000000;
		(_this->m_subtitle_widget)->setPage(page);
	}
}

RESULT eServiceMP3::enableSubtitles(eWidget *parent, ePyObject tuple)
{
	eDebug("eServiceMP3::enableSubtitles");

	ePyObject entry;
	int tuplesize = PyTuple_Size(tuple);
	int pid;
	gint nb_sources;
	GstPad *active_pad;
	GstElement *switch_subtitles = gst_bin_get_by_name(GST_BIN(m_gst_pipeline),"switch_subtitles");

	if (!PyTuple_Check(tuple))
		goto error_out;
	if (tuplesize < 1)
		goto error_out;
	entry = PyTuple_GET_ITEM(tuple, 1);
	if (!PyInt_Check(entry))
		goto error_out;
	pid = PyInt_AsLong(entry);

	m_subtitle_widget = new eSubtitleWidget(parent);
	m_subtitle_widget->resize(parent->size()); /* full size */

	if ( !switch_subtitles )
	{
		eDebug("can't switch subtitle tracks! gst-plugin-selector needed");
		return -2;
	}
	g_object_get (G_OBJECT (switch_subtitles), "n-pads", &nb_sources, NULL);
 	if ( (unsigned int)pid >= m_subtitleStreams.size() || pid >= nb_sources || (unsigned int)m_currentSubtitleStream >= m_subtitleStreams.size() )
		return -2;
	char sinkpad[8];
	sprintf(sinkpad, "sink%d", pid);
	g_object_set (G_OBJECT (switch_subtitles), "active-pad", gst_element_get_pad (switch_subtitles, sinkpad), NULL);
	g_object_get (G_OBJECT (switch_subtitles), "active-pad", &active_pad, NULL);
	gchar *name;
	name = gst_pad_get_name (active_pad);
	eDebug ("switched subtitles to (%s)", name);
	g_free(name);
	m_currentSubtitleStream = pid;

	return 0;
error_out:
	eDebug("enableSubtitles needs a tuple as 2nd argument!\n"
		"for gst subtitles (2, subtitle_stream_count)");
	return -1;
}

RESULT eServiceMP3::disableSubtitles(eWidget *parent)
{
	eDebug("eServiceMP3::disableSubtitles");
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
	int stream_count = 0;

	for (std::vector<subtitleStream>::iterator IterSubtitleStream(m_subtitleStreams.begin()); IterSubtitleStream != m_subtitleStreams.end(); ++IterSubtitleStream)
	{
		ePyObject tuple = PyTuple_New(5);
		PyTuple_SET_ITEM(tuple, 0, PyInt_FromLong(2));
		PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(stream_count));
		PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(0));
		PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(0));
		PyTuple_SET_ITEM(tuple, 4, PyString_FromString((IterSubtitleStream->language_code).c_str()));
		PyList_Append(l, tuple);
		Py_DECREF(tuple);
		stream_count++;
	}

	return l;
}

#else
#warning gstreamer not available, not building media player
#endif
