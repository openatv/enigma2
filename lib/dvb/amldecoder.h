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
// Amlogic includes
extern "C" {
#include <codec.h>
}

class eSocketNotifier;


class eAMLTSMPEGDecoder: public sigc::trackable, public iTSMPEGDecoder
{
	DECLARE_REF(eAMLTSMPEGDecoder);
private:
	static int m_pcm_delay;
	static int m_ac3_delay;
	static int m_audio_channel;
	std::string m_radio_pic;
	ePtr<eDVBDemux> m_demux;
	int m_vpid, m_vtype, m_apid, m_atype, m_pcrpid, m_textpid;
	int m_width, m_height, m_framerate, m_aspect, m_progressive;
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
	sigc::signal1<void, struct videoEvent> m_video_event;
	int m_video_clip_fd;
	ePtr<eTimer> m_showSinglePicTimer;
	void finishShowSinglePic(); // called by timer
	ePtr<eTimer> m_VideoRead;	
	void parseVideoInfo(); // called by timer

	//Amcodec related
	codec_para_t m_codec;

public:
	enum { aMPEG, aAC3, aDTS, aAAC, aAACHE, aLPCM, aDTSHD, aDDP,UNKNOWN = -1, MPEG2=0, MPEG4_H264, VC1 = 3, MPEG4_Part2, VC1_SM, MPEG1, H265_HEVC, AVS = 16 };
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
	RESULT connectVideoEvent(const sigc::slot1<void, struct videoEvent> &event, ePtr<eConnection> &connection);
	int getVideoWidth();
	int getVideoHeight();
	int getVideoProgressive();
	int getVideoFrameRate();
	int getVideoAspect();
	int getVideoGamma();
	static RESULT setHwPCMDelay(int delay);
	static RESULT setHwAC3Delay(int delay);
};

#endif
