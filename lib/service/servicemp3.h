#ifndef __servicemp3_h
#define __servicemp3_h

#include <gst/gst.h>
#include <lib/base/message.h>
#include <lib/dvb/metaparser.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/subtitle.h>
#include <lib/dvb/teletext.h>
#include <lib/service/iservice.h>
/* for subtitles */
#include <lib/gui/esubtitle.h>
#include <mutex>

class eStaticServiceMP3Info;

class eServiceFactoryMP3 : public iServiceHandler {
	DECLARE_REF(eServiceFactoryMP3);

public:
	eServiceFactoryMP3();
	virtual ~eServiceFactoryMP3();
	enum { id = eServiceReference::idServiceMP3 };

	// iServiceHandler
	RESULT play(const eServiceReference&, ePtr<iPlayableService>& ptr);
	RESULT record(const eServiceReference&, ePtr<iRecordableService>& ptr);
	RESULT list(const eServiceReference&, ePtr<iListableService>& ptr);
	RESULT info(const eServiceReference&, ePtr<iStaticServiceInformation>& ptr);
	RESULT offlineOperations(const eServiceReference&, ePtr<iServiceOfflineOperations>& ptr);
	gint m_eServicemp3_counter;

private:
	ePtr<eStaticServiceMP3Info> m_service_info;
};

class eStaticServiceMP3Info : public iStaticServiceInformation {
	DECLARE_REF(eStaticServiceMP3Info);
	friend class eServiceFactoryMP3;
	eStaticServiceMP3Info();
	eDVBMetaParser m_parser;

public:
	RESULT getName(const eServiceReference& ref, std::string& name);
	int getLength(const eServiceReference& ref);
	int getInfo(const eServiceReference& ref, int w);
	int isPlayable(const eServiceReference& ref, const eServiceReference& ignore, bool simulate) {
		return 1;
	}
	long long getFileSize(const eServiceReference& ref);
	RESULT getEvent(const eServiceReference& ref, ePtr<eServiceEvent>& ptr, time_t start_time);
};

class eStreamBufferInfo : public iStreamBufferInfo {
	DECLARE_REF(eStreamBufferInfo);
	int bufferPercentage;
	int inputRate;
	int outputRate;
	int bufferSpace;
	int bufferSize;

public:
	eStreamBufferInfo(int percentage, int inputrate, int outputrate, int space, int size);

	int getBufferPercentage() const;
	int getAverageInputRate() const;
	int getAverageOutputRate() const;
	int getBufferSpace() const;
	int getBufferSize() const;
};

class eServiceMP3InfoContainer : public iServiceInfoContainer {
	DECLARE_REF(eServiceMP3InfoContainer);

	double doubleValue;
	GstBuffer* bufferValue;

	unsigned char* bufferData;
	unsigned int bufferSize;
	GstMapInfo map;

public:
	eServiceMP3InfoContainer();
	~eServiceMP3InfoContainer();

	double getDouble(unsigned int index) const;
	unsigned char* getBuffer(unsigned int& size) const;
	void setDouble(double value);
	void setBuffer(GstBuffer* buffer);
};

class GstMessageContainer : public iObject {
	DECLARE_REF(GstMessageContainer);
	GstMessage* messagePointer;
	GstPad* messagePad;
	GstBuffer* messageBuffer;
	int messageType;

public:
	GstMessageContainer(int type, GstMessage* msg, GstPad* pad, GstBuffer* buffer) {
		messagePointer = msg;
		messagePad = pad;
		messageBuffer = buffer;
		messageType = type;
	}
	~GstMessageContainer() {
		if (messagePointer)
			gst_message_unref(messagePointer);
		if (messagePad)
			gst_object_unref(messagePad);
		if (messageBuffer)
			gst_buffer_unref(messageBuffer);
	}
	int getType() {
		return messageType;
	}
	operator GstMessage*() {
		return messagePointer;
	}
	operator GstPad*() {
		return messagePad;
	}
	operator GstBuffer*() {
		return messageBuffer;
	}
};

typedef struct _GstElement GstElement;

