#include "eramserviceplay.h"
#include <lib/base/cfile.h>
#include <lib/dvb/csasession.h>
#include <lib/base/esimpleconfig.h>
#include <algorithm>
#include <unistd.h>

DEFINE_REF(eRamServicePlay);

eRamServicePlay::eRamServicePlay(const eServiceReference &ref, eDVBService *service, int delay_seconds)
	: eDVBServicePlay(ref, service, true)
{
	m_ts_source = nullptr;
	m_ram_recorder = nullptr;
	m_frozen_play_position = 0;

	// Compute capacity: at least 32 MB or delay_seconds * 4 MB.
	// The *4 factor assumes ~4 Mbit/s average bitrate — generous
	// for most DVB-S2 transponders.
	int cap_mb = std::max(32, delay_seconds * 4);
	m_capacity_bytes = (size_t)cap_mb * 1024 * 1024;
	eDebug("[eRamServicePlay] cap=%dMB", cap_mb);
}

eRamServicePlay::~eRamServicePlay()
{
	stopTimeshift(false);
}

// ------------------------------------------------------------------
// startTimeshift
// ------------------------------------------------------------------
RESULT eRamServicePlay::startTimeshift()
{
	if (m_timeshift_enabled)
		return -1;
	ePtr<iDVBDemux> demux;
	if (m_service_handler.getDataDemux(demux))
		return -2;

	m_ram_ring = std::make_shared<eRamRingBuffer>(m_capacity_bytes, 8192);
	if (!m_ram_ring->isValid())
	{
		eWarning("[eRamServicePlay] RAM buffer allocation failed");
		m_ram_ring.reset();
		return -3;
	}

	demux->createTSRecorder(m_record, 188, false);

	// RTTI is disabled (-fno-rtti), so we must use static_cast
	// to access eDVBTSRecorder specific methods.
	eDVBTSRecorder *recorder = static_cast<eDVBTSRecorder *>(m_record.operator->());
	if (!recorder)
	{
		eWarning("[eRamServicePlay] Failed to get recorder - RAM timeshift aborted");
		m_ram_ring.reset();
		m_record = 0;
		return -3;
	}

	eRamRecorder *ram_rec = new eRamRecorder(m_ram_ring.get(), 188);
	m_ram_recorder = ram_rec;
	recorder->replaceThread(ram_rec);
	m_record->setTargetFD(-1);

	// NOTE: We intentionally do NOT call m_record->enableAccessPoints(false)
	// here. The disk-timeshift base class disables access points because
	// it has tstools/.ap files for seeking. RAM timeshift has neither —
	// the only way to identify I-frame positions in the ring buffer is
	// through the access-point counter in eMPEGStreamParserTS.
	//
	// With access points enabled, parseData() calls addAccessPoint() on
	// each I-frame, incrementing getAccessPointCount(). eRamRecorder::
	// writeData() uses the before/after count to set the is_access_point
	// flag on each ring-buffer block. findNearestAccessPoint() then
	// uses these flags to snap seek positions to I-frame boundaries,
	// eliminating decode artifacts after seeking.
	//
	// The in-memory deque growth is negligible (~16 bytes per AP,
	// ~7200 entries/hour = ~115 KB). No .ap file is written because
	// startSaveMetaInformation() is never called in RAM mode
	// (m_structure_write_fd remains -1).

	m_record->connectEvent(sigc::mem_fun(*this, &eRamServicePlay::recordEvent), m_con_record_event);

	// StreamRelay / CSA-ALT channels need per-session descrambling.
	if (m_csa_session && m_csa_session->isActive())
	{
		eServiceReferenceDVB dvb_ref = (eServiceReferenceDVB &)m_reference;
		m_timeshift_csa_session = new eDVBCSASession(dvb_ref);
		if (m_timeshift_csa_session && m_timeshift_csa_session->init())
		{
			m_timeshift_csa_session->forceActivate();
			m_record->setDescrambler(static_cast<iServiceScrambled *>(m_timeshift_csa_session.operator->()));
		}
	}

	// Use the ap base path as the "file" so eDVBTSTools finds our .ap.
	// createTsSource() returns eRamTsSource (ring buffer), not a real file.
	// Create an empty .ap sentinel so tstools doesn't log ENOENT warnings.
	m_timeshift_file = "/tmp/ram_timeshift";
	CFile::writeStr("/tmp/ram_timeshift.ap", "");
	m_timeshift_enabled = 1;
	updateTimeshiftPids();

	const int sret = m_record->start();
	if (sret < 0)
	{
		eWarning("[eRamServicePlay] record->start() failed: %d", sret);
		if (m_timeshift_csa_session)
		{
			m_record->setDescrambler(nullptr);
			m_timeshift_csa_session = nullptr;
		}
		m_ram_recorder = nullptr;
		m_record = 0;
		m_ram_ring.reset();
		::unlink("/tmp/ram_timeshift.ap");
		m_timeshift_file.clear();
		m_timeshift_enabled = 0;
		return sret;
	}

	CFile::writeStr("/proc/stb/lcd/symbol_timeshift", "1");
	CFile::writeStr("/proc/stb/lcd/symbol_record", "1");
	eDebug("[eRamServicePlay] recording started (%zuMB)", m_capacity_bytes >> 20);
	return 0;
}

