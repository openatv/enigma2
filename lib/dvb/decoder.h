#ifndef __decoder_h
#define __decoder_h

#include <lib/base/object.h>
#include <lib/dvb/demux.h>
#ifdef DREAMNEXTGEN
#include <lib/dvb/tsparser.h>
#include <lib/base/ebase.h>
#endif

class eSocketNotifier;
class eHEVCHDRDetector;

class eDVBAudio: public iObject
{
	DECLARE_REF(eDVBAudio);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux, m_dev, m_is_freezed, m_bypass;
	static int m_debug;
#ifdef DREAMNEXTGEN
	eTsParser *m_TsPaser;
#endif
public:
	enum { aMPEG, aAC3, aDTS, aAAC, aAACHE, aLPCM, aDTSHD, aDDP, aDRA, aAC4 };
	eDVBAudio(eDVBDemux *demux, int dev);
	enum { aMonoLeft, aStereo, aMonoRight };
	void setChannel(int channel);
	void stop();
	int startPid(int pid, int type);
	void flush();
	void freeze();
	void unfreeze();
	int getPTS(pts_t &now);
	virtual ~eDVBAudio();
};

class eDVBVideo: public iObject, public sigc::trackable
{
	DECLARE_REF(eDVBVideo);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd, m_fd_demux, m_dev;
	bool m_fcc_enable;
	static int m_debug;
	static int m_close_invalidates_attributes;
	int m_is_slow_motion, m_is_fast_forward, m_is_freezed;
	ePtr<eSocketNotifier> m_sn;
	void video_event(int what);
	sigc::signal<void(struct iTSMPEGDecoder::videoEvent)> m_event;
	int m_width, m_height, m_framerate, m_aspect, m_progressive, m_gamma, m_streamtype;
	static int readApiSize(int fd, int &xres, int &yres, int &aspect);

	// HEVC HDR fallback for drivers which do not expose a usable sGamma.
	eHEVCHDRDetector *m_hdr_detector;
	int m_hdr_gamma, m_driver_gamma;
	bool m_hdr_gamma_authoritative, m_gamma_from_driver_event;
	void hdr_gamma_detected(int gamma);
	void publish_gamma(int gamma);
	int read_driver_gamma();
#ifdef DREAMNEXTGEN
	ePtr<eTimer> m_sysfs_poll_timer;
	bool m_sysfs_size_event_sent;
	unsigned int m_sysfs_poll_attempts;
	void sysfs_poll_timeout();
#endif
public:
	enum { UNKNOWN = -1, MPEG2, MPEG4_H264, VC1 = 3, MPEG4_Part2, VC1_SM, MPEG1, H265_HEVC, AVS = 16, AVS2 = 40 };
	eDVBVideo(eDVBDemux *demux, int dev, bool fcc_enable=false);
	void stop();
	int startPid(int pid, int type=MPEG2);
	void flush();
	void freeze();
	int setSlowMotion(int repeat);
	int setFastForward(int skip);
	void unfreeze();
#ifdef DREAMNEXTGEN
	/* Explicit VIDEO_PLAY ioctl used by trick→play recovery dance.
	 * Distinct from startPid() which also opens demux + sets stream type. */
	void playRecovery();
	/* Post-VIDEO_FAST_FORWARD flush: DMX_STOP + VIDEO_CLEAR_BUFFER +
	 * DMX_START. Commits the kernel decoder_set_trickmode to the screen. */
	void dnxtPostFastForward();
#endif
	int getPTS(pts_t &now);
	virtual ~eDVBVideo();
	RESULT connectEvent(const sigc::slot<void(struct iTSMPEGDecoder::videoEvent)> &event, ePtr<eConnection> &conn);
	int getWidth();
	int getHeight();
	int getProgressive();
	int getFrameRate();
	int getAspect();
	int getGamma();
};

class eDVBPCR: public iObject
{
	DECLARE_REF(eDVBPCR);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd_demux, m_dev;
	static int m_debug;
public:
	eDVBPCR(eDVBDemux *demux, int dev);
	int startPid(int pid);
#ifdef DREAMNEXTGEN
	int start();
#endif
	void stop();
	virtual ~eDVBPCR();
};

class eDVBTText: public iObject
{
	DECLARE_REF(eDVBTText);
private:
	ePtr<eDVBDemux> m_demux;
	int m_fd_demux, m_dev;
	static int m_debug;
public:
	eDVBTText(eDVBDemux *demux, int dev);
	int startPid(int pid);
	void stop();
	virtual ~eDVBTText();
};

