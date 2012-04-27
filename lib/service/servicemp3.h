#ifndef __servicemp3_h
#define __servicemp3_h

#include <lib/base/message.h>
#include <lib/service/iservice.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/subtitle.h>
#include <lib/dvb/teletext.h>
#include <gst/gst.h>
/* for subtitles */
#include <lib/gui/esubtitle.h>

class eStaticServiceMP3Info;

class eSubtitleWidget;

class eServiceFactoryMP3: public iServiceHandler
{
	DECLARE_REF(eServiceFactoryMP3);
public:
	eServiceFactoryMP3();
	virtual ~eServiceFactoryMP3();
	enum { id = 0x1001 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
private:
	ePtr<eStaticServiceMP3Info> m_service_info;
};

class eStaticServiceMP3Info: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceMP3Info);
	friend class eServiceFactoryMP3;
	eStaticServiceMP3Info();
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	int getInfo(const eServiceReference &ref, int w);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate) { return 1; }
	PyObject* getInfoObject(const eServiceReference &ref, int w);
};

typedef struct _GstElement GstElement;

typedef enum { atUnknown, atMPEG, atMP3, atAC3, atDTS, atAAC, atPCM, atOGG, atFLAC, atWMA } audiotype_t;
typedef enum { stUnknown, stPlainText, stSSA, stASS, stSRT, stVOB, stPGS } subtype_t;
typedef enum { ctNone, ctMPEGTS, ctMPEGPS, ctMKV, ctAVI, ctMP4, ctVCD, ctCDA, ctASF } containertype_t;

class eServiceMP3: public iPlayableService, public iPauseableService,
	public iServiceInformation, public iSeekableService, public iAudioTrackSelection, public iAudioChannelSelection, 
	public iSubtitleOutput, public iStreamedService, public iAudioDelay, public Object
{
	DECLARE_REF(eServiceMP3);
public:
	virtual ~eServiceMP3();

		// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT setTarget(int target);
	
	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT setSlowMotion(int ratio);
	RESULT setFastForward(int ratio);

	RESULT seek(ePtr<iSeekableService> &ptr);
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr);
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr);
	RESULT subtitle(ePtr<iSubtitleOutput> &ptr);
	RESULT audioDelay(ePtr<iAudioDelay> &ptr);

		// not implemented (yet)
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) { ptr = 0; return -1; }
	RESULT subServices(ePtr<iSubserviceList> &ptr) { ptr = 0; return -1; }
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) { ptr = 0; return -1; }
	RESULT cueSheet(ePtr<iCueSheet> &ptr) { ptr = 0; return -1; }

	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = 0; return -1; }
	RESULT keys(ePtr<iServiceKeys> &ptr) { ptr = 0; return -1; }
	RESULT stream(ePtr<iStreamableService> &ptr) { ptr = 0; return -1; }

		// iPausableService
	RESULT pause();
	RESULT unpause();
	
	RESULT info(ePtr<iServiceInformation>&);
	
		// iSeekableService
	RESULT getLength(pts_t &SWIG_OUTPUT);
	RESULT seekTo(pts_t to);
	RESULT seekRelative(int direction, pts_t to);
	RESULT getPlayPosition(pts_t &SWIG_OUTPUT);
	RESULT setTrickmode(int trick);
	RESULT isCurrentlySeekable();

		// iServiceInformation
	RESULT getName(std::string &name);
	int getInfo(int w);
	std::string getInfoString(int w);
	PyObject *getInfoObject(int w);

		// iAudioTrackSelection	
	int getNumberOfTracks();
	RESULT selectTrack(unsigned int i);
	RESULT getTrackInfo(struct iAudioTrackInfo &, unsigned int n);
	int getCurrentTrack();

		// iAudioChannelSelection	
	int getCurrentChannel();
	RESULT selectChannel(int i);

		// iSubtitleOutput
	RESULT enableSubtitles(eWidget *parent, SWIG_PYOBJECT(ePyObject) entry);
	RESULT disableSubtitles(eWidget *parent);
	PyObject *getSubtitleList();
	PyObject *getCachedSubtitle();

		// iStreamedService
	RESULT streamed(ePtr<iStreamedService> &ptr);
	PyObject *getBufferCharge();
	int setBufferSize(int size);

		// iAudioDelay
	int getAC3Delay();
	int getPCMDelay();
	void setAC3Delay(int);
	void setPCMDelay(int);

	struct audioStream
	{
		GstPad* pad;
		audiotype_t type;
		std::string language_code; /* iso-639, if available. */
		std::string codec; /* clear text codec description */
		audioStream()
			:pad(0), type(atUnknown)
		{
		}
	};
	struct subtitleStream
	{
		GstPad* pad;
		subtype_t type;
		std::string language_code; /* iso-639, if available. */
		subtitleStream()
			:pad(0)
		{
		}
	};
	struct sourceStream
	{
		audiotype_t audiotype;
		containertype_t containertype;
		bool is_video;
		bool is_streaming;
		sourceStream()
			:audiotype(atUnknown), containertype(ctNone), is_video(FALSE), is_streaming(FALSE)
		{
		}
	};
	struct bufferInfo
	{
		gint bufferPercent;
		gint avgInRate;
		gint avgOutRate;
		gint64 bufferingLeft;
		bufferInfo()
			:bufferPercent(0), avgInRate(0), avgOutRate(0), bufferingLeft(-1)
		{
		}
	};
	struct errorInfo
	{
		std::string error_message;
		std::string missing_codec;
	};