// ------------------------------------------------------------------
// activateTimeshift — start watchdog after parent activates
// ------------------------------------------------------------------
RESULT eRamServicePlay::activateTimeshift()
{
	RESULT r = eDVBServicePlay::activateTimeshift();
	if (r != 0)
		return r;

	// Start 200ms watchdog to detect ring-buffer lap events and
	// force the push thread to jump to a safe read position.
	m_watchdog_timer = eTimer::create(eApp);
	m_watchdog_timer->timeout.connect(sigc::mem_fun(*this, &eRamServicePlay::checkLapAndSeek));
	m_watchdog_timer->start(200, false);
	return 0;
}

// ------------------------------------------------------------------
// checkLapAndSeek (watchdog, every 200ms)
// ------------------------------------------------------------------
void eRamServicePlay::checkLapAndSeek()
{
	if (!m_timeshift_active)
		return;

	// Guard: Do not move the read position while PRS is paused
	// waiting for stream corruption to clear. On high-bitrate 4K
	// streams, the ring buffer can wrap during the pause window.
	// Forcing a position jump here would break the PRS recovery.
	if (m_stream_corruption_detected)
		return;

	// --- Lap detection (ring buffer overtook read position) ---
	//
	// When the ring buffer wraps and overwrites data that the push
	// thread is still reading, eRamTsSource::read() sets the lap flag.
	//
	// Recovery: force the push thread's read position to the first
	// valid byte in the ring buffer via forceSourcePosition(). This
	// bypasses tstools entirely (which has stale .ap data) and
	// directly moves the push thread's m_current_position in
	// eFilePushThread.
	ePtr<eRamTsSource> src = m_ts_source;
	if (!src)
		return;

	off_t lapped_at = 0;
	if (!src->getLappedOffset(lapped_at))
		return;

	if (!m_ram_ring)
		return;

	off_t min_off = m_ram_ring->getMinOffset();

	// Align up to 188-byte packet boundary for clean decode.
	off_t safe = min_off + (188 - min_off % 188) % 188;
	eDebug("[eRamServicePlay] watchdog: lap at %lld, jumping to min_off=%lld",
		(long long)lapped_at, (long long)safe);

	ePtr<iDVBPVRChannel> pvr_channel;
	if (m_service_handler_timeshift.getPVRChannel(pvr_channel) == 0)
		pvr_channel->forceSourcePosition(safe);
}

void eRamServicePlay::recordEvent(int event)
{
	if (event == iDVBTSRecorder::eventStreamCorrupt)
	{
		// Save play position NOW — before base class sets
		// m_stream_corruption_detected = true.
		// On Hisilicon, getPTS() advances even in pause(), so we
		// must freeze it at the exact moment corruption is detected.
		if (!m_stream_corruption_detected)
			getPlayPosition(m_frozen_play_position);
	}
	eDVBServicePlay::recordEvent(event);
}

