#ifdef HAVE_GSTREAMER

	/* note: this requires gstreamer 0.10.x and a big list of plugins. */
	/* it's currently hardcoded to use a big-endian alsasink as sink. */
#include <lib/base/eerror.h>
#include <lib/base/object.h>
#include <lib/base/ebase.h>
#include <string>
#include <lib/service/servicemp3.h>
#include <lib/service/service.h>
#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <gst/gst.h>

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

RESULT eServiceFactoryMP3::offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr)
{
	ptr = 0;
	return -1;
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
	CONNECT(m_pump.recv_msg, eServiceMP3::gstPoll);
	GstElement *source = 0;
	
	GstElement *filter = 0, *decoder = 0, *conv = 0, *flt = 0, *sink = 0; /* for audio */
	
	GstElement *audio = 0, *queue_audio = 0, *video = 0, *queue_video = 0, *mpegdemux = 0;
	
	m_state = stIdle;
	eDebug("SERVICEMP3 construct!");
	
		/* FIXME: currently, decodebin isn't possible for 
		   video streams. in that case, make a manual pipeline. */

	const char *ext = strrchr(filename, '.');
	if (!ext)
		ext = filename;

	int is_mpeg_ps = !(strcasecmp(ext, ".mpeg") && strcasecmp(ext, ".mpg") && strcasecmp(ext, ".vob") && strcasecmp(ext, ".bin"));
	int is_mpeg_ts = !strcasecmp(ext, ".ts");
	int is_matroska = !strcasecmp(ext, ".mkv");
	int is_avi = !strcasecmp(ext, ".avi");
	int is_mp3 = !strcasecmp(ext, ".mp3"); /* force mp3 instead of decodebin */
	int is_video = is_mpeg_ps || is_mpeg_ts || is_matroska || is_avi;
	int is_streaming = !strncmp(filename, "http://", 7);
	
	eDebug("filename: %s, is_mpeg_ps: %d, is_mpeg_ts: %d, is_video: %d, is_streaming: %d, is_mp3: %d, is_matroska: %d, is_avi: %d", filename, is_mpeg_ps, is_mpeg_ts, is_video, is_streaming, is_mp3, is_matroska, is_avi);
	
	int is_audio = !is_video;
	
	int all_ok = 0;

	m_gst_pipeline = gst_pipeline_new ("audio-player");
	if (!m_gst_pipeline)
		eWarning("failed to create pipeline");

	if (!is_streaming)
		source = gst_element_factory_make ("filesrc", "file-source");
	else
	{
		source = gst_element_factory_make ("neonhttpsrc", "http-source");
		if (source)
			g_object_set (G_OBJECT (source), "automatic-redirect", TRUE, NULL);
	}

	if (!source)
		eWarning("failed to create %s", is_streaming ? "neonhttpsrc" : "filesrc");
	else
				/* configure source */
		g_object_set (G_OBJECT (source), "location", filename, NULL);

	if (is_audio)
	{
			/* filesrc -> decodebin -> audioconvert -> capsfilter -> alsasink */
		const char *decodertype = is_mp3 ? "mad" : "decodebin";

		decoder = gst_element_factory_make (decodertype, "decoder");
		if (!decoder)
			eWarning("failed to create %s decoder", decodertype);

			/* mp3 decoding needs id3demux to extract ID3 data. 'decodebin' would do that internally. */
		if (is_mp3)
		{
			filter = gst_element_factory_make ("id3demux", "filter");
			if (!filter)
				eWarning("failed to create id3demux");
		}

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
			GstCaps *caps = gst_caps_new_simple("audio/x-raw-int", /* "endianness", G_TYPE_INT, 4321, */ "depth", G_TYPE_INT, 16, "width", G_TYPE_INT, 16, "channels", G_TYPE_INT, 2, (char*)0);
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

		audio = gst_element_factory_make("dvbaudiosink", "audio");
		queue_audio = gst_element_factory_make("queue", "queue_audio");
		
		video = gst_element_factory_make("dvbvideosink", "video");
		queue_video = gst_element_factory_make("queue", "queue_video");
		
		if (is_mpeg_ps)
			mpegdemux = gst_element_factory_make("flupsdemux", "mpegdemux");
		else if (is_mpeg_ts)
			mpegdemux = gst_element_factory_make("flutsdemux", "mpegdemux");
		else if (is_matroska)
			mpegdemux = gst_element_factory_make("matroskademux", "mpegdemux");
		else if (is_avi)
			mpegdemux = gst_element_factory_make("avidemux", "mpegdemux");

		if (!mpegdemux)
		{
			eDebug("fluendo mpegdemux not available, falling back to mpegdemux\n");
			mpegdemux = gst_element_factory_make("mpegdemux", "mpegdemux");
		}
		
		eDebug("audio: %p, queue_audio %p, video %p, queue_video %p, mpegdemux %p", audio, queue_audio, video, queue_video, mpegdemux);
		if (audio && queue_audio && video && queue_video && mpegdemux)
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

		if (is_audio)
		{
			if (!is_mp3)
			{
					/* decodebin has dynamic pads. When they get created, we connect them to the audio bin */
				g_signal_connect (decoder, "new-decoded-pad", G_CALLBACK(gstCBnewPad), this);
				g_signal_connect (decoder, "unknown-type", G_CALLBACK(gstCBunknownType), this);
			}

				/* gst_bin will take the 'floating references' */
			gst_bin_add_many (GST_BIN (m_gst_pipeline),
						source, decoder, NULL);

			if (filter)
			{
					/* id3demux also has dynamic pads, which need to be connected to the decoder (this is done in the 'gstCBfilterPadAdded' CB) */
				gst_bin_add(GST_BIN(m_gst_pipeline), filter);
				gst_element_link(source, filter);
				m_decoder = decoder;
				g_signal_connect (filter, "pad-added", G_CALLBACK(gstCBfilterPadAdded), this);
			} else
					/* in decodebin's case we can just connect the source with the decodebin, and decodebin will take care about id3demux (or whatever is required) */
				gst_element_link(source, decoder);

				/* create audio bin with the audioconverter, the capsfilter and the audiosink */
			m_gst_audio = gst_bin_new ("audiobin");

			GstPad *audiopad = gst_element_get_static_pad (conv, "sink");
			gst_bin_add_many(GST_BIN(m_gst_audio), conv, flt, sink, (char*)0);
			gst_element_link_many(conv, flt, sink, (char*)0);
			gst_element_add_pad(m_gst_audio, gst_ghost_pad_new ("sink", audiopad));
			gst_object_unref(audiopad);
			gst_bin_add (GST_BIN(m_gst_pipeline), m_gst_audio);

				/* in mad's case, we can directly connect the decoder to the audiobin. otherwise, we do this in gstCBnewPad */
			if (is_mp3)
				gst_element_link(decoder, m_gst_audio);
		} else
		{
			gst_bin_add_many(GST_BIN(m_gst_pipeline), source, mpegdemux, audio, queue_audio, video, queue_video, NULL);
			gst_element_link(source, mpegdemux);
			gst_element_link(queue_audio, audio);
			gst_element_link(queue_video, video);
			
			m_gst_audioqueue = queue_audio;
			m_gst_videoqueue = queue_video;
			
			g_signal_connect(mpegdemux, "pad-added", G_CALLBACK (gstCBpadAdded), this);
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
		if (mpegdemux)
			gst_object_unref(GST_OBJECT(mpegdemux));

		eDebug("sorry, can't play.");
		m_gst_pipeline = 0;
	}
	
	gst_element_set_state (m_gst_pipeline, GST_STATE_PLAYING);
}

eServiceMP3::~eServiceMP3()
{
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
	printf("MP3: %s stop\n", m_filename.c_str());
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
	return -1;
}

RESULT eServiceMP3::setFastForward(int ratio)
{
	return -1;
}
  
		// iPausableService
RESULT eServiceMP3::pause()
{
	if (!m_gst_pipeline)
		return -1;
	gst_element_set_state(m_gst_pipeline, GST_STATE_PAUSED);
	return 0;
}

RESULT eServiceMP3::unpause()
{
	if (!m_gst_pipeline)
		return -1;
	gst_element_set_state(m_gst_pipeline, GST_STATE_PLAYING);
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

	pause();

	pts_t ppos;
	getPlayPosition(ppos);
	ppos += to * direction;
	if (ppos < 0)
		ppos = 0;
	seekTo(ppos);
	
	unpause();

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
		/* trickmode currently doesn't make any sense for us. */
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

std::string eServiceMP3::getInfoString(int w)
{
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
	default:
		return "";
	}
	
	if (!m_stream_tags || !tag)
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


		void foreach(const GstTagList *list, const gchar *tag, gpointer user_data)
		{
			if (tag)
				eDebug("Tag: %c%c%c%c", tag[0], tag[1], tag[2], tag[3]);
			
		}

void eServiceMP3::gstBusCall(GstBus *bus, GstMessage *msg)
{
	if (msg)
	{
		gchar *string = gst_structure_to_string(gst_message_get_structure(msg));
		eDebug("gst_message: %s", string);
		g_free(string);
	}
	
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
		eWarning("Gstreamer error: %s", err->message);
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
		gst_tag_list_free(tags);
		
		m_event((iPlayableService*)this, evUpdatedInfo);
		break;
	}
	default:
		break;
	}
}