class eTSMPEGDecoder: public sigc::trackable, public iTSMPEGDecoder
{
	DECLARE_REF(eTSMPEGDecoder);
private:
	static int m_pcm_delay;
	static int m_ac3_delay;
	static int m_audio_channel;
	static int m_debugTXT;
	std::string m_radio_pic;
	ePtr<eDVBDemux> m_demux;
	ePtr<eDVBAudio> m_audio;
	ePtr<eDVBVideo> m_video;
	ePtr<eDVBPCR> m_pcr;
	ePtr<eDVBTText> m_text;
	int m_vpid, m_vtype, m_apid, m_atype, m_pcrpid, m_textpid;
#ifdef DREAMNEXTGEN
	int m_width, m_height, m_framerate, m_aspect, m_progressive;
#endif
	enum
	{
		changeVideo = 1,
		changeAudio = 2,
		changePCR   = 4,
		changeText  = 8,
		changeState = 16,
	};
	int m_changed, m_decoder;
	int m_state;
	int m_ff_sm_ratio;
	bool m_has_audio;
#ifdef DREAMNEXTGEN
	bool m_user_pause_active = false;
#endif
	int setState();
	ePtr<eConnection> m_demux_event_conn;
	ePtr<eConnection> m_video_event_conn;

	void demux_event(int event);
	void video_event(struct videoEvent);
	sigc::signal<void(struct videoEvent)> m_video_event;
	int m_video_clip_fd;
	ePtr<eTimer> m_showSinglePicTimer;
	int m_fcc_fd;
	bool m_fcc_enable;
	int m_fcc_state;
	int m_fcc_feid;
	int m_fcc_vpid;
	int m_fcc_vtype;
	int m_fcc_pcrpid;
	void finishShowSinglePic(); // called by timer
public:
#ifdef DREAMNEXTGEN
	enum { aMPEG, aAC3, aDTS, aAAC, aAACHE, aLPCM, aDTSHD, aDDP,UNKNOWN = -1, MPEG2=0, MPEG4_H264, VC1 = 3, MPEG4_Part2, VC1_SM, MPEG1, H265_HEVC, AVS = 16, AVS2 = 40 };
#endif
	enum { pidNone = -1 };
	eTSMPEGDecoder(eDVBDemux *demux, int decoder);
	virtual ~eTSMPEGDecoder();
	RESULT setVideoPID(int vpid, int type);
	RESULT setAudioPID(int apid, int type);
	RESULT setAudioChannel(int channel);
	int getAudioChannel();
	RESULT setPCMDelay(int delay);
	int getPCMDelay() { return m_pcm_delay; }
	RESULT setAC3Delay(int delay);
	int getAC3Delay() { return m_ac3_delay; }
	static int getStaticPCMDelay() { return m_pcm_delay; }
	static int getStaticAC3Delay() { return m_ac3_delay; }
	RESULT setSyncPCR(int pcrpid);
	RESULT setTextPID(int textpid);
	RESULT setSyncMaster(int who);

		/*
		The following states exist:

		 - stop: data source closed, no playback
		 - pause: data source active, decoder paused
		 - play: data source active, decoder consuming
		 - decoder fast forward: data source linear, decoder drops frames
		 - trickmode, highspeed reverse: data source fast forwards / reverses, decoder just displays frames as fast as it can
		 - slow motion: decoder displays frames multiple times
		*/
	enum {
		stateStop,
		statePause,
		statePlay,
		stateDecoderFastForward,
		stateTrickmode,
		stateSlowMotion
	};
	RESULT set(); /* just apply settings, keep state */
	RESULT play(); /* -> play */
	RESULT pause(); /* -> pause */
#ifdef DREAMNEXTGEN
	void setUserPauseActive(bool b) override { m_user_pause_active = b; }
#endif
	RESULT setFastForward(int frames_to_skip); /* -> decoder fast forward */
	RESULT setSlowMotion(int repeat); /* -> slow motion **/
	RESULT setTrickmode(); /* -> highspeed fast forward */

	RESULT flush();
	RESULT showSinglePic(const char *filename);
	RESULT showSinglePic(const char *filename, bool keepVisible);
	RESULT setRadioPic(const std::string &filename);
		/* what 0=auto, 1=video, 2=audio. */
	RESULT getPTS(int what, pts_t &pts);
	RESULT connectVideoEvent(const sigc::slot<void(struct videoEvent)> &event, ePtr<eConnection> &connection);
	int getVideoWidth();
	int getVideoHeight();
	int getVideoProgressive();
	int getVideoFrameRate();
	int getVideoAspect();
	int getVideoGamma();
	static RESULT setHwPCMDelay(int delay);
	static RESULT setHwAC3Delay(int delay);

