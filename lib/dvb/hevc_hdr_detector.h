/* SPDX-License-Identifier: GPL-2.0-only */

#ifndef __lib_dvb_hevc_hdr_detector_h
#define __lib_dvb_hevc_hdr_detector_h

#include <cstddef>

#include <lib/base/ebase.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/hevc_hdr_parser.h>

/*
 * Reads the selected HEVC video PID through a temporary DMX_OUT_TAP filter and
 * reports a gamma value when SPS/VUI or HDR SEI signalling is conclusive.
 *
 * Vu+ driver generations differ in what DMX_OUT_TAP returns: some expose full
 * PES packets, others expose the elementary-stream payload.  Both forms are
 * parsed in parallel.  The detector is a fallback; callers may stop it as soon
 * as the native video driver reports a useful VIDEO_EVENT_GAMMA_CHANGED value.
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
		DeferredResultMs = 1
	};

	void data(const uint8_t *buffer, int length);
	void timerExpired();
	void scheduleResult(int gamma);
	static int selectGamma(int pes_gamma, int es_gamma, bool final);

	ePtr<eDVBDemux> m_demux;
	ePtr<iDVBPESReader> m_reader;
	ePtr<eConnection> m_read_connection;
	ePtr<eTimer> m_timer;
	sigc::slot<void(int)> m_result_slot;
	eHEVCHDRParser m_pes_parser;
	eHEVCHDRParser m_es_parser;
	bool m_running;
	int m_pending_gamma;
	size_t m_bytes_received;
};

#endif
