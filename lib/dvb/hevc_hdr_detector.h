/* SPDX-License-Identifier: GPL-2.0-only */

#ifndef __lib_dvb_hevc_hdr_detector_h
#define __lib_dvb_hevc_hdr_detector_h

#include <array>
#include <cstddef>

#include <lib/base/ebase.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/hevc_hdr_parser.h>

/*
 * Reads the selected HEVC video PID through a temporary DMX_OUT_TSDEMUX_TAP
 * filter and reports a gamma value when SPS/VUI or HDR SEI signalling is
 * conclusive.
 *
 * A TS tap is used instead of DMX_OUT_TAP: on Vu+ (dvb_bcm7444) a PES tap on
 * the running video PID uses a separate recpump whose close can deadlock in
 * DMX_STOP.  The detector is a fallback; callers may stop it as soon as the
 * native video driver reports a useful VIDEO_EVENT_GAMMA_CHANGED value.
 */
class eHEVCHDRDetector : public sigc::trackable
{
public:
	eHEVCHDRDetector(eDVBDemux *demux, const sigc::slot<void(int)> &result_slot);
	~eHEVCHDRDetector();

	bool start(int pid);
	void stop();
	bool running() const { return m_running; }

private:
	enum
	{
		ScanTimeoutMs = 12000,
		DeferredResultMs = 1,
		TSPacketSize = 188,
		TapBufferSize = 512 * 1024
	};

	void readData(int what);
	int payloadOffset(const uint8_t *packet) const;
	void closeTap();
	void timerExpired();
	void scheduleResult(int gamma);

	ePtr<eDVBDemux> m_demux;
	ePtr<eSocketNotifier> m_notifier;
	ePtr<eTimer> m_timer;
	sigc::slot<void(int)> m_result_slot;
	eHEVCHDRParser m_parser;
	int m_fd = -1;
	int m_pid = -1;
	std::array<uint8_t, TSPacketSize> m_partial = {};
	size_t m_partial_length = 0;
	bool m_running = false;
	int m_pending_gamma = eHEVCHDRParser::GammaUnknown;
	size_t m_bytes_received = 0;
};

#endif
