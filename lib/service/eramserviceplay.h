#ifndef __lib_service_eramserviceplay_h
#define __lib_service_eramserviceplay_h

#include <lib/service/servicedvb.h>
#include <lib/dvb/eramtimeshift.h>
#include <lib/base/ebase.h>
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
 * Enabled via: config.timeshift.ram_mode = true
 * Instantiated by eServiceFactoryDVB::play() when that config is set.
 */
class eRamServicePlay : public eDVBServicePlay
{
	DECLARE_REF(eRamServicePlay);
public:
	eRamServicePlay(const eServiceReference &ref,
	                eDVBService *service,
	                int delay_seconds = 10);
	virtual ~eRamServicePlay();

	bool	isRamBufferReady() const;
	float	ramBufferedSeconds() const;
	int	ramFillPercent() const;

	RESULT	getLength(pts_t &len) override;
	RESULT	getPlayPosition(pts_t &pos) override;
	RESULT	seekTo(pts_t to) override;
	RESULT	seekRelative(int direction, pts_t to) override;
	RESULT	activateTimeshift() override;
	RESULT	saveTimeshiftFile() override;
	void	serviceEventTimeshift(int event) override;

protected:
	RESULT	startTimeshift() override;
	RESULT	stopTimeshift(bool swToLive = false) override;

	ePtr<iTsSource> createTsSource(eServiceReferenceDVB &ref,
	                               int packetsize = 188) override;

private:
	void	checkLapAndSeek();
	void	recordEvent(int event) override;

	static inline pts_t pts_delta(pts_t newer, pts_t older)
	{ return (newer - older) & ((1LL << 33) - 1); }

	std::shared_ptr<eRamRingBuffer>	m_ram_ring;
	ePtr<eTimer>			m_watchdog_timer;
	size_t				m_capacity_bytes;
	ePtr<eRamTsSource>		m_ts_source;

	/* Raw pointer to the RAM recorder thread — owned by m_record via
	 * replaceThread(). Valid for the lifetime of m_record. */
	eRamRecorder			*m_ram_recorder;
	pts_t				m_frozen_play_position;
};

#endif /* __lib_service_eramserviceplay_h */