// ------------------------------------------------------------------
// serviceEventTimeshift — suppress EOF-triggered switchToLive
// ------------------------------------------------------------------
//
// On disk timeshift, eventEOF means the push thread reached the end
// of the timeshift file — the base class responds with switchToLive().
//
// On RAM timeshift there is no end-of-file: the ring buffer always
// has data up to the write offset. An eventEOF from the push thread
// means one of two things:
// 1. The ring has lapped the read position (handled by checkLapAndSeek)
// 2. The push thread reached the live edge (normal — wait for data)
//
// In both cases, ignoring the EOF and letting the watchdog handle
// recovery is the correct response. Calling switchToLive() here
// would tear down the entire timeshift session.
void eRamServicePlay::serviceEventTimeshift(int event)
{
	if (event == eDVBServicePMTHandler::eventEOF)
	{
		eTrace("[eRamServicePlay] ignoring eventEOF — watchdog handles lap/live-edge");
		return;
	}
	eDVBServicePlay::serviceEventTimeshift(event);
}

// ------------------------------------------------------------------
// stopTimeshift
// ------------------------------------------------------------------
RESULT eRamServicePlay::stopTimeshift(bool swToLive)
{
	if (!m_timeshift_enabled)
		return -1;

	// Stop watchdog first — prevents callbacks on partially
	// torn-down state.
	if (m_watchdog_timer)
	{
		m_watchdog_timer->stop();
		m_watchdog_timer = nullptr;
	}
	resetRecoveryState();

	if (m_record)
	{
		// Stop the push thread FIRST — guarantees eRamTsSource::read() /
		// offset() are no longer executing before we release the source.
		// Reversing this order (nulling m_ts_source before stop()) would
		// create a use-after-free window because eFilePushThread holds a
		// raw pointer to the source and may be mid-read.
		m_record->stop();
		if (m_timeshift_csa_session)
		{
			m_record->setDescrambler(nullptr);
			m_timeshift_csa_session = nullptr;
		}
		m_record = 0;
	}

	// Safe to release now — push thread is guaranteed stopped
	// (stop() calls kill() which joins the thread).
	m_ts_source = nullptr;
	m_ram_recorder = nullptr;
	m_ram_ring.reset();
	m_timeshift_enabled = 0;

	CFile::writeStr("/proc/stb/lcd/symbol_timeshift", "0");
	CFile::writeStr("/proc/stb/lcd/symbol_record", "0");

	// Clean up sentinel file and clear path last so any remaining
	// code that checks m_timeshift_file still finds a valid value.
	::unlink("/tmp/ram_timeshift.ap");
	m_timeshift_file.clear();

	if (swToLive)
		switchToLive();

	eDebug("[eRamServicePlay] stopped");
	return 0;
}

// ------------------------------------------------------------------
// seekTo — DISABLED FOR RAM TIMESHIFT
// ------------------------------------------------------------------
RESULT eRamServicePlay::seekTo(pts_t to)
{
	// Seek is completely disabled for RAM timeshift to prevent
	// issues with 4K channels and to offload PCR history searches.
	// This does NOT affect the Precise Recovery System (PRS).
	if (m_timeshift_active && m_ram_recorder)
	{
		eTrace("[eRamServicePlay] seekTo: disabled on RAM timeshift");
		return -1;
	}
	return eDVBServicePlay::seekTo(to);
}

// ------------------------------------------------------------------
// seekRelative — DISABLED FOR RAM TIMESHIFT
// ------------------------------------------------------------------
RESULT eRamServicePlay::seekRelative(int direction, pts_t to)
{
	// Seek is completely disabled for RAM timeshift to prevent
	// issues with 4K channels and to offload PCR history searches.
	// This does NOT affect the Precise Recovery System (PRS).
	if (m_timeshift_active && m_ram_recorder)
	{
		eTrace("[eRamServicePlay] seekRelative: disabled on RAM timeshift");
		return -1;
	}
	return eDVBServicePlay::seekRelative(direction, to);
}

// ------------------------------------------------------------------
// saveTimeshiftFile — no-op for RAM (nothing on disk to save)
// ------------------------------------------------------------------
RESULT eRamServicePlay::saveTimeshiftFile()
{
	// RAM timeshift has no disk file to save/copy.
	// Return success to prevent the parent from trying to copy
	// a non-existent file.
	return 0;
}

