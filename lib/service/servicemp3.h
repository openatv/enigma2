#ifndef __servicemp3_h
#define __servicemp3_h

#ifdef HAVE_GSTREAMER
#include <lib/base/message.h>
#include <lib/service/iservice.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/subtitle.h>
#include <lib/dvb/teletext.h>
#include <gst/gst.h>

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
};

typedef struct _GstElement GstElement;

class eServiceMP3: public iPlayableService, public iPauseableService, 
	public iServiceInformation, public iSeekableService, public iAudioTrackSelection, public iAudioChannelSelection, public iSubtitleOutput, public Object
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

		// not implemented (yet)
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) { ptr = 0; return -1; }
	RESULT subServices(ePtr<iSubserviceList> &ptr) { ptr = 0; return -1; }
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) { ptr = 0; return -1; }
	RESULT cueSheet(ePtr<iCueSheet> &ptr) { ptr = 0; return -1; }
	RESULT audioDelay(ePtr<iAudioDelay> &ptr) { ptr = 0; return -1; }
	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = 0; return -1; }
	RESULT stream(ePtr<iStreamableService> &ptr) { ptr = 0; return -1; }
	RESULT keys(ePtr<iServiceKeys> &ptr) { ptr = 0; return -1; }

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

	struct audioStream
	{
		GstPad* pad;
		enum { atMP2, atMP3, atAC3, atDTS, atAAC, atPCM, atOGG };
		int type; // mpeg2, ac3, dts, ...
		std::string language_code; /* iso-639, if available. */
	};
	struct subtitleStream
	{
		GstElement* element;
		std::string language_code; /* iso-639, if available. */
	};
private:
	int m_currentAudioStream;
	int m_currentSubtitleStream;
	int selectAudioStream(int i);
	std::vector<audioStream> m_audioStreams;
	std::vector<subtitleStream> m_subtitleStreams;
	eSubtitleWidget *m_subtitle_widget;
	int m_currentTrickRatio;
	eTimer m_seekTimeout;
	void eServiceMP3::seekTimeoutCB();
	friend class eServiceFactoryMP3;
	std::string m_filename;
	eServiceMP3(const char *filename);
	Signal2<void,iPlayableService*,int> m_event;
	enum
	{
		stIdle, stRunning, stStopped,
	};
	int m_state;
	GstElement *m_gst_pipeline;
	GstTagList *m_stream_tags;
	eFixedMessagePump<int> m_pump;

	void gstBusCall(GstBus *bus, GstMessage *msg);
	static GstBusSyncReply gstBusSyncHandler(GstBus *bus, GstMessage *message, gpointer user_data);
	static void gstCBpadAdded(GstElement *decodebin, GstPad *pad, gpointer data); /* for mpegdemux */
	static void gstCBfilterPadAdded(GstElement *filter, GstPad *pad, gpointer user_data); /* for id3demux */
	static void gstCBnewPad(GstElement *decodebin, GstPad *pad, gboolean last, gpointer data); /* for decodebin */
	static void gstCBunknownType(GstElement *decodebin, GstPad *pad, GstCaps *l, gpointer data);
	static void gstCBsubtitleAvail(GstElement *element, GstBuffer *buffer, GstPad *pad, gpointer user_data);
	void gstPoll(const int&);
};
#endif

#endif