GstBusSyncReply eServiceMP3::gstBusSyncHandler(GstBus *bus, GstMessage *message, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	_this->m_pump.send(1);
		/* wake */
	return GST_BUS_PASS;
}

void eServiceMP3::gstCBpadAdded(GstElement *decodebin, GstPad *pad, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	gchar *name;
	name = gst_pad_get_name (pad);
	g_print ("A new pad %s was created\n", name);
	GstPad *sinkpad;

	if (g_strrstr(name,"audio")) // mpegdemux uses video_nn with n=0,1,.., flupsdemux uses stream id
		gst_pad_link(pad, gst_element_get_static_pad (_this->m_gst_audioqueue, "sink"));
	if (g_strrstr(name,"video"))
		gst_pad_link(pad, gst_element_get_static_pad (_this->m_gst_videoqueue, "sink"));
	g_free (name);
}

void eServiceMP3::gstCBfilterPadAdded(GstElement *filter, GstPad *pad, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	gst_pad_link(pad, gst_element_get_static_pad (_this->m_decoder, "sink"));
}

void eServiceMP3::gstCBnewPad(GstElement *decodebin, GstPad *pad, gboolean last, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	GstCaps *caps;
	GstStructure *str;
	GstPad *audiopad;

	/* only link once */
	audiopad = gst_element_get_request_pad (_this->m_gst_audio, "sink");
	if (GST_PAD_IS_LINKED (audiopad)) {
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
	eServiceMP3 *_this = (eServiceMP3*)user_data;
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
#else
#warning gstreamer not available, not building media player
#endif
