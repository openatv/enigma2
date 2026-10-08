#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/dvb/alsa.h>
#include <lib/dvb/avsync_core.h>
#include <lib/dvb/volume.h>
#include <lib/dvb/decoder.h>

#include <inttypes.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <linux/dvb/dmx.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <limits.h>
#include <pthread.h>
#include <sched.h>

#define ALSA_OPEN_MAX_RETRIES    5
#define ALSA_OPEN_RETRY_DELAY_MS 50

#define SYNC_LOG_EVERY            10    /* heartbeat throttle: every Nth writei */
#define PERIODIC_REANCHOR_MS      30000 /* periodic re-anchor every 30s (kernel-pacer kick) */

static void tsync_write_int(const char *path, int v)
{
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "%d", v);
    fclose(f);
}

static int64_t readTsyncFile(const char *path)
{
    FILE *f = fopen(path, "r");
    if (!f) return AV_NOPTS_VALUE;
    unsigned int x = 0;
    int n = fscanf(f, "0x%x", &x);
    fclose(f);
    if (n != 1 || x == 0) return AV_NOPTS_VALUE;
    return (int64_t)(uint32_t)x;
}

static inline void apply_software_volume(int16_t *samples, size_t count_samples, int vol100)
{
    if (vol100 >= 100) return;
    if (vol100 <= 0) { memset(samples, 0, count_samples * sizeof(int16_t)); return; }
    for (size_t i = 0; i < count_samples; ++i)
        samples[i] = (int16_t)((int32_t)samples[i] * vol100 / 100);
}

/* ═════════════ eFrameFifo ═════════ */

eFrameFifo::eFrameFifo(uint32_t num_slots, uint32_t slot_capacity)
    : m_num_slots(num_slots),
      m_slot_capacity(slot_capacity),
      m_write_idx(0),
      m_read_idx(0),
      m_slots(num_slots),
      m_stopped(false),
      m_total_bytes_pushed(0),
      m_total_bytes_pulled(0)
{
    for (uint32_t i = 0; i < num_slots; ++i) {
        m_slots[i].data = (uint8_t *)malloc(slot_capacity);
        m_slots[i].pts  = AV_NOPTS_VALUE;
        m_slots[i].len  = 0;
    }
    sem_init(&m_space_sem, 0, num_slots);
    sem_init(&m_data_sem,  0, 0);
    pthread_mutex_init(&m_mutex, nullptr);
}

eFrameFifo::~eFrameFifo()
{
    stop();
    for (uint32_t i = 0; i < m_num_slots; ++i) free(m_slots[i].data);
    sem_destroy(&m_space_sem);
    sem_destroy(&m_data_sem);
    pthread_mutex_destroy(&m_mutex);
}

int eFrameFifo::put(int64_t pts, const uint8_t *buf, uint32_t len)
{
    if (m_stopped.load(std::memory_order_acquire)) return -1;
    if (!buf || len == 0) return 0;

    while (len > 0) {
        uint32_t chunk = (len > m_slot_capacity) ? m_slot_capacity : len;
        while (sem_wait(&m_space_sem) != 0) {
            if (errno != EINTR) return -1;
        }
        if (m_stopped.load(std::memory_order_acquire)) {
            sem_post(&m_space_sem);
            return -1;
        }

        pthread_mutex_lock(&m_mutex);
        FrameSlot &s = m_slots[m_write_idx];
        memcpy(s.data, buf, chunk);
        s.len = chunk;
        s.pts = pts;
        m_write_idx = (m_write_idx + 1) % m_num_slots;
        pthread_mutex_unlock(&m_mutex);

        m_total_bytes_pushed.fetch_add(chunk, std::memory_order_relaxed);
        sem_post(&m_data_sem);

        buf += chunk;
        len -= chunk;
    }
    return 0;
}

int eFrameFifo::get(uint8_t *buf_out, uint32_t buf_size, int64_t *pts_out)
{
    if (m_stopped.load(std::memory_order_acquire)) return 0;
    while (sem_wait(&m_data_sem) != 0) {
        if (errno != EINTR) return 0;
    }
    if (m_stopped.load(std::memory_order_acquire)) {
        sem_post(&m_data_sem);
        return 0;
    }

    pthread_mutex_lock(&m_mutex);
    FrameSlot &s = m_slots[m_read_idx];
    uint32_t n = (s.len > buf_size) ? buf_size : s.len;
    if (buf_out && n > 0) memcpy(buf_out, s.data, n);
    if (pts_out) *pts_out = s.pts;
    m_read_idx = (m_read_idx + 1) % m_num_slots;
    pthread_mutex_unlock(&m_mutex);

    m_total_bytes_pulled.fetch_add(n, std::memory_order_relaxed);
    sem_post(&m_space_sem);
    return (int)n;
}

int eFrameFifo::try_get(uint8_t *buf_out, uint32_t buf_size, int64_t *pts_out)
{
    if (m_stopped.load(std::memory_order_acquire)) return 0;
    if (sem_trywait(&m_data_sem) != 0) return 0;
    if (m_stopped.load(std::memory_order_acquire)) {
        sem_post(&m_data_sem);
        return 0;
    }

    pthread_mutex_lock(&m_mutex);
    FrameSlot &s = m_slots[m_read_idx];
    uint32_t n = (s.len > buf_size) ? buf_size : s.len;
    if (buf_out && n > 0) memcpy(buf_out, s.data, n);
    if (pts_out) *pts_out = s.pts;
    m_read_idx = (m_read_idx + 1) % m_num_slots;
    pthread_mutex_unlock(&m_mutex);

    m_total_bytes_pulled.fetch_add(n, std::memory_order_relaxed);
    sem_post(&m_space_sem);
    return (int)n;
}

