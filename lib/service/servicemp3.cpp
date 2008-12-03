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
	m_seekTimeout = eTimer::create(eApp);
	m_stream_tags = 0;
	m_currentAudioStream = 0;
	m_currentSubtitleStream = 0;
	m_subtitle_widget = 0;
	m_currentTrickRatio = 0;
	CONNECT(m_seekTimeout->timeout, eServiceMP3::seekTimeoutCB);
	CONNECT(m_pump.recv_msg, eServiceMP3::gstPoll);
	GstElement *source = 0;
	GstElement *decoder = 0, *conv = 0, *flt = 0, *parser = 0, *sink = 0; /* for audio */
	GstElement *audio = 0, *switch_audio = 0, *queue_audio = 0, *video = 0, *queue_video = 0, *videodemux = 0, *audiodemux = 0;
	
	m_state = stIdle;
	eDebug("SERVICEMP3 construct!");
	
		/* FIXME: currently, decodebin isn't possible for 
		   video streams. in that case, make a manual pipeline. */

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
	else if ( strcasecmp(ext, ".mp4") == 0 )
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
	if ( (strncmp(filename, "http://", 7)) == 0 )
		sourceinfo.is_streaming = TRUE;

	eDebug("filename=%s, containertype=%d, is_video=%d, is_streaming=%d", filename, sourceinfo.containertype, sourceinfo.is_video, sourceinfo.is_streaming);

	int all_ok = 0;

	m_gst_pipeline = gst_pipeline_new ("mediaplayer");
	if (!m_gst_pipeline)
		m_error_message = "failed to create GStreamer pipeline!\n";

	if ( sourceinfo.is_streaming )
	{
		eDebug("play webradio!");
		source = gst_element_factory_make ("neonhttpsrc", "http-source");
		if (source)
		{
			g_object_set (G_OBJECT (source), "location", filename, NULL);
			g_object_set (G_OBJECT (source), "automatic-redirect", TRUE, NULL);
		}
		else
			m_error_message = "GStreamer plugin neonhttpsrc not available!\n";
	}
	else if ( sourceinfo.containertype == ctCDA )
	{
		source = gst_element_factory_make ("cdiocddasrc", "cda-source");
		if (source)
		{
			g_object_set (G_OBJECT (source), "device", "/dev/cdroms/cdrom0", NULL);
			int track = atoi(filename+18);
			eDebug("play audio CD track #%i",track);
			if (track > 0)
				g_object_set (G_OBJECT (source), "track", track, NULL);
		}
	}
	else if ( sourceinfo.containertype == ctVCD )
	{
		int fd = open(filename,O_RDONLY);
		char tmp[128*1024];
		int ret = read(fd, tmp, 128*1024);
		close(fd);
		if ( ret == -1 ) // this is a "REAL" VCD
			source = gst_element_factory_make ("vcdsrc", "vcd-source");
			if (source)
				g_object_set (G_OBJECT (source), "device", "/dev/cdroms/cdrom0", NULL);
	}
	if ( !source && !sourceinfo.is_streaming )
	{
		source = gst_element_factory_make ("filesrc", "file-source");
		if (source)
			g_object_set (G_OBJECT (source), "location", filename, NULL);
		else
			m_error_message = "GStreamer can't open filesrc " + (std::string)filename + "!\n";
	}
	if ( sourceinfo.is_video )
	{
			/* filesrc -> mpegdemux -> | queue_audio -> dvbaudiosink
			                           | queue_video -> dvbvideosink */

		audio = gst_element_factory_make("dvbaudiosink", "audiosink");
		if (!audio)
			m_error_message += "failed to create Gstreamer element dvbaudiosink\n";

		video = gst_element_factory_make("dvbvideosink", "videosink");
		if (!video)
			m_error_message += "failed to create Gstreamer element dvbvideosink\n";

		queue_audio = gst_element_factory_make("queue", "queue_audio");
		queue_video = gst_element_factory_make("queue", "queue_video");

		std::string demux_type;
		switch (sourceinfo.containertype)
		{
			case ctMPEGTS:
				demux_type = "flutsdemux";
				break;
			case ctMPEGPS:
			case ctVCD:
				demux_type = "flupsdemux";
				break;
			case ctMKV:
				demux_type = "matroskademux";
				break;
			case ctAVI:
				demux_type = "avidemux";
				break;
			case ctMP4:
				demux_type = "qtdemux";
				break;
			default:
				break;
		}
		videodemux = gst_element_factory_make(demux_type.c_str(), "videodemux");
		if (!videodemux)
			m_error_message = "GStreamer plugin " + demux_type + " not available!\n";

		switch_audio = gst_element_factory_make ("input-selector", "switch_audio");
		if (!switch_audio)
			m_error_message = "GStreamer plugin input-selector not available!\n";

		if (audio && queue_audio && video && queue_video && videodemux && switch_audio)
		{
			g_object_set (G_OBJECT (queue_audio), "max-size-bytes", 256*1024, NULL);
			g_object_set (G_OBJECT (queue_audio), "max-size-buffers", 0, NULL);
			g_object_set (G_OBJECT (queue_audio), "max-size-time", (guint64)0, NULL);
			g_object_set (G_OBJECT (queue_video), "max-size-buffers", 0, NULL);
			g_object_set (G_OBJECT (queue_video), "max-size-bytes", 2*1024*1024, NULL);
			g_object_set (G_OBJECT (queue_video), "max-size-time", (guint64)0, NULL);
			g_object_set (G_OBJECT (switch_audio), "select-all", TRUE, NULL);
			all_ok = 1;
		}
	} else /* is audio */
	{
		std::string demux_type;
		switch ( sourceinfo.containertype )
		{
			case ctMP4:
				demux_type = "qtdemux";
				break;
			default:
				break;
		}
		if ( demux_type.length() )
		{
			audiodemux = gst_element_factory_make(demux_type.c_str(), "audiodemux");
			if (!audiodemux)
				m_error_message = "GStreamer plugin " + demux_type + " not available!\n";
		}
		switch ( sourceinfo.audiotype )
		{
			case atMP3:
			{
				if ( !audiodemux )
				{
					parser = gst_element_factory_make("mp3parse", "audioparse");
					if (!parser)
					{
						m_error_message += "failed to create Gstreamer element mp3parse\n";
						break;
					}
				}
				sink = gst_element_factory_make("dvbaudiosink", "audiosink");
				if ( !sink )
					m_error_message += "failed to create Gstreamer element dvbaudiosink\n";
				else
					all_ok = 1;
				break;
			}
			case atAAC:
			{
				if ( !audiodemux )
				{
					m_error_message += "cannot parse raw AAC audio\n";
					break;
				}
				sink = gst_element_factory_make("dvbaudiosink", "audiosink");
				if (!sink)
					m_error_message += "failed to create Gstreamer element dvbaudiosink\n";
				else
					all_ok = 1;
				break;
			}
			case atAC3:
			{
				if ( !audiodemux )
				{
					m_error_message += "cannot parse raw AC3 audio\n";
					break;
				}
				sink = gst_element_factory_make("dvbaudiosink", "audiosink");
				if ( !sink )
					m_error_message += "failed to create Gstreamer element dvbaudiosink\n";
				else
					all_ok = 1;
				break;
			}
			default:
			{	/* filesrc -> decodebin -> audioconvert -> capsfilter -> alsasink */
				decoder = gst_element_factory_make ("decodebin", "decoder");
				if (!decoder)
					m_error_message += "failed to create Gstreamer element decodebin\n";
		
				conv = gst_element_factory_make ("audioconvert", "converter");
				if (!conv)
					m_error_message += "failed to create Gstreamer element audioconvert\n";
		
				flt = gst_element_factory_make ("capsfilter", "flt");
				if (!flt)
					m_error_message += "failed to create Gstreamer element capsfilter\n";
		
					/* for some reasons, we need to set the sample format to depth/width=16, because auto negotiation doesn't work. */
					/* endianness, however, is not required to be set anymore. */
				if (flt)
				{
					GstCaps *caps = gst_caps_new_simple("audio/x-raw-int", /* "endianness", G_TYPE_INT, 4321, */ "depth", G_TYPE_INT, 16, "width", G_TYPE_INT, 16, /*"channels", G_TYPE_INT, 2, */NULL);
					g_object_set (G_OBJECT (flt), "caps", caps, NULL);
					gst_caps_unref(caps);
				}
		
				sink = gst_element_factory_make ("alsasink", "alsa-output");
				if (!sink)
					m_error_message += "failed to create Gstreamer element alsasink\n";
		
				if (source && decoder && conv && sink)
					all_ok = 1;
				break;
			}
		}

	}
	if (m_gst_pipeline && all_ok)
	{
		gst_bus_set_sync_handler(gst_pipeline_get_bus (GST_PIPELINE (m_gst_pipeline)), gstBusSyncHandler, this);

		if ( sourceinfo.containertype == ctCDA )
		{
			queue_audio = gst_element_factory_make("queue", "queue_audio");
			g_object_set (G_OBJECT (sink), "preroll-queue-len", 80, NULL);
			gst_bin_add_many (GST_BIN (m_gst_pipeline), source, queue_audio, conv, sink, NULL);
			gst_element_link_many(source, queue_audio, conv, sink, NULL);
		}
		else if ( sourceinfo.is_video )
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
				gst_bin_add(GST_BIN (m_gst_pipeline), subsource);
				GstPad *switchpad = gstCreateSubtitleSink(this, stSRT);
				gst_pad_link(gst_element_get_pad (subsource, "src"), switchpad);
				subtitleStream subs;
				subs.pad = switchpad;
				subs.type = stSRT;
				subs.language_code = std::string("und");
				m_subtitleStreams.push_back(subs);
			}
			gst_bin_add_many(GST_BIN(m_gst_pipeline), source, videodemux, audio, queue_audio, video, queue_video, switch_audio, NULL);

			if ( sourceinfo.containertype == ctVCD && gst_bin_get_by_name(GST_BIN(m_gst_pipeline),"file-source") )
			{
				eDebug("this is a fake video cd... we use filesrc ! cdxaparse !");
				GstElement *cdxaparse = gst_element_factory_make("cdxaparse", "cdxaparse");
				gst_bin_add(GST_BIN(m_gst_pipeline), cdxaparse);
				gst_element_link(source, cdxaparse);
				gst_element_link(cdxaparse, videodemux);
			}
			else
				gst_element_link(source, videodemux);

			gst_element_link(switch_audio, queue_audio);
			gst_element_link(queue_audio, audio);
			gst_element_link(queue_video, video);
			g_signal_connect(videodemux, "pad-added", G_CALLBACK (gstCBpadAdded), this);

		} else /* is audio*/
		{
			if ( decoder )
			{
				queue_audio = gst_element_factory_make("queue", "queue_audio");
	
				g_signal_connect (decoder, "new-decoded-pad", G_CALLBACK(gstCBnewPad), this);
				g_signal_connect (decoder, "unknown-type", G_CALLBACK(gstCBunknownType), this);
	
				g_object_set (G_OBJECT (sink), "preroll-queue-len", 80, NULL);
	
					/* gst_bin will take the 'floating references' */
				gst_bin_add_many (GST_BIN (m_gst_pipeline),
							source, queue_audio, decoder, NULL);
	
					/* in decodebin's case we can just connect the source with the decodebin, and decodebin will take care about id3demux (or whatever is required) */
				gst_element_link_many(source, queue_audio, decoder, NULL);
	
					/* create audio bin with the audioconverter, the capsfilter and the audiosink */
				audio = gst_bin_new ("audiobin");
	
				GstPad *audiopad = gst_element_get_static_pad (conv, "sink");
				gst_bin_add_many(GST_BIN(audio), conv, flt, sink, NULL);
				gst_element_link_many(conv, flt, sink, NULL);
				gst_element_add_pad(audio, gst_ghost_pad_new ("sink", audiopad));
				gst_object_unref(audiopad);
				gst_bin_add (GST_BIN(m_gst_pipeline), audio);
			}
			else
			{
				gst_bin_add_many (GST_BIN (m_gst_pipeline), source, sink, NULL);
				if ( parser )
				{
					gst_bin_add (GST_BIN (m_gst_pipeline), parser);
					gst_element_link_many(source, parser, sink, NULL);
				}
				if ( audiodemux )
				{
					gst_bin_add (GST_BIN (m_gst_pipeline), audiodemux);
					g_signal_connect(audiodemux, "pad-added", G_CALLBACK (gstCBpadAdded), this);
					gst_element_link(source, audiodemux);
					eDebug("linked source, audiodemux, sink");
				}
				audioStream audio;
				audio.type = sourceinfo.audiotype;
				m_audioStreams.push_back(audio);
			}
		}
	} else
	{
		m_event((iPlayableService*)this, evUser+12);

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

		eDebug("sorry, can't play: %s",m_error_message.c_str());
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
		m_seekTimeout->start(1000, 0);
	else
		m_seekTimeout->stop();
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

		GValue *gv_image = gst_tag_list_get_value_index(tags, GST_TAG_IMAGE, 0);
		if ( gv_image )
		{
			GstBuffer *buf_image;
			buf_image = gst_value_get_buffer (gv_image);
			int fd = open("/tmp/.id3coverart", O_CREAT|O_WRONLY|O_TRUNC, 0644);
			int ret = write(fd, GST_BUFFER_DATA(buf_image), GST_BUFFER_SIZE(buf_image));
			close(fd);
			m_event((iPlayableService*)this, evUser+13);
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
				m_error_message = "GStreamer plugin " + (std::string)description + " not available!\n";
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
			GstElement *queue_audio = gst_bin_get_by_name(pipeline , "queue_audio");
			if ( queue_audio)
			{
				gst_pad_link(pad, gst_element_get_static_pad(queue_audio, "sink"));
				_this->m_audioStreams.push_back(audio);
			}
			else
				gst_pad_link(pad, gst_element_get_static_pad(gst_bin_get_by_name(pipeline , "audiosink"), "sink"));
		}
	}
	if (g_strrstr(type,"video"))
	{
		gst_pad_link(pad, gst_element_get_static_pad(gst_bin_get_by_name(pipeline,"queue_video"), "sink"));
	}
	if (g_strrstr(type,"application/x-ssa") || g_strrstr(type,"application/x-ass"))
	{
		GstPad *switchpad = _this->gstCreateSubtitleSink(_this, stSSA);
		gst_pad_link(pad, switchpad);
		subtitleStream subs;
		subs.pad = switchpad;
		subs.type = stSSA;
		_this->m_subtitleStreams.push_back(subs);
	}
	if (g_strrstr(type,"text/plain"))
	{
		GstPad *switchpad = _this->gstCreateSubtitleSink(_this, stPlainText);
		gst_pad_link(pad, switchpad);
		subtitleStream subs;
		subs.pad = switchpad;
		subs.type = stPlainText;
		_this->m_subtitleStreams.push_back(subs);
	}
}

