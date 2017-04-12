#ifndef __servicemp3record_h
#define __servicemp3record_h

#include <lib/service/iservice.h>
#include <lib/service/servicemp3.h>
#include <lib/dvb/idvb.h>
#include <gst/gst.h>

class eServiceMP3Record:
	public iRecordableService,
	public sigc::trackable
{
	DECLARE_REF(eServiceMP3Record);
public:
	RESULT connectEvent(const sigc::slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection);
	RESULT prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id, const char *name, const char *descr, const char *tags, bool descramble, bool recordecm);
	RESULT prepareStreaming(bool descramble, bool includeecm);
	RESULT start(bool simulate=false);
	RESULT stop();
	RESULT stream(ePtr<iStreamableService> &ptr);
	RESULT getError(int &error) { error = m_error; return 0; };
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr);
	RESULT subServices(ePtr<iSubserviceList> &ptr);
	RESULT getFilenameExtension(std::string &ext) { ext = ".stream"; return 0; };

private:
	enum { stateIdle, statePrepared, stateRecording };
	GstElement* m_recording_pipeline;
	GstElement* m_source;
	bool m_simulate;
	int m_state;
	int m_error;
	std::string m_filename;
	eServiceReference m_ref;
	ePtr<eConnection> m_con_record_event;
	ePtr<eTimer> m_streamingsrc_timeout;
	std::string m_useragent;
	std::string m_extra_headers;
	eFixedMessagePump<ePtr<GstMessageContainer> > m_pump;

	friend class eServiceFactoryMP3;
	eServiceMP3Record(const eServiceReference &ref);
	~eServiceMP3Record();

	int doRecord();
	int doPrepare();
	void gstPoll(ePtr<GstMessageContainer> const &);
	void sourceTimeout();
	void gstBusCall(GstMessage *msg);
	void handleMessage(GstMessage *msg);
	static GstBusSyncReply gstBusSyncHandler(GstBus *bus, GstMessage *message, gpointer user_data);
	static void handleUridecNotifySource(GObject *object, GParamSpec *unused, gpointer user_data);
	static void handlePadAdded(GstElement *element, GstPad *pad, gpointer user_data);
	static gboolean handleAutoPlugCont(GstElement *bin, GstPad *pad, GstCaps *caps, gpointer user_data);

			/* events */
	sigc::signal2<void,iRecordableService*,int> m_event;
};

#endif