// ------------------------------------------------------------------
// createTsSource — return ring buffer source, not a real file
// ------------------------------------------------------------------
ePtr<iTsSource> eRamServicePlay::createTsSource(eServiceReferenceDVB &ref, int /*packetsize*/)
{
	if (!m_ram_ring)
		return eDVBServicePlay::createTsSource(ref);
	eRamTsSource *src = new eRamTsSource(m_ram_ring);
	m_ts_source = src;
	return ePtr<iTsSource>(src);
}

// ------------------------------------------------------------------
// getLength — USE PTS ONLY (Consistent with getPlayPosition)
// ------------------------------------------------------------------
//
// Design note: returns total elapsed time since recording start,
// NOT just the buffered window. This is deliberate:
//
// getPlayPosition() = pts_delta(decoder_pts, m_first_pts) — grows
// monotonically from 0. getLength() must use the same reference
// (m_first_pts) so the seek bar stays consistent (pos <= len).
//
// Using the sliding window (getPTSWindow first/last) would cause
// pos > len after wrap, and would also break the Precise Recovery
// System's delay calculation which depends on a stable reference.
//
// seekTo() independently clamps to the live buffer window, so
// seeking beyond what's buffered safely lands at the window edge.
//
// Uses m_record (iDVBTSRecorder interface) for getFirstPTS() and
// getCurrentPCR() — these are on the interface, not eRamRecorder.
RESULT eRamServicePlay::getLength(pts_t &len)
{
	if (!m_ram_recorder)
		return eDVBServicePlay::getLength(len);

	pts_t first_pts = 0, last_pts = 0;
	if (m_record->getFirstPTS(first_pts) != 0)
		return -1;
	if (m_record->getCurrentPCR(last_pts) != 0)
		return -1;

	pts_t d = pts_delta(last_pts, first_pts);
	if (d <= 0)
		return -1;
	len = d;
	return 0;
}

// ------------------------------------------------------------------
// getPlayPosition — use decoder PTS + first PTS from recorder
// ------------------------------------------------------------------
//
// Returns RELATIVE position (decoder PTS delta from first PTS),
// NOT the raw decoder PTS. This matches the master disk-timeshift
// behavior where pvr_channel->getCurrentPosition() returns the
// relative delay, not the absolute PTS.
//
// The UI expects pos and len from the same reference point:
// pos = pts_delta(decoder_pts, first_pts)
// len = pts_delta(last_pts, first_pts)
// so the seek bar shows pos/len consistently.
//
// Uses m_record (iDVBTSRecorder interface) for getFirstPTS()
// which is on the interface, not eRamRecorder.
RESULT eRamServicePlay::getPlayPosition(pts_t &pos)
{
	if (!m_timeshift_active || !m_ram_recorder || !m_decoder || !m_record)
		return eDVBServicePlay::getPlayPosition(pos);

	// During stream corruption, freeze play position.
	// On Hisilicon, m_decoder->getPTS() keeps advancing even in
	// pause() because the hardware decoder drains its internal buffer.
	// Freezing pos here prevents current_delay from shrinking → PRS waits.
	if (m_stream_corruption_detected)
	{
		pos = m_frozen_play_position;
		return 0;
	}

	pts_t first_pts = 0;
	if (m_record->getFirstPTS(first_pts) != 0)
		return -1;
	pts_t dec = 0;
	if (m_decoder->getPTS(0, dec) != 0)
		if (m_decoder->getPTS(1, dec) != 0)
			return -1;
	pos = pts_delta(dec, first_pts);
	return 0;
}

// ------------------------------------------------------------------
// Status helpers
// ------------------------------------------------------------------
bool eRamServicePlay::isRamBufferReady() const
{
	return m_ram_ring && m_ram_ring->getWriteOffset() > 0;
}

float eRamServicePlay::ramBufferedSeconds() const
{
	return m_ram_ring ? (float)(m_ram_ring->bufferedMs() / 1000.0) : 0.f;
}

int eRamServicePlay::ramFillPercent() const
{
	if (!m_ram_ring) return 0;
	off_t filled = m_ram_ring->getWriteOffset() - m_ram_ring->getMinOffset();
	return (int)(filled * 100 / (off_t)(m_capacity_bytes));
}