#ifndef __LIB_DVB_AVSYNC_CORE_H_
#define __LIB_DVB_AVSYNC_CORE_H_

#include <pthread.h>
#include <stdint.h>

/* /dev/tsync ioctl + /sys/class/tsync sysfs wrapper for AMLogic
 * kernel PCR-master sync. Singleton, thread-safe via mutex. */
class eAVSyncCore
{
public:
	static eAVSyncCore *getInstance();

	/* Write /sys/class/tsync/{enable,mode}. Idempotent. */
	int enableKernelSync();

	/* Trigger tsync_pcr_start via TSYNC_IOC_SET_DEMUX_INFO.
	 * Use 0x1FFF for any PID that is absent. */
	int setDemuxInfo(int demux_device_id, int index,
					 int vpid, int apid, int pcrpid);

	/* Trigger tsync_pcr_stop via TSYNC_IOC_STOP_TSYNC_PCR. */
	int stopPCRSync();

	/* /proc/stb/pcr_offset in 90 kHz units (HW pipeline latency). */
	int setPCROffset(int offset_90khz);

	/* /proc/stb/auto_pcr_offset — usually 0 (disabled). */
	int setAutoPCROffset(int offset_90khz);

	/* Current kernel-tracked PCR / video PTS via sysfs. */
	int64_t readPtsPcrscr();
	int64_t readPtsVideo();
	int64_t readDemuxPcr();
	/* (demux_pcr - pts_pcrscr) in ms — kernel pacer lag. */
	int     readPcrscrLagMs();

	bool kernelSyncActive() const { return m_kernel_sync_active; }

	/* True when last setDemuxInfo got pcrpid=0x1FFF. Set by both SW-descramble
	 * paths (eDVBSoftDecoder = in-process CSA, m_is_stream = oscam SR relay)
	 * because both call setSyncPCR(-1). Kernel-pacer has no real stream PCR,
	 * demux_pcr is synthesized from first PES. */
	bool isPCRPidAbsent() const { return m_pcrpid_absent; }

private:
	eAVSyncCore();
	~eAVSyncCore();

	/* Lazy /dev/tsync open, protected by m_tsync_mutex. */
	int openTsync();

	static int writeNode(const char *path, const char *value);
	static int writeHex(const char *path, unsigned int value);
	static int64_t readHex(const char *path);

	int m_tsync_fd;             /* /dev/tsync, lazy-opened */
	bool m_kernel_sync_active;
	bool m_pcrpid_absent;       /* pcrpid==0x1FFF in last setDemuxInfo */
	pthread_mutex_t m_tsync_mutex;

	static eAVSyncCore *s_instance;
	static pthread_mutex_t s_instance_mutex;
};

#endif /* __LIB_DVB_AVSYNC_CORE_H_ */