private:
	static int pcm_delay;
	static int ac3_delay;
	int m_currentAudioStream;
	int m_currentSubtitleStream;
	int m_cachedSubtitleStream;
	int selectAudioStream(int i);
	std::vector<audioStream> m_audioStreams;
	std::vector<subtitleStream> m_subtitleStreams;
	eSubtitleWidget *m_subtitle_widget;
	gdouble m_currentTrickRatio;
	friend class eServiceFactoryMP3;
	eServiceReference m_ref;
	int m_buffer_size;
	gint64 m_buffer_duration;
	bool m_use_prefillbuffer;
	bufferInfo m_bufferInfo;
	errorInfo m_errorInfo;
	eServiceMP3(eServiceReference ref);
	Signal2<void,iPlayableService*,int> m_event;
	enum
	{
		stIdle, stRunning, stStopped,
	};
	int m_state;
	GstElement *m_gst_playbin, *audioSink, *videoSink;
	GstTagList *m_stream_tags;

	class GstMessageContainer: public iObject
	{
		DECLARE_REF(GstMessageContainer);
		GstMessage *messagePointer;
		GstPad *messagePad;
		GstBuffer *messageBuffer;
		int messageType;

	public:
		GstMessageContainer(int type, GstMessage *msg, GstPad *pad, GstBuffer *buffer)
		{
			messagePointer = msg;
			messagePad = pad;
			messageBuffer = buffer;
			messageType = type;
		}
		~GstMessageContainer()
		{
			if (messagePointer) gst_message_unref(messagePointer);
			if (messagePad) gst_object_unref(messagePad);
			if (messageBuffer) gst_buffer_unref(messageBuffer);
		}
		int getType() { return messageType; }
		operator GstMessage *() { return messagePointer; }
		operator GstPad *() { return messagePad; }
		operator GstBuffer *() { return messageBuffer; }
	};
	eFixedMessagePump<ePtr<GstMessageContainer> > m_pump;

	audiotype_t gstCheckAudioPad(GstStructure* structure);
	void gstBusCall(GstMessage *msg);
	void handleMessage(GstMessage *msg);
	static GstBusSyncReply gstBusSyncHandler(GstBus *bus, GstMessage *message, gpointer user_data);
	static void gstTextpadHasCAPS(GstPad *pad, GParamSpec * unused, gpointer user_data);
	void gstTextpadHasCAPS_synced(GstPad *pad);
	static void gstCBsubtitleAvail(GstElement *element, GstBuffer *buffer, gpointer user_data);
	GstPad* gstCreateSubtitleSink(eServiceMP3* _this, subtype_t type);
	void gstPoll(ePtr<GstMessageContainer> const &);
	static void gstHTTPSourceSetAgent(GObject *source, GParamSpec *unused, gpointer user_data);
	static gint match_sinktype(GstElement *element, gpointer type);

	struct SubtitlePage
	{
		enum { Unknown, Pango, Vob } type;
		ePangoSubtitlePage pango_page;
		eVobSubtitlePage vob_page;
	};

	std::list<SubtitlePage> m_subtitle_pages;
	ePtr<eTimer> m_subtitle_sync_timer;
	
	ePtr<eTimer> m_streamingsrc_timeout;
	pts_t m_prev_decoder_time;
	int m_decoder_time_valid_state;

	void pushSubtitles();
	void pullSubtitle(GstBuffer *buffer);
	void sourceTimeout();
	sourceStream m_sourceinfo;
	gulong m_subs_to_pull_handler_id;

	RESULT seekToImpl(pts_t to);

	gint m_aspect, m_width, m_height, m_framerate, m_progressive;
	std::string m_useragent;
	RESULT trickSeek(gdouble ratio);
};

#endif
