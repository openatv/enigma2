#ifndef __lib_service_eramserviceplay_h
#define __lib_service_eramserviceplay_h

#include <lib/base/ebase.h>
#include <lib/dvb/eramtimeshift.h>
#include <lib/service/servicedvb.h>
#include <memory>

/*
 * eRamServicePlay
 *
 * Extends eDVBServicePlay to store timeshift data in RAM instead of
 * disk.  Pause, unpause, and seek all work exactly as in the normal
 * disk timeshift.
 *
 * Pause triggers startTimeshift() which records into RAM.  Unpause
 * calls activateTimeshift() which starts playback from the RAM buffer
 * at the accumulated delay — identical to disk timeshift behavior.
 *
 * Enabled via: eSettings::ram_timeshift_delay_seconds > 0
 * Instantiated by eServiceFactoryDVB::play() when that config is set.
 */
class eRamServicePlay : public eDVBServicePlay {
	DECLARE_REF(eRamServicePlay);

public:
	eRamServicePlay(const eServiceReference& ref, eDVBService* service, int delay_seconds = 10);
	~eRamServicePlay() override;

	bool isRamBufferReady() const;
	float ramBufferedSeconds() const;
	int ramFillPercent() const;

	RESULT getLength(pts_t& len) override;
	RESULT getPlayPosition(pts_t& pos) override;
	RESULT seekTo(pts_t to) override;
	RESULT seekRelative(int direction, pts_t to) override;
	RESULT activateTimeshift() override;
	RESULT saveTimeshiftFile() override;
	void serviceEventTimeshift(int event) override;

protected:
	RESULT startTimeshift() override;
	RESULT stopTimeshift(bool swToLive = false) override;

	ePtr<iTsSource> createTsSource(eServiceReferenceDVB& ref, int packetsize = 188) override;

private:
	void checkLapAndSeek();
	void recordEvent(int event) override;

	/* PTS delta with 33-bit wrap-around (standard DVB/MPEG behavior). */
	static inline pts_t pts_delta(pts_t newer, pts_t older) { return (newer - older) & ((1LL << 33) - 1); }

	/* Shared ownership with eRamTsSource — reader and writer both
	 * need the buffer alive until both are done. */
	std::shared_ptr<eRamRingBuffer> m_ram_ring;

	/* 200ms periodic watchdog that detects ring-buffer lap events
	 * and forces the push thread to jump to the safe read position. */
	ePtr<eTimer> m_watchdog_timer;

	/* Buffer size in bytes (aligned down to 188 in eRamRingBuffer). */
	size_t m_capacity_bytes;

	/* iTsSource wrapping the ring buffer for eFilePushThread. */
	ePtr<eRamTsSource> m_ts_source;

	/* Raw pointer to the RAM recorder thread — owned by m_record via
	 * replaceThread().  Valid for the lifetime of m_record only.
	 * DO NOT delete — m_record owns the lifecycle through the
	 * eDVBRecordScrambledThread base. */
	eRamRecorder* m_ram_recorder;

	/* Frozen play position captured at stream corruption detection.
	 * On Hisilicon, getPTS() advances even during pause (HW decoder
	 * drains internal buffer).  Freezing prevents current_delay from
	 * shrinking, which would cause the Precise Recovery System to
	 * loop forever waiting for a stable PTS. */
	pts_t m_frozen_play_position;
};

#endif /* __lib_service_eramserviceplay_h */
