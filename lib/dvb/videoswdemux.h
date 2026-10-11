/* SPDX-License-Identifier: GPL-2.0-only */

#ifndef __lib_dvb_videoswdemux_h
#define __lib_dvb_videoswdemux_h

#include <atomic>
#include <cstdint>
#include <vector>

#include <lib/base/thread.h>
#include <lib/dvb/demux.h>

/*
 * DreamOne/DreamTwo: the hardware demux only feeds the first video decoder.
 * Further decoders take memory input (as DreamOS): the video PID is tapped
 * as TS from the service demux and every PES payload is handed to the
 * decoder with its PTS. Soft descrambled services work as well.
 */
class eDVBVideoSwDemux: public eThread
{
public:
	/* codecs with an entry point the input waits for */
	enum Codec { OTHER, MPEG2, H264, HEVC };

	eDVBVideoSwDemux(eDVBDemux *demux, int fd_video, int pes_type);
	~eDVBVideoSwDemux();

	int start(int pid, Codec codec);
	void stop();

private:
	enum
	{
		TSPacketSize = 188,
		TapBufferSize = 2 * 1024 * 1024
	};

	void thread() override;
	void feed(const uint8_t *data, size_t length);
	void writeFrame();
	bool entryPoint(const uint8_t *es, size_t length) const;
	void reportStreamBase(int64_t pts);

	ePtr<eDVBDemux> m_demux;
	int m_fd_video;
	int m_pes_type;
	int m_fd_demux = -1;
	int m_pid = -1;
	Codec m_codec = OTHER;
	/* continuity counter of the last packet, -1 = none */
	int m_cc = -1;
	/* a packet of the current PES is missing */
	bool m_pes_broken = false;
	/* an entry point was handed to the decoder */
	bool m_synced = false;
	bool m_base_reported = false;
	bool m_random_access = false;
	std::atomic<bool> m_stop{false};
	std::vector<uint8_t> m_partial;
	std::vector<uint8_t> m_pes;
};

#endif
