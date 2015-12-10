#include <lib/service/servicemp3record.h>
#include <lib/base/eerror.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/metaparser.h>
#include <lib/base/httpstream.h>
#include <lib/base/nconfig.h>
#include <lib/nav/core.h>

#include <gst/gst.h>
#include <gst/pbutils/missing-plugins.h>

#define HTTP_TIMEOUT 60

DEFINE_REF(eServiceMP3Record);

eServiceMP3Record::eServiceMP3Record(const eServiceReference &ref):
	m_ref(ref),
	m_streamingsrc_timeout(eTimer::create(eApp)),
	m_pump(eApp, 1)
{
	m_state = stateIdle;
	m_error = 0;
	m_simulate = false;
	m_recording_pipeline = 0;
	m_useragent = "Enigma2 Mediaplayer";
	m_extra_headers = "";

	CONNECT(m_pump.recv_msg, eServiceMP3Record::gstPoll);
	CONNECT(m_streamingsrc_timeout->timeout, eServiceMP3Record::sourceTimeout);
}

eServiceMP3Record::~eServiceMP3Record()
{
	if (m_recording_pipeline)
	{
		// disconnect sync handler callback
		GstBus *bus = gst_pipeline_get_bus(GST_PIPELINE(m_recording_pipeline));
#if GST_VERSION_MAJOR < 1
		gst_bus_set_sync_handler(bus, NULL, NULL);
#else
		gst_bus_set_sync_handler(bus, NULL, NULL, NULL);
#endif
		gst_object_unref(bus);
	}

	if (m_state > stateIdle)
		stop();

	if (m_recording_pipeline)
	{
		gst_object_unref(GST_OBJECT(m_recording_pipeline));
	}
}

RESULT eServiceMP3Record::prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id, const char *name, const char *descr, const char *tags, bool descramble, bool recordecm)
{
	eDebug("[eMP3ServiceRecord] prepare filename %s", filename);
	m_filename = filename;

	if (m_state == stateIdle)
	{
		int ret = doPrepare();
		if (!ret)
		{
			eDVBMetaParser meta;
			std::string service_data;

			meta.m_time_create = begTime;
			meta.m_ref = eServiceReferenceDVB(m_ref.toString());
			meta.m_data_ok = 1;
			meta.m_service_data = service_data;
			if (name)
				meta.m_name = name;
			if (descr)
				meta.m_description = descr;
			if (tags)
				meta.m_tags = tags;
			meta.m_scrambled = recordecm; /* assume we will record scrambled data, when ecm will be included in the recording */
			ret = meta.updateMeta(m_filename.c_str()) ? -255 : 0;
			if (!ret)
			{
				std::string fname = m_filename;
				fname += "eit";
				eEPGCache::getInstance()->saveEventToFile(fname.c_str(), m_ref, eit_event_id, begTime, endTime);
			}
			m_state = statePrepared;
		}
		return ret;
	}
	return -1;
}

RESULT eServiceMP3Record::prepareStreaming(bool descramble, bool includeecm)
{
	return -1;
}

RESULT eServiceMP3Record::start(bool simulate)
{
	m_simulate = simulate;
	m_event((iRecordableService*)this, evStart);
	if (simulate)
		return 0;
	return doRecord();
}

RESULT eServiceMP3Record::stop()
{
	if (!m_simulate)
		eDebug("[eMP3ServiceRecord] stop recording");
	if (m_state == stateRecording)
	{
		gst_element_set_state(m_recording_pipeline, GST_STATE_NULL);
		m_state = statePrepared;
	} else if (!m_simulate)
		eDebug("[eMP3ServiceRecord] stop was not recording");
	if (m_state == statePrepared)
	{
		if (m_streamingsrc_timeout)
			m_streamingsrc_timeout->stop();
		m_state = stateIdle;
	}
	m_event((iRecordableService*)this, evRecordStopped);
	return 0;
}

