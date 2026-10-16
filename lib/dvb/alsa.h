#ifndef __LIB_DRIVER_ALSA_H_
#define __LIB_DRIVER_ALSA_H_

#include <lib/base/thread.h>
#include <lib/base/elock.h>
#include <lib/base/cfile.h>

#include <alsa/asoundlib.h>
#include <atomic>
#include <semaphore.h>
#include <string>
#include <vector>

#ifndef AV_NOPTS_VALUE
#define AV_NOPTS_VALUE          ((int64_t)UINT64_C(0x8000000000000000))
#endif

struct FrameSlot
{
    int64_t  pts;
    uint8_t *data;
    uint32_t len;
};

class eFrameFifo
{
private:
    uint32_t              m_num_slots;
    uint32_t              m_slot_capacity;
    uint32_t              m_write_idx;
    uint32_t              m_read_idx;
    std::vector<FrameSlot> m_slots;
    sem_t                 m_space_sem;
    sem_t                 m_data_sem;
    pthread_mutex_t       m_mutex;
    std::atomic<bool>     m_stopped;
    std::atomic<uint64_t> m_total_bytes_pushed;
    std::atomic<uint64_t> m_total_bytes_pulled;

public:
    eFrameFifo(uint32_t num_slots, uint32_t slot_capacity);
    ~eFrameFifo();

    int put(int64_t pts, const uint8_t *buf, uint32_t len);
    int get(uint8_t *buf_out, uint32_t buf_size, int64_t *pts_out);
    int try_get(uint8_t *buf_out, uint32_t buf_size, int64_t *pts_out);
    int64_t peek_pts();
    bool drop_one();
    void flush();
    uint32_t fill();
    uint32_t space();
    uint32_t fill_bytes();
    void stop();
    void resume();

    uint64_t total_bytes_pushed() const { return m_total_bytes_pushed.load(std::memory_order_relaxed); }
    uint64_t total_bytes_pulled() const { return m_total_bytes_pulled.load(std::memory_order_relaxed); }
    uint32_t num_slots()     const { return m_num_slots; }
    uint32_t slot_capacity() const { return m_slot_capacity; }
};

class eAlsaOutput : public eThread
{
protected:
    snd_pcm_t        *m_handle;
    unsigned int      m_sample_rate;
    unsigned int      m_channels;
    unsigned int      m_bytes_per_sample;
    unsigned int      m_passthrough;
    std::string       m_device;
    int               m_stop;          /* 1 = idle, 0 = playing */
    int               m_shutdown;      /* destructor sets this */
    int               m_thread_idle;   /* 1 = safe to reconfigure */
    int               m_writer_paused; /* 1 = writer holds (user PVR pause) */
    pthread_mutex_t   m_state_mutex;
    pthread_cond_t    m_state_cond;

    int64_t           m_calced_apts;        /* -1 = re-anchor on next chunk */
    int               m_sync_log_count;
    bool              m_pcr_offset_computed;
    int               m_applied_delay_ms;
    int               m_huge_drift_count;
    std::atomic<int>  m_pending_delay_delta_ms;
    std::atomic<int>  m_user_delay_ms;
    std::atomic<int64_t> m_last_user_delay_change_ms;

    int  openAlsa();
    void closeAlsa();
    int  configureAlsa();

    int     m_pcr_demux_fd;
    int     m_pcr_demux_adapter;
    int     m_pcr_demux_idx;
    int64_t readPcrScr() const;

    /* 1 = writer waits for FIFO to refill after flushOnSeek so the next
     * anchor reads stable chunk-PTS/PCR. */
    int     m_post_flush_preroll_pending;

    unsigned int m_diag_sleep_count;
    bool         m_diag_pcr_noseen;

    /* Singleton state */
    static eAlsaOutput     *s_instance;
    static pthread_mutex_t  s_instance_mutex;
    static int64_t          s_post_seek_window_until_ms;

public:
    eFrameFifo  *m_fifo;

    /* nullptr = just get current instance; non-null = switch device if needed. */
    static eAlsaOutput *instance(const char *device = nullptr);

    /* Current video codec (debug log only). */
    static void setVideoType(int vtype);

    /* idx<0 closes existing fd. */
    int setPcrDemux(int adapter, int idx);

    int switchDevice(const char *new_device);
    void releaseHandle();

    eAlsaOutput(const char *device_name);
    virtual ~eAlsaOutput();

    int  start(unsigned int sample_rate, unsigned int channels,
               unsigned int bytes_per_sample, unsigned int passthrough,
               int delay_ms = 0);
    /* Switch device + start passthrough. Standard 48k/2ch, HBR 192k/8ch. */
    int  startPassthrough(const char *device, unsigned int rate = 48000,
                          unsigned int channels = 2);
    void stop();
    int  pushData(uint8_t *data, int size, int64_t pts);
    bool running() const { return m_handle != nullptr; }

    /* User-initiated seek (seekTo/seekRelative/FF-stop). Drop in-flight chunks,
     * arm re-anchor on next chunk, signal kernel tsync discontinuity so the
     * pacer drops the now-stale pts_audio/pts_video and re-locks on fresh PCR. */
    void flushOnSeek();

    /* User PVR/Timeshift pause: writer thread drains the ALSA HW buffer
     * (snd_pcm_drain → state SETUP) and waits on m_state_cond. FIFO is
     * NOT touched, so on resumeWriter the buffered chunks still match the
     * frozen STC and audio resumes from exactly where it left off. */
    void pauseWriter();
    void resumeWriter();

    void thread();   /* writer thread loop */

    unsigned int sample_rate() const { return m_sample_rate; }
    unsigned int channels()    const { return m_channels; }
    bool         passthrough() const { return m_passthrough != 0; }

    void applyAudioPtsOffset();
};

#endif // __LIB_DRIVER_ALSA_H_
