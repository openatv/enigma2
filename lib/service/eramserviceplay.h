#ifndef __lib_service_eramserviceplay_h
#define __lib_service_eramserviceplay_h

#include <lib/base/ebase.h>
#include <lib/dvb/eramtimeshift.h>
#include <lib/service/servicedvb.h>
#include <memory>

// Extends eDVBServicePlay to store timeshift data in RAM instead of disk.
// Pause triggers startTimeshift() into a ring buffer; unpause calls
// activateTimeshift() to play back at the accumulated delay.
// Seeking is disabled to avoid PCR history search issues on high-bitrate channels.
// Enabled when eSettings::ram_timeshift_delay_seconds > 0.
class eRamServicePlay : public eDVBServicePlay {
	DECLARE_REF(eRamServicePlay);

public:
	eRamServicePlay(const eServiceReference& ref, eDVBService* service, int delay_seconds = 10);
	~eRamServicePlay() override;

	// Status helpers
	bool  isRamBufferReady()    const; // ring buffer has received at least one write
	float ramBufferedSeconds()  const; // seconds elapsed since first data
	int   ramFillPercent()      const; // percentage of ring buffer currently used

	// Position / length (PTS-based)
	RESULT getLength(pts_t& len)      override;
	RESULT getPlayPosition(pts_t& pos) override;

	// Seek disabled for RAM timeshift
	RESULT seekTo(pts_t to)                        override;
	RESULT seekRelative(int direction, pts_t to)   override;

	// Timeshift management
	RESULT activateTimeshift()              override;
	RESULT saveTimeshiftFile()              override; // no-op: nothing on disk
	void   serviceEventTimeshift(int event) override;

protected:
	RESULT startTimeshift()                                              override;
	RESULT stopTimeshift(bool swToLive = false)                         override;
	ePtr<iTsSource> createTsSource(eServiceReferenceDVB& ref, int packetsize = 188) override;

private:
	void checkLapAndSeek();       // watchdog: detect ring-buffer lap and recover
	void recordEvent(int event)   override; // freeze position on stream corruption

	// Safe PTS delta with 33-bit wrap-around (DVB/MPEG standard).
	static inline pts_t pts_delta(pts_t newer, pts_t older) { return (newer - older) & ((1LL << 33) - 1); }

	std::shared_ptr<eRamRingBuffer> m_ram_ring;   // shared with eRamTsSource
	ePtr<eTimer>      m_watchdog_timer;            // 200 ms lap-detection watchdog
	size_t            m_capacity_bytes;            // total ring buffer size
	ePtr<eRamTsSource> m_ts_source;               // iTsSource wrapper for eFilePushThread

	// Owned by m_record via replaceThread(); must NOT be deleted directly.
	eRamRecorder* m_ram_recorder;

	// Frozen play position (PTS delta) captured at stream-corruption onset.
	// Prevents PRS from seeing a spuriously advancing getPTS() during pause.
	pts_t m_frozen_play_position;
};

#endif // __lib_service_eramserviceplay_h