typedef enum { atUnknown, atMPEG, atMP3, atAC3, atDTS, atAAC, atPCM, atOGG, atFLAC, atWMA, atDRA, atEAC3 } audiotype_t;
typedef enum { stUnknown, stPlainText, stSSA, stASS, stSRT, stVOB, stPGS, stWebVTT, stDVB } subtype_t;
typedef enum {
	ctNone,
	ctMPEGTS,
	ctMPEGPS,
	ctMKV,
	ctAVI,
	ctMP4,
	ctVCD,
	ctCDA,
	ctASF,
	ctOGG,
	ctWEBM,
	ctDRA
} containertype_t;

class eServiceMP3 : public iPlayableService,
					public iPauseableService,
					public iServiceInformation,
					public iSeekableService,
					public iAudioTrackSelection,
					public iAudioChannelSelection,
					public iSubtitleOutput,
					public iStreamedService,
					public iAudioDelay,
					public sigc::trackable,
					public iCueSheet {
	DECLARE_REF(eServiceMP3);

public:
	virtual ~eServiceMP3();

	void setCacheEntry(bool isAudio, int pid);
	// iPlayableService
	RESULT connectEvent(const sigc::slot<void(iPlayableService*, int)>& event, ePtr<eConnection>& connection);
	RESULT start();
	RESULT stop();

	RESULT pause(ePtr<iPauseableService>& ptr);
	RESULT setSlowMotion(int ratio);
	RESULT setFastForward(int ratio);

	RESULT seek(ePtr<iSeekableService>& ptr);
	RESULT audioTracks(ePtr<iAudioTrackSelection>& ptr);
	RESULT audioChannel(ePtr<iAudioChannelSelection>& ptr);
	RESULT subtitle(ePtr<iSubtitleOutput>& ptr);
	RESULT audioDelay(ePtr<iAudioDelay>& ptr);
	RESULT cueSheet(ePtr<iCueSheet>& ptr);

	// not implemented (yet)
	RESULT setTarget(int target, bool noaudio = false) {
		return -1;
	}
	RESULT frontendInfo(ePtr<iFrontendInformation>& ptr) {
		ptr = nullptr;
		return -1;
	}
	RESULT subServices(ePtr<iSubserviceList>& ptr) {
		ptr = nullptr;
		return -1;
	}
	RESULT timeshift(ePtr<iTimeshiftService>& ptr) {
		ptr = nullptr;
		return -1;
	}
	RESULT tap(ePtr<iTapService>& ptr) {
		ptr = nullptr;
		return -1;
	};
	//	RESULT cueSheet(ePtr<iCueSheet> &ptr) { ptr = nullptr; return -1; }

	// iCueSheet
	PyObject* getCutList();
	void setCutList(SWIG_PYOBJECT(ePyObject));
	void setCutListEnable(int enable);

	RESULT rdsDecoder(ePtr<iRdsDecoder>& ptr) {
		ptr = nullptr;
		return -1;
	}
	RESULT keys(ePtr<iServiceKeys>& ptr) {
		ptr = nullptr;
		return -1;
	}
	RESULT stream(ePtr<iStreamableService>& ptr) {
		ptr = nullptr;
		return -1;
	}

	void setQpipMode(bool value, bool audio) {}

	// iPausableService
	RESULT pause();
	RESULT unpause();

	RESULT info(ePtr<iServiceInformation>&);

	// iSeekableService
	RESULT getLength(pts_t& SWIG_OUTPUT);
	RESULT seekTo(pts_t to);
	RESULT seekRelative(int direction, pts_t to);
	RESULT getPlayPosition(pts_t& SWIG_OUTPUT);
	RESULT setTrickmode(int trick);
	RESULT isCurrentlySeekable();

	// iServiceInformation
	RESULT getName(std::string& name);
	RESULT getEvent(ePtr<eServiceEvent>& evt, int nownext);
	int getInfo(int w);
	std::string getInfoString(int w);
	ePtr<iServiceInfoContainer> getInfoObject(int w);

	// iAudioTrackSelection
	int getNumberOfTracks();
	RESULT selectTrack(unsigned int i);
	RESULT getTrackInfo(struct iAudioTrackInfo&, unsigned int n);
	int getCurrentTrack();

	// iAudioChannelSelection
	int getCurrentChannel();
	RESULT selectChannel(int i);

	// iSubtitleOutput
	RESULT enableSubtitles(iSubtitleUser* user, SubtitleTrack& track);
	RESULT disableSubtitles();
	RESULT getSubtitleList(std::vector<SubtitleTrack>& sublist);
	RESULT getCachedSubtitle(SubtitleTrack& track);

	// iStreamedService
	RESULT streamed(ePtr<iStreamedService>& ptr);
	ePtr<iStreamBufferInfo> getBufferCharge();
	int setBufferSize(int size);

	// iAudioDelay
	int getAC3Delay();
	int getPCMDelay();
	void setAC3Delay(int);
	void setPCMDelay(int);

	struct audioStream {
		GstPad* pad;
		audiotype_t type;
		std::string language_code; /* iso-639, if available. */
		std::string codec; /* clear text codec description */
		std::string title;
		audioStream() : pad(0), type(atUnknown) {}
		bool operator==(const audioStream& lhs) const {
			return (lhs.type == type) && (lhs.language_code == language_code) && (lhs.codec == codec);
		}
		bool operator!=(const audioStream& lhs) const {
			return (lhs.type != type) || (lhs.language_code != language_code) || (lhs.codec != codec);
		}
	};
	struct subtitleStream {
		GstPad* pad;
		subtype_t type;
		std::string language_code; /* iso-639, if available. */
		std::string title;
		subtitleStream() : pad(0) {}
		bool operator==(const subtitleStream& lhs) const {
			return (lhs.type == type) && (lhs.language_code == language_code) && (lhs.title == title);
		}
		bool operator!=(const subtitleStream& lhs) const {
			return (lhs.type != type) || (lhs.language_code != language_code) || (lhs.title != title);
		}
	};
	struct sourceStream {
		audiotype_t audiotype;
		containertype_t containertype;
		gboolean is_audio;
		gboolean is_video;
		gboolean is_streaming;
		gboolean is_hls;
		sourceStream()
			: audiotype(atUnknown), containertype(ctNone), is_audio(FALSE), is_video(FALSE), is_streaming(FALSE),
			  is_hls(FALSE) {}
	};
	struct bufferInfo {
		gint bufferPercent;
		gint avgInRate;
		gint avgOutRate;
		gint64 bufferingLeft;
		bufferInfo() : bufferPercent(0), avgInRate(0), avgOutRate(0), bufferingLeft(-1) {}
	};
	struct errorInfo {
		std::string error_message;
		std::string missing_codec;
	};

protected:
	ePtr<eTimer> m_nownext_timer;
	ePtr<eServiceEvent> m_event_now, m_event_next;
	void updateEpgCacheNowNext();

	/* cuesheet */
	struct cueEntry {
		pts_t where;
		unsigned int what;

		bool operator<(const struct cueEntry& o) const {
			return where < o.where;
		}
		cueEntry(const pts_t& where, unsigned int what) : where(where), what(what) {}
	};

	std::multiset<cueEntry> m_cue_entries;
	int m_cuesheet_changed, m_cutlist_enabled;
	void loadCuesheet();
	void saveCuesheet();

private:
	static int pcm_delay;
	static int ac3_delay;
	int m_currentAudioStream;
	int m_currentSubtitleStream;
	int m_cachedSubtitleStream;
	int selectAudioStream(int i, bool skipAudioFix = false);
	std::vector<audioStream> m_audioStreams;
	std::vector<subtitleStream> m_subtitleStreams;
	iSubtitleUser* m_subtitle_widget;
	gdouble m_currentTrickRatio;
	friend class eServiceFactoryMP3;
	eServiceReference m_ref;
	int m_buffer_size;
	int m_ignore_buffering_messages;
	bool m_is_live;
	bool m_subtitles_paused;
	bool m_use_prefillbuffer;
	bool m_paused;
	bool m_clear_buffers;
	bool m_initial_start;
	bool m_send_ev_start;
	bool m_first_paused;
	/* cuesheet load check */
	bool m_cuesheet_loaded;
	bool m_audiosink_not_running;
	/* servicemMP3 chapter TOC support CVR */
	bool m_use_chapter_entries;
	/* last used seek position gst-1 only */
	gint64 m_last_seek_pos;
	pts_t m_media_lenght;
	ePtr<eTimer> m_play_position_timer;
	void playPositionTiming();
	gint m_last_seek_count;
	bool m_seeking_or_paused;
	bool m_to_paused;
	bufferInfo m_bufferInfo;
	errorInfo m_errorInfo;
	std::string m_download_buffer_path;
	eServiceMP3(eServiceReference ref);
	sigc::signal<void(iPlayableService*, int)> m_event;
	enum {
		stIdle,
		stRunning,
		stStopped,
	};
	int m_state;
	bool m_gstdot;
	GstElement* m_gst_playbin;
	GstTagList* m_stream_tags;
	bool m_coverart;
	std::list<eDVBSubtitlePage> m_dvb_subtitle_pages;

	eFixedMessagePump<ePtr<GstMessageContainer>> m_pump;

	audiotype_t gstCheckAudioPad(GstStructure* structure);
	void gstBusCall(GstMessage* msg);
	void handleMessage(GstMessage* msg);
	static GstBusSyncReply gstBusSyncHandler(GstBus* bus, GstMessage* message, gpointer user_data);
	static void gstTextpadHasCAPS(GstPad* pad, GParamSpec* unused, gpointer user_data);
	void gstTextpadHasCAPS_synced(GstPad* pad);
	static void gstCBsubtitleAvail(GstElement* element, GstBuffer* buffer, gpointer user_data);
	GstPad* gstCreateSubtitleSink(eServiceMP3* _this, subtype_t type);
	void gstPoll(ePtr<GstMessageContainer> const&);
	static void playbinNotifySource(GObject* object, GParamSpec* unused, gpointer user_data);
	/* TOC processing CVR */
	void HandleTocEntry(GstMessage* msg);
	static gint match_sinktype(const GValue* velement, const gchar* type);
	static void handleElementAdded(GstBin* bin, GstElement* element, gpointer user_data);

	struct subtitle_page_t {
		uint32_t start_ms;
		uint32_t end_ms;
		int64_t vtt_mpegts_base;
		std::string text;

		subtitle_page_t(uint32_t start_ms_in, uint32_t end_ms_in, const std::string& text_in)
			: start_ms(start_ms_in), end_ms(end_ms_in), vtt_mpegts_base(0), text(text_in) {}
	};

	typedef std::map<uint32_t, subtitle_page_t> subtitle_pages_map_t;
	typedef std::pair<uint32_t, subtitle_page_t> subtitle_pages_map_pair_t;
	subtitle_pages_map_t m_subtitle_pages;
	ePtr<eTimer> m_subtitle_sync_timer;
	ePtr<eTimer> m_dvb_subtitle_sync_timer;
#ifdef PASSTHROUGH_FIX
	ePtr<eTimer> m_passthrough_fix_timer;
#endif
	ePtr<eDVBSubtitleParser> m_dvb_subtitle_parser;
	ePtr<eConnection> m_new_dvb_subtitle_page_connection;
	void newDVBSubtitlePage(const eDVBSubtitlePage& p);

	pts_t m_prev_decoder_time;
	int m_decoder_time_valid_state;
	int64_t m_initial_vtt_mpegts;
	int64_t m_vtt_live_base_time;
	bool m_vtt_live;

	void pushDVBSubtitles();
	void pushSubtitles();
	void pullSubtitle(GstBuffer* buffer);
	void sourceTimeout();
	void clearBuffers(bool force = false);
#ifdef PASSTHROUGH_FIX
	void forcePassthrough();
#endif
	sourceStream m_sourceinfo;
	gulong m_subs_to_pull_handler_id, m_notify_source_handler_id, m_notify_element_added_handler_id;

	RESULT seekToImpl(pts_t to);

	gint m_aspect, m_width, m_height, m_framerate, m_progressive, m_gamma;
	std::string m_useragent;
	std::string m_extra_headers;
	RESULT trickSeek(gdouble ratio);
	ePtr<iTSMPEGDecoder> m_decoder; // for showSinglePic when radio
	int64_t getLiveDecoderTime();
	std::mutex m_subtitle_pages_mutex;

	std::string m_external_subtitle_path;
	std::string m_external_subtitle_language;
	std::string m_external_subtitle_extension;
};

#endif