int eServiceMP3Record::doPrepare()
{
	if (m_state == stateIdle)
	{
		gchar *uri;
		size_t pos = m_ref.path.find('#');
		std::string stream_uri;
		if (pos != std::string::npos && (m_ref.path.compare(0, 4, "http") == 0 || m_ref.path.compare(0, 4, "rtsp") == 0))
		{
			stream_uri = m_ref.path.substr(0, pos);
			m_extra_headers = m_ref.path.substr(pos + 1);

			pos = m_extra_headers.find("User-Agent=");
			if (pos != std::string::npos)
			{
				size_t hpos_start = pos + 11;
				size_t hpos_end = m_extra_headers.find('&', hpos_start);
				if (hpos_end != std::string::npos)
					m_useragent = m_extra_headers.substr(hpos_start, hpos_end - hpos_start);
				else
					m_useragent = m_extra_headers.substr(hpos_start);
			}

		}
		else
		{
			stream_uri = m_ref.path;
		}
		eDebug("[eMP3ServiceRecord] doPrepare uri=%s", stream_uri.c_str());
		uri = g_strdup_printf ("%s", stream_uri.c_str());

		m_recording_pipeline = gst_pipeline_new ("recording-pipeline");
		m_source = gst_element_factory_make("uridecodebin", "uridec");
		GstElement* sink = gst_element_factory_make("filesink", "fsink");

		// set uridecodebin properties and notify
		g_object_set(m_source, "uri", uri, NULL);
		g_object_set(m_source, "caps", gst_caps_from_string("video/mpegts;video/x-flv;video/x-matroska;video/quicktime;video/x-msvideo;video/x-ms-asf;audio/mpeg;audio/x-flac;audio/x-ac3"), NULL);
		g_signal_connect(m_source, "notify::source", G_CALLBACK(handleUridecNotifySource), this);
		g_signal_connect(m_source, "pad-added", G_CALLBACK(handlePadAdded), sink);
		g_signal_connect(m_source, "autoplug-continue", G_CALLBACK(handleAutoPlugCont), this);

		// set sink properties
		g_object_set(sink, "location", m_filename.c_str(), NULL);

		g_free(uri);
		if (m_recording_pipeline && m_source && sink)
		{
			gst_bin_add_many(GST_BIN(m_recording_pipeline), m_source, sink, NULL);

			GstBus *bus = gst_pipeline_get_bus(GST_PIPELINE(m_recording_pipeline));
#if GST_VERSION_MAJOR < 1
			gst_bus_set_sync_handler(bus, gstBusSyncHandler, this);
#else
			gst_bus_set_sync_handler(bus, gstBusSyncHandler, this, NULL);
#endif
			gst_object_unref(bus);
		}
		else
		{
			m_recording_pipeline = 0;
			eDebug("[eServiceMP3Record] doPrepare Sorry, cannot record: Failed to create GStreamer pipeline!");
			return -1;
		}
	}
	return 0;
}

int eServiceMP3Record::doRecord()
{
	int err = doPrepare();
	if (err)
	{
		m_error = errMisconfiguration;
		m_event((iRecordableService*)this, evRecordFailed);
		return err;
	}

	if (gst_element_set_state(m_recording_pipeline, GST_STATE_PLAYING) == GST_STATE_CHANGE_FAILURE)
	{
		eDebug("[eMP3ServiceRecord] doRecord error cannot set pipeline to state_playing");
		m_error = errMisconfiguration;
		m_event((iRecordableService*)this, evRecordFailed);
		return -1;
	}

	m_state = stateRecording;
	m_error = 0;
	m_event((iRecordableService*)this, evRecordRunning);
	return 0;
}

void eServiceMP3Record::gstPoll(ePtr<GstMessageContainer> const &msg)
{
	switch (msg->getType())
	{
		case 1:
		{
			GstMessage *gstmessage = *((GstMessageContainer*)msg);
			if (gstmessage)
			{
				gstBusCall(gstmessage);
			}
			break;
		}
		default:
			eDebug("[eMP3ServiceRecord] gstPoll error unknown message type");
	}
}

void eServiceMP3Record::sourceTimeout()
{
	eDebug("[eMP3ServiceRecord] sourceTimeout recording failed");
	m_event((iRecordableService*)this, evRecordFailed);
}