	enum 
	{
		fcc_state_stop,
		fcc_state_ready,
		fcc_state_decoding
	};

	void freeDecoder() override;

	RESULT prepareFCC(int fe_id, int vpid, int vtype, int pcrpid);
	RESULT fccStart();
	RESULT fccStop();
	RESULT fccDecoderStart();
	RESULT fccDecoderStop();
	RESULT fccUpdatePids(int fe_id, int vpid, int vtype, int pcrpid);
	RESULT fccSetPids(int fe_id, int vpid, int vtype, int pcrpid);
	RESULT fccGetFD();
	RESULT fccFreeFD();

	bool canFlush() const { return true; }

};

#ifdef DREAMNEXTGEN

extern "C" {
#include <libavformat/avformat.h>
#include <libavdevice/avdevice.h>
#include <libavcodec/avcodec.h>
#include <libswresample/swresample.h>
#include <libavutil/opt.h>
#include <libavutil/channel_layout.h>
#include <libavutil/samplefmt.h>
#include <libavutil/mem.h>
#include <libavutil/timestamp.h>
#include <libavutil/audio_fifo.h>
}
#include <lib/dvb/alsa.h>

class eIec61937Passthrough;
struct AVAudioFifo;

#include <atomic>

/* Skip-until-PTS gate: drop PES whose PTS is older than this value.
 * AV_NOPTS_VALUE = inactive. Set by eAlsaOutput when pcrscr jumps. */
extern std::atomic<int64_t> g_audio_skip_until_pts;

/* One-shot codec flush flag set by alsa.cpp flushOnSeek.
 * eAudioDecoder consumes (exchange-false) at next decode(). */
extern std::atomic<bool> g_audio_request_codec_flush;

/* Userspace FFmpeg+ALSA audio decoder, coexists with eDVBAudio. */
class eAudioDecoder
{
public:
    eAudioDecoder();
    ~eAudioDecoder();

    int start(int sample_rate, int channels, int bytes_per_sample, enum AVCodecID codec_id);
    int decode(uint8_t *framedata, int framesize, int64_t pts, int64_t dts);
    int getCodecDelayMs() const;

    /* Set before start() to transcode PCM → codec and route via
     * eIec61937Passthrough. Currently only AV_CODEC_ID_AC3 is wired. */
    enum AVCodecID m_transcode_to = AV_CODEC_ID_NONE;

    /* AC-4 immersive probe: librempeg's upper channels often carry noise
     * floor only; latch full layout when ch[1+] peak reaches >= 30% of
     * ch[0] peak over m_ac4_probe_streak consecutive frames. */
    bool m_ac4_immersive_ok = false;
    int  m_ac4_probe_streak = 0;

    unsigned int m_sample_rate;
    unsigned int m_bytes_per_sample;
    int64_t m_last_pts;

    const class AVCodec  *m_codec = NULL;
    class AVCodecContext *m_codec_ctx = NULL;
    class SwrContext     *m_swr_ctx = NULL;
    class AVFrame        *m_frame = NULL;
    class AVPacket       *m_avpkt = NULL;

    eAlsaOutput *m_AlsaOutput;
    unsigned int m_alsa_channels;
    unsigned int m_alsa_sample_rate;   ///< actual HW rate from snd_pcm_hw_params_set_rate_near
    unsigned int m_alsa_dec_rate;      ///< decoder-side rate, compared against frame sample_rate to detect real changes

private:
    int m_stop;
    int m_audio_port;   ///< cached /sys/class/amhdmitx/amhdmitx0/audio_source
    void updateAudioOutputDevice();

    /* Transcode path state. NULL when m_transcode_to == AV_CODEC_ID_NONE. */
    class AVCodecContext     *m_enc_ctx     = NULL;
    class AVFrame            *m_enc_frame   = NULL;
    class AVPacket           *m_enc_pkt     = NULL;
    AVAudioFifo              *m_enc_fifo    = NULL;
    class SwrContext         *m_enc_swr     = NULL;  ///< decoded -> encoder input fmt
    eIec61937Passthrough     *m_iec61937    = NULL;
    int64_t                   m_enc_next_pts = 0;
    int  startEncoder();
    void freeEncoder();
    int  feedEncoder(class AVFrame *pcm);  ///< swr to FLTP, FIFO, encode, push IEC61937
    int  drainEncoderFifo(bool flush);
};

#endif // DREAMNEXTGEN

#endif
