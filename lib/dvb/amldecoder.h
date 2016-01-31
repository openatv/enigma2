/** @file
 * This file add support for Amlogic video decoding to enigma2
 * Copyright (C) 2015  Christian Ege <k4230r6@gmail.com>
 *
 * This file is part of Enigma2
 *
 * AMLDecocder is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * AMLDecocder is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with AMLDecocder.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __amldecoder_h
#define __amldecoder_h

#include <lib/base/object.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/decoder.h>
// Amlogic includes
extern "C" {
#include <codec.h>
#include <adec-external-ctrl.h>
#define AMSTREAM_IOC_MAGIC  'S'
#define AMSTREAM_IOC_PCRID  _IOW(AMSTREAM_IOC_MAGIC, 0x4f, int)
}

class eSocketNotifier;


class eAMLTSMPEGDecoder: public Object, public iTSMPEGDecoder
{
	DECLARE_REF(eAMLTSMPEGDecoder);
private:
	static int m_pcm_delay;
	static int m_ac3_delay;
	static int m_audio_channel;
	std::string m_radio_pic;
	ePtr<eDVBDemux> m_demux;
	ePtr<eDVBTText> m_text;
	int m_vpid, m_vtype, m_apid, m_atype, m_pcrpid, m_textpid;
	int m_width, m_height, m_framerate, m_aspect, m_progressive;
	int aml_fd;
	int cntl_fd;
	enum
	{
		changeVideo = 1,
		changeAudio = 2,
		changePCR   = 4,
		changeText  = 8,
		changeState = 16,
	};
	int m_changed, m_decoder;
	int m_radio_pic_on;
	int m_state;
	int m_ff_sm_ratio;
	bool m_has_audio;
	int setState();
	ePtr<eConnection> m_demux_event_conn;
	ePtr<eConnection> m_video_event_conn;


	void demux_event(int event);
	void video_event(struct videoEvent);
	Signal1<void, struct videoEvent> m_video_event;
	int m_video_clip_fd;
	ePtr<eTimer> m_showSinglePicTimer;
	void finishShowSinglePic(); // called by timer
	ePtr<eTimer> m_VideoRead;	
	void parseVideoInfo(); // called by timer
	
	//Amcodec related

	int m_axis[8];

	int osdBlank(int cmd);
	int setAvsyncEnable(int enable);
	int setSyncMode(int mode);
	codec_para_t m_codec;
	dec_sysinfo_t am_sysinfo;
	arm_audio_info am_param;
	void *adec_handle;

public:
	enum { aMPEG, aAC3, aDTS, aAAC, aAACHE, aLPCM, aDTSHD, aDDP, MPEG2 = 0, MPEG4_H264, MPEG1, MPEG4_Part2, VC1, VC1_SM };
	enum { pidNone = -1 };
	eAMLTSMPEGDecoder(eDVBDemux *demux, int decoder);
	virtual ~eAMLTSMPEGDecoder();
	RESULT setVideoPID(int vpid, int type);
	RESULT setAudioPID(int apid, int type);
	RESULT setAudioChannel(int channel);
	int getAudioChannel();
	RESULT setPCMDelay(int delay);
	int getPCMDelay() { return m_pcm_delay; }
	RESULT setAC3Delay(int delay);
	int getAC3Delay() { return m_ac3_delay; }
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
	RESULT setFastForward(int frames_to_skip); /* -> decoder fast forward */
	RESULT setSlowMotion(int repeat); /* -> slow motion **/
	RESULT setTrickmode(); /* -> highspeed fast forward */

	RESULT flush();
	RESULT showSinglePic(const char *filename);
	RESULT setRadioPic(const std::string &filename);
		/* what 0=auto, 1=video, 2=audio. */
	RESULT getPTS(int what, pts_t &pts);
	RESULT connectVideoEvent(const Slot1<void, struct videoEvent> &event, ePtr<eConnection> &connection);
	int getVideoWidth();
	int getVideoHeight();
	int getVideoProgressive();
	int getVideoFrameRate();
	int getVideoAspect();
	static RESULT setHwPCMDelay(int delay);
	static RESULT setHwAC3Delay(int delay);
};

#endif