void eServiceMP3Record::gstBusCall(GstMessage *msg)
{
	if (!msg)
		return;
	ePtr<iRecordableService> ptr = this;
	gchar *sourceName;
	GstObject *source;
	source = GST_MESSAGE_SRC(msg);
	if (!GST_IS_OBJECT(source))
		return;
	sourceName = gst_object_get_name(source);
	switch (GST_MESSAGE_TYPE (msg))
	{
		case GST_MESSAGE_EOS:
			eDebug("[eMP3ServiceRecord] gstBusCall eos event");
			// Stream end -> stop recording
			m_event((iRecordableService*)this, evGstRecordEnded);
			break;
		case GST_MESSAGE_STATE_CHANGED:
		{
			if(GST_MESSAGE_SRC(msg) != GST_OBJECT(m_recording_pipeline))
				break;

			GstState old_state, new_state;
			gst_message_parse_state_changed(msg, &old_state, &new_state, NULL);

			if(old_state == new_state)
				break;

			GstStateChange transition = (GstStateChange)GST_STATE_TRANSITION(old_state, new_state);
			eDebug("[eMP3ServiceRecord] gstBusCall state transition %s -> %s", gst_element_state_get_name(old_state), gst_element_state_get_name(new_state));
			switch(transition)
			{
				case GST_STATE_CHANGE_PAUSED_TO_PLAYING:
				{
					if (m_streamingsrc_timeout)
						m_streamingsrc_timeout->stop();
					break;
				}
				default:
					break;
			}
			break;
		}
		case GST_MESSAGE_ERROR:
		{
			gchar *debug;
			GError *err;
			gst_message_parse_error(msg, &err, &debug);
			g_free(debug);
			if (err->code != GST_STREAM_ERROR_CODEC_NOT_FOUND)
				eWarning("[eServiceMP3Record] gstBusCall Gstreamer error: %s (%i) from %s", err->message, err->code, sourceName);
			g_error_free(err);
			break;
		}
		case GST_MESSAGE_ELEMENT:
		{
			const GstStructure *msgstruct = gst_message_get_structure(msg);
			if (msgstruct)
			{
				if (gst_is_missing_plugin_message(msg))
				{
					GstCaps *caps = NULL;
					gst_structure_get (msgstruct, "detail", GST_TYPE_CAPS, &caps, NULL);
					if (caps)
					{
						std::string codec = (const char*) gst_caps_to_string(caps);
						eDebug("[eServiceMP3Record] gstBusCall cannot record because of incompatible codecs %s", codec.c_str());
						gst_caps_unref(caps);
					}
				}
				else
				{
					const gchar *eventname = gst_structure_get_name(msgstruct);
					if (eventname)
					{
						if (!strcmp(eventname, "redirect"))
						{
							const char *uri = gst_structure_get_string(msgstruct, "new-location");
							eDebug("[eServiceMP3Record] gstBusCall redirect to %s", uri);
							gst_element_set_state (m_recording_pipeline, GST_STATE_NULL);
							g_object_set(G_OBJECT (m_source), "uri", uri, NULL);
							gst_element_set_state (m_recording_pipeline, GST_STATE_PLAYING);
						}
					}
				}
			}
			break;
		}
		case GST_MESSAGE_STREAM_STATUS:
		{
			GstStreamStatusType type;
			GstElement *owner;
			gst_message_parse_stream_status (msg, &type, &owner);
			if (type == GST_STREAM_STATUS_TYPE_CREATE)
			{
				if (GST_IS_PAD(source))
					owner = gst_pad_get_parent_element(GST_PAD(source));
				else if (GST_IS_ELEMENT(source))
					owner = GST_ELEMENT(source);
				else
					owner = 0;
				if (owner)
				{
					GstState state;
					gst_element_get_state(m_recording_pipeline, &state, NULL, 0LL);
					GstElementFactory *factory = gst_element_get_factory(GST_ELEMENT(owner));
					const gchar *name = gst_plugin_feature_get_name(GST_PLUGIN_FEATURE(factory));
					if (!strcmp(name, "souphttpsrc") && (state == GST_STATE_READY) && !m_streamingsrc_timeout->isActive())
					{
						m_streamingsrc_timeout->start(HTTP_TIMEOUT*1000, true);
						g_object_set (G_OBJECT (owner), "timeout", HTTP_TIMEOUT, NULL);
						eDebug("[eServiceMP3Record] gstBusCall setting timeout on %s to %is", name, HTTP_TIMEOUT);
					}
				}
				if (GST_IS_PAD(source))
					gst_object_unref(owner);
			}
			break;
		}
		default:
			break;
	}
	g_free(sourceName);
}

void eServiceMP3Record::handleMessage(GstMessage *msg)
{
	if (GST_MESSAGE_TYPE(msg) == GST_MESSAGE_STATE_CHANGED && GST_MESSAGE_SRC(msg) != GST_OBJECT(m_recording_pipeline))
	{
		/*
		 * ignore verbose state change messages for all active elements;
		 * we only need to handle state-change events for the recording pipeline
		 */
		gst_message_unref(msg);
		return;
	}
	m_pump.send(new GstMessageContainer(1, msg, NULL, NULL));
}