int64_t eFrameFifo::peek_pts()
{
    int val = 0;
    if (sem_getvalue(&m_data_sem, &val) != 0 || val == 0) return AV_NOPTS_VALUE;
    pthread_mutex_lock(&m_mutex);
    int64_t pts = m_slots[m_read_idx].pts;
    pthread_mutex_unlock(&m_mutex);
    return pts;
}

bool eFrameFifo::drop_one()
{
    if (sem_trywait(&m_data_sem) != 0) return false;
    pthread_mutex_lock(&m_mutex);
    uint32_t n = m_slots[m_read_idx].len;
    m_read_idx = (m_read_idx + 1) % m_num_slots;
    pthread_mutex_unlock(&m_mutex);
    m_total_bytes_pulled.fetch_add(n, std::memory_order_relaxed);
    sem_post(&m_space_sem);
    return true;
}

void eFrameFifo::flush()
{
    pthread_mutex_lock(&m_mutex);
    m_write_idx = 0;
    m_read_idx  = 0;
    pthread_mutex_unlock(&m_mutex);
    while (sem_trywait(&m_data_sem)  == 0) {}
    while (sem_trywait(&m_space_sem) == 0) {}
    for (uint32_t i = 0; i < m_num_slots; ++i) sem_post(&m_space_sem);
}

uint32_t eFrameFifo::fill()
{
    int val = 0;
    sem_getvalue(&m_data_sem, &val);
    return val < 0 ? 0 : (uint32_t)val;
}

uint32_t eFrameFifo::space()
{
    int val = 0;
    sem_getvalue(&m_space_sem, &val);
    return val < 0 ? 0 : (uint32_t)val;
}

uint32_t eFrameFifo::fill_bytes()
{
    pthread_mutex_lock(&m_mutex);
    uint32_t bytes = 0;
    uint32_t f = (m_write_idx >= m_read_idx)
        ? (m_write_idx - m_read_idx)
        : (m_num_slots - m_read_idx + m_write_idx);
    for (uint32_t i = 0; i < f; ++i) {
        uint32_t idx = (m_read_idx + i) % m_num_slots;
        bytes += m_slots[idx].len;
    }
    pthread_mutex_unlock(&m_mutex);
    return bytes;
}

void eFrameFifo::stop()
{
    m_stopped.store(true, std::memory_order_release);
    sem_post(&m_space_sem);
    sem_post(&m_data_sem);
}

void eFrameFifo::resume()
{
    m_stopped.store(false, std::memory_order_release);
}

/* AML mute switch persists across close+open; force ON. */
static void forceMuteSwitchOn()
{
    snd_mixer_t *mh = nullptr;
    if (snd_mixer_open(&mh, 0) != 0) return;
    if (snd_mixer_attach(mh, "hw:0") == 0
        && snd_mixer_selem_register(mh, NULL, NULL) == 0
        && snd_mixer_load(mh) == 0)
    {
        snd_mixer_selem_id_t *sid;
        snd_mixer_selem_id_alloca(&sid);
        snd_mixer_selem_id_set_index(sid, 0);
        snd_mixer_selem_id_set_name(sid, "Master");
        snd_mixer_elem_t *e = snd_mixer_find_selem(mh, sid);
        if (e && snd_mixer_selem_has_playback_switch(e))
            snd_mixer_selem_set_playback_switch_all(e, 1);
    }
    snd_mixer_close(mh);
}

int eAlsaOutput::openAlsa()
{
    int err = 0;
    for (int i = 0; i < ALSA_OPEN_MAX_RETRIES; ++i)
    {
        err = snd_pcm_open(&m_handle, m_device.c_str(),
                           SND_PCM_STREAM_PLAYBACK, SND_PCM_NONBLOCK);
        if (err == 0) break;
        if (err == -EBUSY && i < ALSA_OPEN_MAX_RETRIES - 1) {
            usleep(ALSA_OPEN_RETRY_DELAY_MS * 1000);
            m_handle = nullptr;
            continue;
        }
        eDebug("[eAlsaOutput] open '%s' failed: %s", m_device.c_str(), snd_strerror(err));
        m_handle = nullptr;
        return err;
    }
    snd_pcm_nonblock(m_handle, 0);
    return 0;
}

void eAlsaOutput::closeAlsa()
{
    if (m_handle) {
        snd_pcm_drop(m_handle);
        snd_pcm_close(m_handle);
        m_handle = nullptr;
        usleep(10000);
    }
}

