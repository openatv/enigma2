#ifndef __dvbsoftdecoder_h
#define __dvbsoftdecoder_h

#include <lib/base/object.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/idvb.h>

#include <lib/service/iservice.h>
#include <sigc++/sigc++.h>
#include <set>

class eDVBCSASession;
class eDVBService;

/**
 * eDVBSoftDecoder - Decoder-Proxy for Live-TV with Software Descrambling
 *
 * Reads scrambled TS from demux, passes to eDVBCSASession
 * for descrambling, and feeds the hardware decoder.
 *
 * Reacts to the 'activated' signal from the session.
 * When session activates (CSA-ALT detected), sets up PVR playback.
 */
class eDVBSoftDecoder : public iObject, public sigc::trackable
{
	DECLARE_REF(eDVBSoftDecoder);

public:
	/**
	 * Constructor
	 * @param source_handler PMT-Handler of Live-TV source
	 * @param dvb_service Service object
	 * @param decoder_index Decoder index (0, 1, ...)
	 */
	eDVBSoftDecoder(eDVBServicePMTHandler& source_handler,
	                ePtr<eDVBService> dvb_service,
	                int decoder_index);
	~eDVBSoftDecoder();

	// Assign session (connects 'activated' signal)
	void setSession(ePtr<eDVBCSASession> session);

	// Manual start/stop
	int start();
	void stop();

	// Status
	bool isRunning() const { return m_running; }

	// Decoder Access
	ePtr<iTSMPEGDecoder> getDecoder() { return m_decoder; }

	// Playback Control
	int play();
	int pause();
	int setSlowMotion(int ratio);
	int setFastForward(int ratio);
	int setTrickmode();

	// Audio Control
	int setAudioPID(int pid, int type);
	int selectAudioTrack(unsigned int i);  // Complete track selection (mirrors v11)
	int getAudioChannel();
	void setAudioChannel(int channel);
	int getAC3Delay();
	int getPCMDelay();
	void setAC3Delay(int delay);
	void setPCMDelay(int delay);

	// Video Info
	int getVideoHeight();
	int getVideoWidth();
	int getVideoFrameRate();
	int getVideoProgressive();
	int getVideoAspect();
	int getVideoGamma();

	// PTS
	int getPTS(int what, pts_t& pts);

	// Video Events
	RESULT connectVideoEvent(
		const sigc::slot<void(struct iTSMPEGDecoder::videoEvent)>& slot,
		ePtr<eConnection>& conn);

	// Demux access (for position calculation)
	ePtr<iDVBDemux> getDecodeDemux() { return m_decode_demux; }

	// Audio track selection signal (notifies parent when SoftDecoder selects audio)
	sigc::signal<void(int)> m_audio_pid_selected;

private:
	eDVBServicePMTHandler& m_source_handler;
	eDVBServicePMTHandler m_pvr_handler;  // Separate PVR handler for decode demux

	ePtr<eDVBService> m_dvb_service;
	ePtr<eDVBCSASession> m_session;

	ePtr<iDVBDemux> m_decode_demux;
	ePtr<iTSMPEGDecoder> m_decoder;
	ePtr<iDVBTSRecorder> m_record;
	ePtr<eConnection> m_record_event_conn;
	ePtr<eConnection> m_session_activated_conn;
	sigc::connection m_source_event_conn;

	int m_decoder_index;
	int m_dvr_fd;
	bool m_running;
	bool m_stopping;
	std::set<int> m_pids_active;

	// CW waiting: Timer-based decoder start
	ePtr<eTimer> m_start_timer;
	sigc::connection m_first_cw_conn;
	bool m_decoder_started;

	ePtr<eTimer> m_health_timer;
	pts_t m_last_pts;
	int m_stall_count;
	bool m_stream_stalled;
	bool m_paused;
	int64_t m_last_health_check;
	void streamHealthCheck();

	// Event Handlers
	void onSessionActivated(bool active);
	void onFirstCwReceived();
	void onWaitForFirstDataTimeout();
	void startDecoderWithDvrWait();
	void serviceEventSource(int event);
	void recordEvent(int event);
	void videoEvent(struct iTSMPEGDecoder::videoEvent event);

	// Setup
	int setupRecorder();
	void updatePids(bool withDecoder = true);
	void updateDecoder(int vpid, int vpidtype, int pcrpid);

	// Video Event Signal
	sigc::signal<void(struct iTSMPEGDecoder::videoEvent)> m_video_event;
	ePtr<eConnection> m_video_event_conn;
};

#endif // __dvbsoftdecoder_h