GstBusSyncReply eServiceMP3Record::gstBusSyncHandler(GstBus *bus, GstMessage *message, gpointer user_data)
{
	eServiceMP3Record *_this = (eServiceMP3Record*)user_data;
	if (_this) _this->handleMessage(message);
	return GST_BUS_DROP;
}

void eServiceMP3Record::handleUridecNotifySource(GObject *object, GParamSpec *unused, gpointer user_data)
{
	GstElement *source = NULL;
	eServiceMP3Record *_this = (eServiceMP3Record*)user_data;
	g_object_get(object, "source", &source, NULL);
	if (source)
	{
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(source), "ssl-strict") != 0)
		{
			g_object_set(G_OBJECT(source), "ssl-strict", FALSE, NULL);
		}
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(source), "user-agent") != 0 && !_this->m_useragent.empty())
		{
			g_object_set(G_OBJECT(source), "user-agent", _this->m_useragent.c_str(), NULL);
		}
		if (g_object_class_find_property(G_OBJECT_GET_CLASS(source), "extra-headers") != 0 && !_this->m_extra_headers.empty())
		{
#if GST_VERSION_MAJOR < 1
			GstStructure *extras = gst_structure_empty_new("extras");
#else
			GstStructure *extras = gst_structure_new_empty("extras");
#endif
			size_t pos = 0;
			while (pos != std::string::npos)
			{
				std::string name, value;
				size_t start = pos;
				size_t len = std::string::npos;
				pos = _this->m_extra_headers.find('=', pos);
				if (pos != std::string::npos)
				{
					len = pos - start;
					pos++;
					name = _this->m_extra_headers.substr(start, len);
					start = pos;
					len = std::string::npos;
					pos = _this->m_extra_headers.find('&', pos);
					if (pos != std::string::npos)
					{
						len = pos - start;
						pos++;
					}
					value = _this->m_extra_headers.substr(start, len);
				}
				if (!name.empty() && !value.empty())
				{
					GValue header;
					eDebug("[eServiceMP3Record] handleUridecNotifySource setting extra-header '%s:%s'", name.c_str(), value.c_str());
					memset(&header, 0, sizeof(GValue));
					g_value_init(&header, G_TYPE_STRING);
					g_value_set_string(&header, value.c_str());
					gst_structure_set_value(extras, name.c_str(), &header);
				}
				else
				{
					eDebug("[eServiceMP3Record] handleUridecNotifySource invalid header format %s", _this->m_extra_headers.c_str());
					break;
				}
			}
			if (gst_structure_n_fields(extras) > 0)
			{
				g_object_set(G_OBJECT(source), "extra-headers", extras, NULL);
			}
			gst_structure_free(extras);
		}
		gst_object_unref(source);
	}
}

void eServiceMP3Record::handlePadAdded(GstElement *element, GstPad *pad, gpointer user_data)
{
	GstElement *sink= (GstElement*)user_data;
	GstPad *filesink_pad = gst_element_get_static_pad(sink, "sink");
	if (gst_pad_is_linked(filesink_pad))
	{
		gst_object_unref(filesink_pad);
		return;
	}

	if (gst_pad_link(pad, filesink_pad) != GST_PAD_LINK_OK)
	{
		eDebug("[eServiceMP3Record] handlePadAdded cannot link uridecodebin with filesink");
	}
	else
	{
		eDebug("[eServiceMP3Record] handlePadAdded pads linked -> recording starts");
	}
	gst_object_unref(filesink_pad);
}

gboolean eServiceMP3Record::handleAutoPlugCont(GstElement *bin, GstPad *pad, GstCaps *caps, gpointer user_data)
{
	eDebug("[eMP3ServiceRecord] handleAutoPlugCont found caps %s", gst_caps_to_string(caps));
	return true;
}

RESULT eServiceMP3Record::frontendInfo(ePtr<iFrontendInformation> &ptr)
{
	ptr = 0;
	return -1;
}

RESULT eServiceMP3Record::connectEvent(const Slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iRecordableService*)this, m_event.connect(event));
	return 0;
}

RESULT eServiceMP3Record::stream(ePtr<iStreamableService> &ptr)
{
	ptr = 0;
	return -1;
}

RESULT eServiceMP3Record::subServices(ePtr<iSubserviceList> &ptr)
{
	ptr = 0;
	return -1;
}