int eAlsaOutput::configureAlsa()
{
    if (!m_handle) return -1;
    snd_pcm_hw_params_t *hw;
    snd_pcm_hw_params_alloca(&hw);

    int err;
    unsigned int rate = m_sample_rate, chans = m_channels;

    snd_pcm_hw_params_any(m_handle, hw);
    snd_pcm_hw_params_set_access(m_handle, hw, SND_PCM_ACCESS_RW_INTERLEAVED);
    snd_pcm_hw_params_set_format(m_handle, hw, SND_PCM_FORMAT_S16);
    snd_pcm_hw_params_set_rate_near(m_handle, hw, &rate, NULL);
    snd_pcm_hw_params_set_channels_near(m_handle, hw, &chans);

    /* Explicit period_size required: set_periods_near alone produces 32-frame
     * periods on this AML kernel and underruns on any pause > 0.7ms. */
    snd_pcm_uframes_t period_size = ((snd_pcm_uframes_t)rate * 1024) / 48000;
    snd_pcm_uframes_t buffer_size = period_size * 8;
    snd_pcm_hw_params_set_period_size_near(m_handle, hw, &period_size, NULL);
    snd_pcm_hw_params_set_buffer_size_near(m_handle, hw, &buffer_size);
    if ((err = snd_pcm_hw_params(m_handle, hw)) < 0)
    { eDebug("[eAlsaOutput] hw_params: %s", snd_strerror(err)); return -1; }

    snd_pcm_hw_params_get_period_size(hw, &period_size, NULL);
    snd_pcm_hw_params_get_buffer_size(hw, &buffer_size);
    eDebug("[eAlsaOutput] hw_params: %lu frames buf, %lu frames period",
           (unsigned long)buffer_size, (unsigned long)period_size);

    snd_pcm_sw_params_t *sw;
    snd_pcm_sw_params_alloca(&sw);
    snd_pcm_sw_params_current(m_handle, sw);
    if (m_passthrough) {
        /* Manual start; no silence-pad so underrun → EPIPE → shared recovery. */
        snd_pcm_sw_params_set_start_threshold(m_handle, sw, (snd_pcm_uframes_t)INT_MAX);
        snd_pcm_sw_params_set_stop_threshold(m_handle, sw, buffer_size);
        snd_pcm_sw_params_set_silence_threshold(m_handle, sw, 0);
        snd_pcm_sw_params_set_silence_size(m_handle, sw, 0);
    } else {
        snd_pcm_sw_params_set_start_threshold(m_handle, sw, 1);
        snd_pcm_sw_params_set_stop_threshold(m_handle, sw, buffer_size);
        snd_pcm_sw_params_set_silence_threshold(m_handle, sw, 0);
        snd_pcm_sw_params_set_silence_size(m_handle, sw, 0);
    }
    int sw_err = snd_pcm_sw_params(m_handle, sw);
    if (sw_err < 0)
        eDebug("[eAlsaOutput] sw_params: %s", snd_strerror(sw_err));

    m_sample_rate = rate;
    m_channels    = chans;
    return 0;
}

eAlsaOutput     *eAlsaOutput::s_instance        = nullptr;
pthread_mutex_t  eAlsaOutput::s_instance_mutex  = PTHREAD_MUTEX_INITIALIZER;
static int       s_video_type                   = -1;   /* set by decoder.cpp setState */

eAlsaOutput *eAlsaOutput::instance(const char *device)
{
    pthread_mutex_lock(&s_instance_mutex);
    if (!s_instance) {
        const char *dev = device ? device : "dreamhdmi";
        s_instance = new eAlsaOutput(dev);
        eDebug("[eAlsaOutput] singleton created on device '%s'", dev);
    } else if (device && s_instance->m_device != device) {
        eDebug("[eAlsaOutput] singleton device switch '%s' -> '%s'",
               s_instance->m_device.c_str(), device);
        s_instance->switchDevice(device);
    }
    pthread_mutex_unlock(&s_instance_mutex);
    return s_instance;
}

void eAlsaOutput::releaseHandle()
{
    /* Park audio thread in IDLE so it won't touch m_handle, then close. */
    if (!m_stop) stop();
    closeAlsa();
    eDebug("[eAlsaOutput] handle released — next start() will re-open");
}

void eAlsaOutput::setVideoType(int vtype)
{
    pthread_mutex_lock(&s_instance_mutex);
    s_video_type = vtype;
    pthread_mutex_unlock(&s_instance_mutex);
}

int eAlsaOutput::startPassthrough(const char *device, unsigned int rate, unsigned int channels)
{
    if (!device || !*device) return -1;
    if (switchDevice(device) < 0) return -1;
    return start(rate, channels, /*bytes_per_sample=*/2, /*passthrough=*/1, 0);
}

int eAlsaOutput::switchDevice(const char *new_device)
{
    if (!new_device || m_device == new_device) return 0;
    /* Stop any active playback first — caller will restart with start(). */
    if (!m_stop) stop();
    closeAlsa();
    /* Switch to direct hw:0,N: 300ms settle for dmix slave release (else EIO). */
    bool to_direct_hw = (strncmp(new_device, "hw:", 3) == 0);
    if (to_direct_hw) usleep(300 * 1000);
    m_device = new_device;
    if (openAlsa() < 0) {
        eDebug("[eAlsaOutput] switchDevice: openAlsa failed for '%s'", new_device);
        return -1;
    }
    return 0;
}

eAlsaOutput::eAlsaOutput(const char *device_name)
    : m_handle(nullptr)
    , m_sample_rate(0), m_channels(0), m_bytes_per_sample(0), m_passthrough(0)
    , m_device(device_name ? device_name : "default")
    , m_stop(1)
    , m_shutdown(0)
    , m_thread_idle(0)
    , m_writer_paused(0)
    , m_calced_apts(-1)
    , m_sync_log_count(0)
    , m_pcr_offset_computed(false)
    , m_applied_delay_ms(0)
    , m_huge_drift_count(0)
    , m_pending_delay_delta_ms(0)
    , m_user_delay_ms(0)
    , m_last_user_delay_change_ms(0)
    , m_pcr_demux_fd(-1)
    , m_pcr_demux_adapter(-1)
    , m_pcr_demux_idx(-1)
    , m_post_flush_preroll_pending(0)
    , m_diag_sleep_count(0)
    , m_diag_pcr_noseen(false)
    , m_fifo(nullptr)
{
    pthread_mutex_init(&m_state_mutex, nullptr);
    pthread_cond_init(&m_state_cond, nullptr);
    openAlsa();
    m_fifo = new eFrameFifo(128, 8192);
    run();
}