GstPad* eServiceMP3::gstCreateSubtitleSink(eServiceMP3* _this, subtype_t type)
{
	GstBin *pipeline = GST_BIN(_this->m_gst_pipeline);
	GstElement *switch_subparse = gst_bin_get_by_name(pipeline,"switch_subparse");
	if ( !switch_subparse )
	{
		switch_subparse = gst_element_factory_make ("input-selector", "switch_subparse");
		GstElement *sink = gst_element_factory_make("fakesink", "sink_subtitles");
		gst_bin_add_many(pipeline, switch_subparse, sink, NULL);
		gst_element_link(switch_subparse, sink);
		g_object_set (G_OBJECT(sink), "signal-handoffs", TRUE, NULL);
		g_object_set (G_OBJECT(sink), "sync", TRUE, NULL);
		g_object_set (G_OBJECT(sink), "async", FALSE, NULL);
		g_signal_connect(sink, "handoff", G_CALLBACK(_this->gstCBsubtitleAvail), _this);
	
		// order is essential since requested sink pad names can't be explicitely chosen
		GstElement *switch_substream_plain = gst_element_factory_make ("input-selector", "switch_substream_plain");
		gst_bin_add(pipeline, switch_substream_plain);
		GstPad *sinkpad_plain = gst_element_get_request_pad (switch_subparse, "sink%d");
		gst_pad_link(gst_element_get_pad (switch_substream_plain, "src"), sinkpad_plain);
	
		GstElement *switch_substream_ssa = gst_element_factory_make ("input-selector", "switch_substream_ssa");
		GstElement *ssaparse = gst_element_factory_make("ssaparse", "ssaparse");
		gst_bin_add_many(pipeline, switch_substream_ssa, ssaparse, NULL);
		GstPad *sinkpad_ssa = gst_element_get_request_pad (switch_subparse, "sink%d");
		gst_element_link(switch_substream_ssa, ssaparse);
		gst_pad_link(gst_element_get_pad (ssaparse, "src"), sinkpad_ssa);
	
		GstElement *switch_substream_srt = gst_element_factory_make ("input-selector", "switch_substream_srt");
		GstElement *srtparse = gst_element_factory_make("subparse", "srtparse");
		gst_bin_add_many(pipeline, switch_substream_srt, srtparse, NULL);
		GstPad *sinkpad_srt = gst_element_get_request_pad (switch_subparse, "sink%d");
		gst_element_link(switch_substream_srt, srtparse);
		gst_pad_link(gst_element_get_pad (srtparse, "src"), sinkpad_srt);
		g_object_set (G_OBJECT(srtparse), "subtitle-encoding", "ISO-8859-15", NULL);
	}

	switch (type)
	{
		case stSSA:
			return gst_element_get_request_pad (gst_bin_get_by_name(pipeline,"switch_substream_ssa"), "sink%d");
		case stSRT:
			return gst_element_get_request_pad (gst_bin_get_by_name(pipeline,"switch_substream_srt"), "sink%d");
		case stPlainText:
		default:
			break;
	}
	return gst_element_get_request_pad (gst_bin_get_by_name(pipeline,"switch_substream_plain"), "sink%d");
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
	ePyObject entry;
	int tuplesize = PyTuple_Size(tuple);
	int pid;
	int type;
	gint nb_sources;
	GstPad *active_pad;
	GstElement *switch_substream = NULL;
	GstElement *switch_subparse = gst_bin_get_by_name (GST_BIN(m_gst_pipeline), "switch_subparse");

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

	switch ((subtype_t)type)
	{
		case stPlainText:
			switch_substream = gst_bin_get_by_name(GST_BIN(m_gst_pipeline),"switch_substream_plain");
			break;
		case stSSA:
			switch_substream = gst_bin_get_by_name(GST_BIN(m_gst_pipeline),"switch_substream_ssa");
			break;
		case stSRT:
			switch_substream = gst_bin_get_by_name(GST_BIN(m_gst_pipeline),"switch_substream_srt");
			break;
		default:
			goto error_out;
	}

	m_subtitle_widget = new eSubtitleWidget(parent);
	m_subtitle_widget->resize(parent->size()); /* full size */

	if ( !switch_substream )
	{
		eDebug("can't switch subtitle tracks! gst-plugin-selector needed");
		return -2;
	}
	g_object_get (G_OBJECT (switch_substream), "n-pads", &nb_sources, NULL);
 	if ( (unsigned int)pid >= m_subtitleStreams.size() || pid >= nb_sources || (unsigned int)m_currentSubtitleStream >= m_subtitleStreams.size() )
		return -2;
	g_object_get (G_OBJECT (switch_subparse), "n-pads", &nb_sources, NULL);
	if ( type < 0 || type >= nb_sources )
		return -2;

	char sinkpad[6];
	sprintf(sinkpad, "sink%d", type);
	g_object_set (G_OBJECT (switch_subparse), "active-pad", gst_element_get_pad (switch_subparse, sinkpad), NULL);
	sprintf(sinkpad, "sink%d", pid);
	g_object_set (G_OBJECT (switch_substream), "active-pad", gst_element_get_pad (switch_substream, sinkpad), NULL);
	m_currentSubtitleStream = pid;

	return 0;
error_out:
	eDebug("enableSubtitles needs a tuple as 2nd argument!\n"
		"for gst subtitles (2, subtitle_stream_count, subtitle_type)");
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
