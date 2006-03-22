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
		sc->addServiceFactory(eServiceFactoryMP3::id, this);

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
	GstElement *source, *decoder, *conv, *flt, *sink;
	m_state = stIdle;
	eDebug("SERVICEMP3 construct!");

	m_gst_pipeline = gst_pipeline_new ("audio-player");
	if (!m_gst_pipeline)
		eWarning("failed to create pipeline");

	source = gst_element_factory_make ("filesrc", "file-source");
	if (!source)
		eWarning("failed to create filesrc");
		
	decoder = gst_element_factory_make ("decodebin", "decoder");
	if (!decoder)
		eWarning("failed to create decodebin decoder");
	
	conv = gst_element_factory_make ("audioconvert", "converter");
	if (!conv)
		eWarning("failed to create audioconvert");
	
	flt = gst_element_factory_make ("capsfilter", "flt");
	if (!flt)
		eWarning("failed to create capsfilter");
	
		/* workaround for [3des]' driver bugs: */
	if (flt)
	{
		GstCaps *caps = gst_caps_new_simple("audio/x-raw-int", "endianness", G_TYPE_INT, 4321, 0);
		g_object_set (G_OBJECT (flt), "caps", caps, 0);
		gst_caps_unref(caps);
	}
	
	sink = gst_element_factory_make ("alsasink", "alsa-output");
	if (!sink)
		eWarning("failed to create osssink");
	
	if (m_gst_pipeline && source && decoder && conv && sink)
	{
		gst_bus_set_sync_handler(gst_pipeline_get_bus (GST_PIPELINE (m_gst_pipeline)), gstBusSyncHandler, this);

		g_object_set (G_OBJECT (source), "location", filename, NULL);
		g_signal_connect (decoder, "new-decoded-pad", G_CALLBACK(gstCBnewPad), this);

			/* gst_bin will take the 'floating references' */
		gst_bin_add_many (GST_BIN (m_gst_pipeline),
					source, decoder, NULL);
		
		gst_element_link(source, decoder);
		
			/* create audio bin */
		m_gst_audio = gst_bin_new ("audiobin");
		GstPad *audiopad = gst_element_get_pad (conv, "sink");
		
		gst_bin_add_many(GST_BIN(m_gst_audio), conv, flt, sink, 0);
		gst_element_link_many(conv, flt, sink, 0);
		gst_element_add_pad(m_gst_audio, gst_ghost_pad_new ("sink", audiopad));
		gst_object_unref(audiopad);
		
		gst_bin_add (GST_BIN(m_gst_pipeline), m_gst_audio);
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
		eDebug("sorry, can't play.");
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
	/* implement me */
	return -1;
}

RESULT eServiceMP3::seekRelative(int direction, pts_t to)
{
	/* implement me */
	return -1;
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
	name = "MP3 File: " + m_filename;
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
	switch (GST_MESSAGE_TYPE (msg))
	{
	case GST_MESSAGE_EOS:
		eDebug("end of stream!");
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
		exit(0);
		break;
	}
	case GST_MESSAGE_TAG:
	{
		GstTagList *tags, *result;
		gst_message_parse_tag(msg, &tags);
		eDebug("is tag list: %d", GST_IS_TAG_LIST(tags));

		result = gst_tag_list_merge(m_stream_tags, tags, GST_TAG_MERGE_PREPEND);
		if (result)
		{
			if (m_stream_tags)
				gst_tag_list_free(m_stream_tags);
			m_stream_tags = result;
		}
		gst_tag_list_free(tags);
		
		eDebug("listing tags..");
		gst_tag_list_foreach(m_stream_tags, foreach, 0);
		eDebug("ok");

		if (m_stream_tags)
		{
			gchar *title;
			eDebug("is tag list: %d", GST_IS_TAG_LIST(m_stream_tags));
			if (gst_tag_list_get_string(m_stream_tags, GST_TAG_TITLE, &title))
			{
				eDebug("TITLE: %s", title);
				g_free(title);
			} else
				eDebug("no title");
		} else
			eDebug("no tags");
		
		eDebug("tag list updated!");
		break;
	}
	default:
		eDebug("unknown message");
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

void eServiceMP3::gstCBnewPad(GstElement *decodebin, GstPad *pad, gboolean last, gpointer user_data)
{
	eServiceMP3 *_this = (eServiceMP3*)user_data;
	GstCaps *caps;
	GstStructure *str;
	GstPad *audiopad;
	
	/* only link once */
	audiopad = gst_element_get_pad (_this->m_gst_audio, "sink");
	if (GST_PAD_IS_LINKED (audiopad)) {
		g_object_unref (audiopad);
		return;
	}
	
	/* check media type */
	caps = gst_pad_get_caps (pad);
	str = gst_caps_get_structure (caps, 0);
	if (!g_strrstr (gst_structure_get_name (str), "audio")) {
		gst_caps_unref (caps);
		gst_object_unref (audiopad);
		return;
	}
	
	gst_caps_unref (caps);
	gst_pad_link (pad, audiopad);
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
	while (message = gst_bus_pop (bus))
	{
		gstBusCall(bus, message);
		gst_message_unref (message);
	}
}

eAutoInitPtr<eServiceFactoryMP3> init_eServiceFactoryMP3(eAutoInitNumbers::service+1, "eServiceFactoryMP3");
#else
#warning gstreamer not available, not building media player
#endif