eAlsaOutput::~eAlsaOutput()
{
    pthread_mutex_lock(&m_state_mutex);
    m_shutdown = 1;
    m_stop = 1;
    pthread_cond_broadcast(&m_state_cond);
    pthread_mutex_unlock(&m_state_mutex);
    if (m_fifo) m_fifo->stop();
    kill();
    closeAlsa();
    if (m_pcr_demux_fd >= 0) { ::close(m_pcr_demux_fd); m_pcr_demux_fd = -1; }
    if (m_fifo) { delete m_fifo; m_fifo = nullptr; }
    pthread_cond_destroy(&m_state_cond);
    pthread_mutex_destroy(&m_state_mutex);
}

int eAlsaOutput::start(unsigned int sample_rate, unsigned int channels,
                       unsigned int bytes_per_sample, unsigned int passthrough,
                       int delay_ms)
{
    /* Keep dmix attach alive across channel zaps; reconfigure only on changes. */
    bool was_released = (m_handle == nullptr);
    if (!m_handle) {
        if (openAlsa() < 0) return -1;
    }
    if (!m_stop) stop();
    if (was_released) {
        eDebug("[eAlsaOutput] re-opened after release, settle 300ms for HW mode switch");
        usleep(300 * 1000);
    }

    snd_pcm_drop(m_handle);

    bool params_changed = (m_sample_rate      != sample_rate ||
                           m_channels         != channels ||
                           m_bytes_per_sample != bytes_per_sample ||
                           m_passthrough      != passthrough);

    m_sample_rate      = sample_rate;
    m_channels         = channels;
    m_bytes_per_sample = bytes_per_sample;
    m_passthrough      = passthrough;

    /* hw_free forces dmix slave re-negotiation, otherwise first writei
     * after a release returns -EIO. */
    if (params_changed || was_released) {
        snd_pcm_hw_free(m_handle);
        if (configureAlsa() < 0) return -1;
    }
    snd_pcm_prepare(m_handle);

    tsync_write_int("/sys/class/tsync/mode", 2);     /* pcrmaster */
    tsync_write_int("/sys/class/tsync/enable", 1);

    forceMuteSwitchOn();

    m_calced_apts        = -1;
    m_sync_log_count     = 0;
    m_pcr_offset_computed = false;
    m_huge_drift_count   = 0;
    m_diag_sleep_count   = 0;
    m_diag_pcr_noseen    = false;

    if (m_fifo) m_fifo->flush();
    if (m_fifo) m_fifo->resume();

    eDebug("[eAlsaOutput] start: %s rate=%u ch=%u mode=%s",
           m_device.c_str(), sample_rate, channels,
           passthrough ? "passthrough" : "PCM");

    pthread_mutex_lock(&m_state_mutex);
    m_stop = 0;
    pthread_cond_broadcast(&m_state_cond);
    pthread_mutex_unlock(&m_state_mutex);

    applyAudioPtsOffset();
    return 0;
}

void eAlsaOutput::applyAudioPtsOffset()
{
    /* Passthrough has no effect either way (DreamOS verified); AVR lipsync only. */
    if (m_passthrough) return;
    int ms = eTSMPEGDecoder::getStaticPCMDelay();
    if (ms == -1) ms = 0;
    /* Negative → kernel (pts_offset skip-ahead). Positive → userspace
     * silence-pad; the kernel can't insert silence behind our ALSA path. */
    int kernel_ms  = ms < 0 ? ms : 0;
    int silence_ms = ms > 0 ? ms : 0;
    int silence_delta = silence_ms - m_applied_delay_ms;
    if (silence_delta == 0 && kernel_ms == 0 && m_user_delay_ms.load(std::memory_order_relaxed) == 0)
        return;
    char buf[16];
    snprintf(buf, sizeof(buf), "%x", (unsigned int)(kernel_ms * 90));
    if (FILE *f = fopen("/proc/stb/audio/pts_offset", "w")) {
        fputs(buf, f);
        fclose(f);
    }
    m_applied_delay_ms = silence_ms;
    m_user_delay_ms.store(ms, std::memory_order_relaxed);
    if (silence_delta != 0) {
        m_pending_delay_delta_ms.fetch_add(silence_delta, std::memory_order_relaxed);
        struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
        m_last_user_delay_change_ms.store(
            (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000,
            std::memory_order_relaxed);
    }
    eDebug("[eAlsaOutput] AV-delay %+dms (kernel=%+dms silence_delta=%+dms)",
           ms, kernel_ms, silence_delta);
}

void eAlsaOutput::stop()
{
    pthread_mutex_lock(&m_state_mutex);
    if (m_stop) { pthread_mutex_unlock(&m_state_mutex); return; }
    eDebug("[eAlsaOutput] stop");
    m_stop = 1;
    pthread_cond_broadcast(&m_state_cond);
    pthread_mutex_unlock(&m_state_mutex);
    if (m_fifo) m_fifo->stop();
    pthread_mutex_lock(&m_state_mutex);
    while (!m_thread_idle && !m_shutdown)
        pthread_cond_wait(&m_state_cond, &m_state_mutex);
    pthread_mutex_unlock(&m_state_mutex);
    /* Fresh next-channel ALSA buffer holds no prior silence-pad. Clearing
     * here prevents a stale delta on the next applyAudioPtsOffset call
     * from rewinding the new channel's audio. */
    m_applied_delay_ms = 0;
    m_pending_delay_delta_ms.store(0, std::memory_order_relaxed);
}

/* Active when CLOCK_MONOTONIC < value: defer/PCR-skip/flush enabled.
 * Set only by flushOnSeek so LiveTV is never affected. */
int64_t eAlsaOutput::s_post_seek_window_until_ms = 0;

void eAlsaOutput::flushOnSeek()
{
    if (!m_fifo) return;
    pthread_mutex_lock(&m_state_mutex);
    m_fifo->flush();
    m_calced_apts = -1;
    g_audio_request_codec_flush.store(true, std::memory_order_relaxed);
    {
        struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
        s_post_seek_window_until_ms = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000 + 10000;
    }
    /* Hold writer until FIFO has ~1.2s buffered so chunk-PTS / PCR settle
     * before the first anchor reads them. */
    m_post_flush_preroll_pending = 1;
    /* m_pcr_offset_computed stays set — pcr_offset is a one-shot
     * pipeline-latency constant, re-computing it on seek poisons it. */
    pthread_mutex_unlock(&m_state_mutex);
    eDebug("[eAlsaOutput] flushOnSeek: FIFO cleared, anchor re-armed (pcr_offset preserved)");
}

void eAlsaOutput::pauseWriter()
{
    pthread_mutex_lock(&m_state_mutex);
    m_writer_paused = 1;
    pthread_cond_broadcast(&m_state_cond);
    pthread_mutex_unlock(&m_state_mutex);
    eDebug("[eAlsaOutput] pauseWriter: writer will drain ALSA and hold, FIFO preserved");
}

void eAlsaOutput::resumeWriter()
{
    pthread_mutex_lock(&m_state_mutex);
    m_writer_paused = 0;
    pthread_cond_broadcast(&m_state_cond);
    pthread_mutex_unlock(&m_state_mutex);
    eDebug("[eAlsaOutput] resumeWriter: writer wakes, snd_pcm_prepare on next writei (EBADFD)");
}

int eAlsaOutput::pushData(uint8_t *data, int size, int64_t pts)
{
    if (m_stop || !m_fifo || !data || size <= 0) return -1;

    if (!m_passthrough) {
        eDVBVolumecontrol *vc = eDVBVolumecontrol::getInstance();
        int vol = vc->isMuted() ? 0 : vc->getVolume();
        if (vol != 100)
            apply_software_volume((int16_t *)data, (size_t)size / sizeof(int16_t), vol);
    }

    if (!m_fifo) return -1;
    m_fifo->put(pts, data, (uint32_t)size);
    return 0;
}

int eAlsaOutput::setPcrDemux(int adapter, int idx)
{
    if (m_pcr_demux_fd >= 0 &&
        (m_pcr_demux_adapter != adapter || m_pcr_demux_idx != idx)) {
        ::close(m_pcr_demux_fd);
        m_pcr_demux_fd = -1;
    }
    if (idx < 0) return 0;
    if (m_pcr_demux_fd >= 0) return 0;  /* same dev, keep cached */
    char path[64];
    snprintf(path, sizeof(path), "/dev/dvb/adapter%d/demux%d", adapter, idx);
    m_pcr_demux_fd = ::open(path, O_RDWR | O_NONBLOCK | O_CLOEXEC);
    if (m_pcr_demux_fd < 0) {
        eDebug("[eAlsaOutput] open %s for DMX_GET_STC failed: %m", path);
        return -1;
    }
    m_pcr_demux_adapter = adapter;
    m_pcr_demux_idx     = idx;
    eDebug("[eAlsaOutput] PCR via DMX_GET_STC on %s", path);
    return 0;
}

int64_t eAlsaOutput::readPcrScr() const
{
    if (m_pcr_demux_fd < 0) return AV_NOPTS_VALUE;
    struct dmx_stc stc = {};
    stc.base = 1;
    if (ioctl(m_pcr_demux_fd, DMX_GET_STC, &stc) < 0) return AV_NOPTS_VALUE;
    return (int64_t)stc.stc;
}

void eAlsaOutput::thread()
{
    hasStarted();

    struct sched_param sp = { 0 };
    sp.sched_priority = sched_get_priority_min(SCHED_FIFO);
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);

    static int64_t s_anchor_log_ms = 0;
    static int64_t s_post_recovery_until_ms = 0;
    static int64_t s_avdelay_reapply_at_ms = 0;
    uint8_t slot_buf[8192];

    while (!m_shutdown) {
        pthread_mutex_lock(&m_state_mutex);
        m_thread_idle = 1;
        pthread_cond_broadcast(&m_state_cond);
        while (m_stop && !m_shutdown)
            pthread_cond_wait(&m_state_cond, &m_state_mutex);
        m_thread_idle = 0;
        pthread_mutex_unlock(&m_state_mutex);
        if (m_shutdown) break;

        const size_t frame_bytes = (size_t)m_channels * m_bytes_per_sample;
        if (frame_bytes == 0 || !m_handle) continue;
        m_fifo->resume();

        while (!m_stop && m_handle) {
            /* Deferred AV-delay re-apply after EPIPE recovery. Positive path:
             * silence buffer lost on snd_pcm_prepare → re-inject. Negative
             * path: kernel pts_offset re-arms via toggle 0→user_delay. */
            if (s_avdelay_reapply_at_ms != 0) {
                struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
                int64_t now_ms = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
                if (now_ms >= s_avdelay_reapply_at_ms) {
                    if (m_user_delay_ms.load(std::memory_order_relaxed) != 0) {
                        if (FILE *f = fopen("/proc/stb/audio/pts_offset", "w")) {
                            fputs("0", f);
                            fclose(f);
                        }
                        m_applied_delay_ms = 0;
                        applyAudioPtsOffset();
                    }
                    s_avdelay_reapply_at_ms = 0;
                }
            }

            /* User pause: drain ALSA (audible tail), park on condvar.
             * FIFO is preserved; resume hits EBADFD → snd_pcm_prepare below. */
            if (m_writer_paused) {
                if (m_handle)
                    snd_pcm_drain(m_handle);
                pthread_mutex_lock(&m_state_mutex);
                while (m_writer_paused && !m_stop && !m_shutdown)
                    pthread_cond_wait(&m_state_cond, &m_state_mutex);
                pthread_mutex_unlock(&m_state_mutex);
                if (m_stop || m_shutdown) continue;
            }

            /* Post-flushOnSeek preroll: wait for 30 slots (~1.2s) so the
             * next anchor reads stable chunk-PTS/PCR. Cap at 3s. */
            if (m_post_flush_preroll_pending) {
                static int s_preroll_waited_ms = 0;
                uint32_t fill = m_fifo ? m_fifo->fill() : 0;
                if (fill >= 30 || s_preroll_waited_ms >= 3000) {
                    if (s_preroll_waited_ms > 0)
                        eDebug("[eAlsaOutput] post-flush preroll done: fifo=%u waited=%dms",
                               fill, s_preroll_waited_ms);
                    m_post_flush_preroll_pending = 0;
                    s_preroll_waited_ms = 0;
                } else {
                    usleep(20 * 1000);
                    s_preroll_waited_ms += 20;
                    continue;
                }
            }

            int64_t slot_pts = AV_NOPTS_VALUE;
            int n = m_fifo->get(slot_buf, sizeof(slot_buf), &slot_pts);
            if (n <= 0) continue;

            /* Drop NOPTS warm-up frames; can't anchor without PTS. */
            if (m_calced_apts == -1 && slot_pts == AV_NOPTS_VALUE)
                continue;

            /* Preroll-wait: hold first slot until pcr catches up to slot_pts.
             * Cap at 2s in case pcr is stuck (wrong demux fd, no data). */
            if (m_calced_apts == -1 && slot_pts != AV_NOPTS_VALUE) {
                int64_t pcr = readPcrScr();
                if (pcr == AV_NOPTS_VALUE && !m_diag_pcr_noseen) {
                    m_diag_pcr_noseen = true;
                    eDebug("[eAlsaOutput] DIAG pcr==NOPTS at first valid slot (demux_fd=%d)",
                           m_pcr_demux_fd);
                }
                int32_t check = (pcr != AV_NOPTS_VALUE)
                    ? (int32_t)((uint32_t)slot_pts - (uint32_t)pcr) / 90 : 0;
                int waited_ms = 0;
                while (pcr != AV_NOPTS_VALUE && check > 5 && check < 5000 &&
                       waited_ms < 2000 && !m_stop) {
                    usleep(50 * 1000);
                    waited_ms += 50;
                    pcr = readPcrScr();
                    if (pcr == AV_NOPTS_VALUE) break;
                    check = (int32_t)((uint32_t)slot_pts - (uint32_t)pcr) / 90;
                }
            }

            /* Anchor: record m_calced_apts and write pcr_offset once per zap. */
            if (m_calced_apts == -1 && slot_pts != AV_NOPTS_VALUE) {
                int64_t pcr = readPcrScr();
                if (pcr == AV_NOPTS_VALUE) continue;
                int32_t check = (int32_t)((uint32_t)slot_pts - (uint32_t)pcr) / 90;
                if (check < -5000 || check > 10000) continue;  /* stale */
                /* Skip startup backlog so anchor falls within audibility (50ms). */
                if (check < -50) {
                    static int s_skip_logged = 0;
                    if (s_skip_logged < 5) {
                        eDebug("[eAlsaOutput] anchor-skip stale chunk: check=%+dms fifo=%u",
                               check, m_fifo->fill());
                        s_skip_logged++;
                    }
                    continue;
                }
                /* Seek-window only: defer if |drift| > audibility, then on
                 * timeout flush FIFO + arm PCR-skip to drop stale frames. */
                {
                    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
                    int64_t now_ms = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
                    bool in_seek_window = (s_post_seek_window_until_ms != 0
                                           && now_ms < s_post_seek_window_until_ms);
                    static int64_t s_defer_start_ms = 0;
                    if (in_seek_window && (check > 100 || check < -100)) {
                        if (s_defer_start_ms == 0) s_defer_start_ms = now_ms;
                        if (now_ms - s_defer_start_ms < 1000) {
                            usleep(20 * 1000);
                            continue;
                        }
                        eDebug("[eAlsaOutput] anchor-defer timeout: check=%+dms (accepting)", check);
                        if (check < -100) {
                            g_audio_skip_until_pts.store(pcr, std::memory_order_relaxed);
                            m_fifo->flush();
                            eDebug("[eAlsaOutput] anchor-defer fallback: PCR-skip + FIFO flush, until pts=%lx", (long)pcr);
                            s_defer_start_ms = 0;
                            continue;
                        }
                    }
                    s_defer_start_ms = 0;
                }

                m_calced_apts = slot_pts;

                /* pcr_offset = demux_pcr - pts_pcrscr (mode-independent). */
                if (!m_pcr_offset_computed
                    && eAVSyncCore::getInstance()->kernelSyncActive()) {
                    int lag_ms = eAVSyncCore::getInstance()->readPcrscrLagMs();
                    if (lag_ms > 0 && lag_ms < 1500) {
                        int pcr_off = lag_ms * 90;
                        eAVSyncCore::getInstance()->setPCROffset(pcr_off);
                        eDebug("[eAlsaOutput] pcr_offset = lag(%dms) vtype=%d → 0x%x",
                               lag_ms, s_video_type, pcr_off);
                        m_pcr_offset_computed = true;
                    }
                }

                snd_pcm_sframes_t hwd = 0;
                snd_pcm_delay(m_handle, &hwd);
                if (hwd < 0) hwd = 0;
                int64_t vpts = readTsyncFile("/sys/class/tsync/pts_video");
                int64_t apts_spk = m_calced_apts - (int64_t)hwd * 90000LL / m_sample_rate;
                int32_t apcr = (int32_t)((uint32_t)apts_spk - (uint32_t)pcr) / 90;
                int32_t vpcr = 0, av = 0;
                if (vpts != AV_NOPTS_VALUE) {
                    vpcr = (int32_t)((uint32_t)vpts - (uint32_t)pcr) / 90;
                    av   = (int32_t)((uint32_t)apts_spk - (uint32_t)vpts) / 90;
                }
                eDebug("[eAlsaOutput] anchor: check=%+dms apcr=%+dms vpcr=%+dms av=%+dms alsa=%dms fifo=%u",
                       check, apcr, vpcr, av,
                       (int)(hwd * 1000 / (int)m_sample_rate),
                       m_fifo->fill());
                struct timespec ts_a; clock_gettime(CLOCK_MONOTONIC, &ts_a);
                s_anchor_log_ms = (int64_t)ts_a.tv_sec * 1000 + ts_a.tv_nsec / 1000000;
            }

            /* Userspace silence-pad for positive AV-delay; negative handled by kernel. */
            int silence_delta = m_pending_delay_delta_ms.exchange(0, std::memory_order_relaxed);
            if (silence_delta != 0 && !m_passthrough && m_sample_rate) {
                if (silence_delta > 0) {
                    snd_pcm_uframes_t df = (snd_pcm_uframes_t)
                        ((int64_t)silence_delta * m_sample_rate / 1000);
                    uint8_t zero[8192] = {0};
                    snd_pcm_uframes_t per = sizeof(zero) / frame_bytes;
                    while (df > 0 && !m_stop) {
                        snd_pcm_uframes_t k = df > per ? per : df;
                        snd_pcm_sframes_t r = snd_pcm_writei(m_handle, zero, k);
                        if (r < 0) break;
                        df -= (snd_pcm_uframes_t)r;
                    }
                } else {
                    snd_pcm_uframes_t df = (snd_pcm_uframes_t)
                        ((int64_t)(-silence_delta) * m_sample_rate / 1000);
                    snd_pcm_sframes_t avail = snd_pcm_rewindable(m_handle);
                    if (avail > 0) {
                        snd_pcm_uframes_t n = df > (snd_pcm_uframes_t)avail
                                              ? (snd_pcm_uframes_t)avail : df;
                        snd_pcm_rewind(m_handle, n);
                    }
                }
                eDebug("[eAlsaOutput] silence-pad %+dms", silence_delta);
            }

            /* Raw writei. Discontinuity handled implicitly: stream-pts jumps
             * drain the ALSA buffer → EPIPE → re-anchor below. */
            snd_pcm_uframes_t frames = (snd_pcm_uframes_t)n / frame_bytes;
            snd_pcm_sframes_t got = snd_pcm_writei(m_handle, slot_buf, frames);
            /* Manual start: passthrough has start_threshold=INT_MAX. */
            if (m_passthrough && got > 0
                && snd_pcm_state(m_handle) == SND_PCM_STATE_PREPARED)
                snd_pcm_start(m_handle);
            if (got < 0) {
                if (got == -EPIPE) {
                    static int64_t s_last_epipe = 0;
                    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
                    int64_t now_ms = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
                    if (now_ms - s_last_epipe > 1000) {
                        s_last_epipe = now_ms;
                        eDebug("[eAlsaOutput] writei EPIPE underrun");
                    }
                    snd_pcm_prepare(m_handle);
                    /* Open 30s post-recovery window: periodic re-anchor runs
                     * at 5s instead of 30s to catch kernel pts_pcrscr drift. */
                    s_post_recovery_until_ms = now_ms + 30000;
                    /* Wait for ≥6 FIFO slots before re-anchor — prevents EPIPE
                     * cascade on start_threshold=1; covers ~360ms CW-loss bursts. */
                    int waited = 0;
                    while (m_fifo->fill() < 6 && waited < 200 && !m_stop) {
                        usleep(10000);
                        waited += 10;
                    }
                } else if (got == -EBADFD) {
                    /* PCM SETUP after snd_pcm_drain at pause — prepare and
                     * force a fresh anchor against the resumed STC. */
                    snd_pcm_prepare(m_handle);
                    eDebug("[eAlsaOutput] writei EBADFD (post-pause), prepared, re-anchor");
                    m_calced_apts = -1;
                    continue;
                } else if (got == -EIO) {
                    eDebug("[eAlsaOutput] writei EIO reopen ALSA");
                    closeAlsa();
                    usleep(100 * 1000);
                    if (openAlsa() == 0) {
                        configureAlsa();
                        snd_pcm_prepare(m_handle);
                    }
                } else {
                    eDebug("[eAlsaOutput] writei=%ld %s", (long)got, snd_strerror((int)got));
                    snd_pcm_prepare(m_handle);
                }
                m_calced_apts = -1;  /* force re-anchor */
                /* Schedule AV-delay re-apply after FIFO backlog has drained
                 * (~1.5s). Fires for both directions when user_delay != 0. */
                if (m_user_delay_ms.load(std::memory_order_relaxed) != 0) {
                    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
                    s_avdelay_reapply_at_ms = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000 + 1500;
                }
                continue;
            }
            if (m_calced_apts != -1 && m_sample_rate) {
                m_calced_apts += (int64_t)got * 90000LL / (int64_t)m_sample_rate;
            }

            if (m_calced_apts != -1 && m_sample_rate) {
                m_sync_log_count++;
                if (m_sync_log_count >= SYNC_LOG_EVERY) {
                    m_sync_log_count = 0;
                    snd_pcm_sframes_t hw_delay = 0;
                    snd_pcm_delay(m_handle, &hw_delay);
                    if (hw_delay < 0) hw_delay = 0;
                    int64_t apts_spk = m_calced_apts - (int64_t)hw_delay * 90000LL / m_sample_rate;
                    int64_t pcr = readPcrScr();
                    int64_t vpts = readTsyncFile("/sys/class/tsync/pts_video");
                    if (pcr == AV_NOPTS_VALUE) continue;
                    int32_t apcr_ms = (int32_t)((uint32_t)apts_spk - (uint32_t)pcr) / 90;
                    bool have_vpts = (vpts != AV_NOPTS_VALUE);
                    int32_t vpcr_ms = 0, av_ms = 0;
                    if (have_vpts) {
                        vpcr_ms = (int32_t)((uint32_t)vpts - (uint32_t)pcr) / 90;
                        av_ms   = (int32_t)((uint32_t)apts_spk - (uint32_t)vpts) / 90;
                    }
                    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
                    int64_t now_ms = (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;

                    static int64_t s_last_log = 0;
                    int interval = (s_anchor_log_ms != 0 && now_ms - s_anchor_log_ms < 30000)
                                   ? 5000 : 30000;
                    if (now_ms - s_last_log > interval) {
                        eDebug("[eAlsaOutput] apcr=%+dms vpcr=%+dms av=%+dms alsa=%dms fifo=%u [heartbeat]",
                               apcr_ms, vpcr_ms, av_ms,
                               (int)(hw_delay * 1000 / (int)m_sample_rate),
                               m_fifo->fill());
                        s_last_log = now_ms;

                        /* Adaptive periodic re-anchor: 5s in post-recovery
                         * window, 30s steady-state. Only fires if |drift|>100ms. */
                        int64_t periodic_threshold = (s_post_recovery_until_ms != 0 && now_ms < s_post_recovery_until_ms)
                                                     ? 5000 : PERIODIC_REANCHOR_MS;
                        if (s_anchor_log_ms != 0 && (now_ms - s_anchor_log_ms) >= periodic_threshold) {
                            int user_delay = m_user_delay_ms.load(std::memory_order_relaxed);
                            int eff_drift = apcr_ms + user_delay;
                            int32_t abs_apcr = eff_drift < 0 ? -eff_drift : eff_drift;
                            int64_t last_chg = m_last_user_delay_change_ms.load(std::memory_order_relaxed);
                            bool slider_settling = last_chg != 0 && (now_ms - last_chg) < 5000;
                            if (abs_apcr > 100 && !slider_settling && user_delay == 0) {
                                eDebug("[eAlsaOutput] periodic re-anchor (drift=%+dms user_delay=%+dms)",
                                       eff_drift, m_user_delay_ms.load(std::memory_order_relaxed));
                                m_calced_apts          = -1;
                                /* Only recompute pcr_offset if drift > 500ms
                                 * persists ≥2 heartbeats (new segment, different
                                 * chunk_pts↔PCR baseline). Small drift = re-anchor only. */
                                if (abs_apcr > 500) {
                                    m_huge_drift_count++;
                                    if (m_huge_drift_count >= 2) {  /* 2 confirmed → bump */
                                        eDebug("[eAlsaOutput] one-shot av-correction: drift %+dms persistent → recompute pcr_offset",
                                               apcr_ms);
                                        m_pcr_offset_computed = false;
                                        m_huge_drift_count = 0;
                                    }
                                } else {
                                    m_huge_drift_count = 0;
                                }
                            }
                        }
                    }
                }
            }
        }
        snd_pcm_drop(m_handle);
    }
}
