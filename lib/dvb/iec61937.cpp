#include <lib/dvb/iec61937.h>
#include <lib/dvb/alsa.h>
#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>

#include <stdio.h>
#include <string.h>

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavformat/avio.h>
#include <libavutil/channel_layout.h>
#include <libavutil/opt.h>
}

/* IEC61937 Pc data type codes (lower byte) */
#define IEC61937_AC3      0x01
#define IEC61937_DTS_1K   0x0B
#define IEC61937_EAC3     0x15
#define IEC61937_AC4      0x11

/* /sys/class/audiodsp/digital_codec values:
 *   0=PCM 1=DTS 2=AC3 4=EAC3 5=DTS-HD 7=TrueHD */

/* AVIO buffer for spdif muxer output. ffmpeg writes in chunks; 64k covers
 * the largest TrueHD MAT burst (61440 bytes) plus headroom. */
#define HBR_AVIO_BUFSIZE   (128 * 1024)

eIec61937Passthrough::eIec61937Passthrough()
    : m_codec_id(0)
    , m_hbr_mode(false)
    , m_burst_size(0)
    , m_data_type(0)
    , m_spdif_fmt(nullptr)
    , m_spdif_avio(nullptr)
    , m_avio_buffer(nullptr)
    , m_spdif_stream(nullptr)
    , m_hbr_header_written(false)
    , m_hbr_packet_pts(0)
{
}

eIec61937Passthrough::~eIec61937Passthrough()
{
    stop();
}

void eIec61937Passthrough::writeSysfs(const char *path, const char *value)
{
    FILE *f = fopen(path, "w");
    if (!f) {
        eDebug("[eIec61937] sysfs open %s: %m", path);
        return;
    }
    fputs(value, f);
    fclose(f);
}

/* AMlogic 'Audio spdif format' mixer enum flips the IEC958 NON_AUDIO bit. */
void eIec61937Passthrough::setSpdifFormat(unsigned int item)
{
    snd_ctl_t *ctl = nullptr;
    if (snd_ctl_open(&ctl, "hw:0", 0) < 0) {
        eDebug("[eIec61937] snd_ctl_open hw:0: %m");
        return;
    }
    snd_ctl_elem_id_t  *id;  snd_ctl_elem_id_alloca(&id);
    snd_ctl_elem_value_t *val; snd_ctl_elem_value_alloca(&val);

    snd_ctl_elem_id_set_interface(id, SND_CTL_ELEM_IFACE_MIXER);
    snd_ctl_elem_id_set_name(id, "Audio spdif format");
    snd_ctl_elem_value_set_id(val, id);
    snd_ctl_elem_value_set_enumerated(val, 0, item);

    int err = snd_ctl_elem_write(ctl, val);
    if (err < 0)
        eDebug("[eIec61937] set spdif format=%u: %s", item, snd_strerror(err));
    snd_ctl_close(ctl);
}

int eIec61937Passthrough::startStandard(int codec_id)
{
    int digital_codec_val = 0;
    switch (codec_id) {
    case AV_CODEC_ID_AC3:
        m_data_type     = IEC61937_AC3;
        m_burst_size    = 6144;
        digital_codec_val = 2;
        break;
    case AV_CODEC_ID_EAC3:
        m_data_type     = IEC61937_EAC3;
        m_burst_size    = 24576;
        digital_codec_val = 4;
        break;
    case AV_CODEC_ID_AC4:
        /* IEC 61937-13: data_type 0x11; 24576 covers broadcast raw_ac4_frame. */
        m_data_type     = IEC61937_AC4;
        m_burst_size    = 24576;
        digital_codec_val = 4;
        break;
    case AV_CODEC_ID_DTS:
        m_data_type     = IEC61937_DTS_1K;
        m_burst_size    = 2048;
        digital_codec_val = 1;
        break;
    default:
        eDebug("[eIec61937] codec %d not supported for std passthrough", codec_id);
        return -1;
    }

    /* SPDIF reset + AC3 delay applied as real PCM silence on hw:0,0 (PCM
     * mode), drained, then bitstream values written and bitstream session
     * opened. The AVR ignores zero-fill in bitstream mode (no Pa preamble),
     * so the delay would have no effect if applied after the bitstream open.
     * 100ms minimum is needed for the SPDIF FIFO to transition fully. */
    int ac3_delay_ms = eSimpleConfig::getInt("config.av.generalAC3delay", 0);
    if (ac3_delay_ms < 0) ac3_delay_ms = 0;
    if (ac3_delay_ms > 1000) ac3_delay_ms = 1000;
    int reset_ms = 100 + ac3_delay_ms;

    writeSysfs("/sys/class/audiodsp/digital_codec", "0\n");
    setSpdifFormat(0);
    {
        snd_pcm_t *pcm = nullptr;
        if (snd_pcm_open(&pcm, "hw:0,0", SND_PCM_STREAM_PLAYBACK, 0) == 0) {
            snd_pcm_set_params(pcm, SND_PCM_FORMAT_S16_LE,
                               SND_PCM_ACCESS_RW_INTERLEAVED,
                               2, 48000, 1, (unsigned int)reset_ms * 1000);
            snd_pcm_uframes_t total = (snd_pcm_uframes_t)reset_ms * 48000 / 1000;
            static const int16_t silence[4800 * 2] = {0};
            snd_pcm_uframes_t chunk = 4800;
            snd_pcm_uframes_t left = total;
            while (left > 0) {
                snd_pcm_uframes_t n = (left > chunk) ? chunk : left;
                snd_pcm_sframes_t w = snd_pcm_writei(pcm, silence, n);
                if (w <= 0) break;
                left -= (snd_pcm_uframes_t)w;
            }
            snd_pcm_drain(pcm);
            snd_pcm_close(pcm);
        }
    }

    char buf[16];
    snprintf(buf, sizeof(buf), "%d\n", digital_codec_val);
    writeSysfs("/sys/class/audiodsp/digital_codec", buf);
    writeSysfs("/sys/class/audiodsp/digital_raw", "1\n");
    setSpdifFormat((unsigned int)digital_codec_val);

    int port = 0;
    {
        FILE *f = fopen("/sys/class/amhdmitx/amhdmitx0/audio_source", "r");
        if (f) { int v; if (fscanf(f, "%d", &v) == 1 && v >= 0) port = v; fclose(f); }
    }
    char dev[16];
    snprintf(dev, sizeof(dev), "hw:0,%d", port);

    /* eAlsaOutput thread takes over write + drift/anchor loop. */
    if (eAlsaOutput::instance()->startPassthrough(dev) < 0) {
        eDebug("[eIec61937] eAlsaOutput::startPassthrough(%s) failed", dev);
        return -1;
    }

    eDebug("[eIec61937] std start codec=%d burst=%zu digital_codec=%d delay=%dms dev=%s",
           codec_id, m_burst_size, digital_codec_val, ac3_delay_ms, dev);
    return 0;
}

int eIec61937Passthrough::spdif_write_cb(void *opaque, const uint8_t *buf, int buf_size)
{
    eIec61937Passthrough *self = (eIec61937Passthrough *)opaque;
    self->m_hbr_out.insert(self->m_hbr_out.end(), buf, buf + buf_size);
    return buf_size;
}

int eIec61937Passthrough::startHBR(int codec_id)
{
    int digital_codec_val;
    unsigned int spdif_fmt;
    enum AVCodecID stream_codec;
    switch (codec_id) {
    case AV_CODEC_ID_TRUEHD:
        digital_codec_val = 7;
        spdif_fmt         = 7;
        stream_codec      = AV_CODEC_ID_TRUEHD;
        break;
    case AV_CODEC_ID_DTS:
        digital_codec_val = 5;       /* DTS-HD */
        spdif_fmt         = 5;
        stream_codec      = AV_CODEC_ID_DTS;
        break;
    default:
        eDebug("[eIec61937] codec %d not supported for HBR", codec_id);
        return -1;
    }

    /* Reset sequence — same idea as standard mode. */
    writeSysfs("/sys/class/audiodsp/digital_codec", "0\n");
    setSpdifFormat(0);
    {
        snd_pcm_t *pcm = nullptr;
        if (snd_pcm_open(&pcm, "hw:0,0", SND_PCM_STREAM_PLAYBACK, 0) == 0) {
            snd_pcm_set_params(pcm, SND_PCM_FORMAT_S16_LE,
                               SND_PCM_ACCESS_RW_INTERLEAVED,
                               2, 48000, 1, 100000);
            static const int16_t silence[4800 * 2] = {0};
            snd_pcm_writei(pcm, silence, 4800);
            snd_pcm_drain(pcm);
            snd_pcm_close(pcm);
        }
    }
    char buf[16];
    snprintf(buf, sizeof(buf), "%d\n", digital_codec_val);
    writeSysfs("/sys/class/audiodsp/digital_codec", buf);
    writeSysfs("/sys/class/audiodsp/digital_raw", "1\n");
    setSpdifFormat(spdif_fmt);

    /* Open hw:0,N at HBR rate. ALSA on AML maps 192k/8ch S16 to the
     * HBR IEC60958 carrier (24.576 Mbit/s wire rate). */
    int port = 0;
    {
        FILE *f = fopen("/sys/class/amhdmitx/amhdmitx0/audio_source", "r");
        if (f) { int v; if (fscanf(f, "%d", &v) == 1 && v >= 0) port = v; fclose(f); }
    }
    char dev[16];
    snprintf(dev, sizeof(dev), "hw:0,%d", port);
    if (eAlsaOutput::instance()->startPassthrough(dev, 192000, 8) < 0) {
        eDebug("[eIec61937] HBR eAlsaOutput::startPassthrough(%s) failed", dev);
        return -1;
    }

    /* Build libavformat 'spdif' output context. The muxer takes raw
     * TrueHD / DTS-HD AVPackets and emits IEC61937 bytes including MAT
     * wrapping for TrueHD (FFmpeg's spdif_header_truehd handles the
     * 61440/61424 burst and the 3 MAT code sequences). */
    int rc = avformat_alloc_output_context2(&m_spdif_fmt, NULL, "spdif", NULL);
    if (rc < 0 || !m_spdif_fmt) {
        eDebug("[eIec61937] alloc spdif muxer: %d", rc);
        eAlsaOutput::instance()->stop();
        return -1;
    }
    m_spdif_stream = avformat_new_stream(m_spdif_fmt, NULL);
    if (!m_spdif_stream) {
        eDebug("[eIec61937] avformat_new_stream failed");
        avformat_free_context(m_spdif_fmt); m_spdif_fmt = nullptr;
        eAlsaOutput::instance()->stop();
        return -1;
    }
    m_spdif_stream->codecpar->codec_type = AVMEDIA_TYPE_AUDIO;
    m_spdif_stream->codecpar->codec_id   = stream_codec;
    m_spdif_stream->codecpar->sample_rate = 48000;
#if LIBAVUTIL_VERSION_INT >= AV_VERSION_INT(57, 28, 100)
    av_channel_layout_default(&m_spdif_stream->codecpar->ch_layout,
                              stream_codec == AV_CODEC_ID_TRUEHD ? 8 : 6);
#else
    m_spdif_stream->codecpar->channels = (stream_codec == AV_CODEC_ID_TRUEHD ? 8 : 6);
#endif

    /* Custom AVIO — bytes from av_write_frame land in spdif_write_cb. */
    m_avio_buffer = (uint8_t *)av_malloc(HBR_AVIO_BUFSIZE);
    if (!m_avio_buffer) {
        avformat_free_context(m_spdif_fmt); m_spdif_fmt = nullptr;
        eAlsaOutput::instance()->stop();
        return -1;
    }
    m_spdif_avio = avio_alloc_context(m_avio_buffer, HBR_AVIO_BUFSIZE,
                                      1 /* write */, this,
                                      NULL, &eIec61937Passthrough::spdif_write_cb,
                                      NULL);
    if (!m_spdif_avio) {
        av_free(m_avio_buffer); m_avio_buffer = nullptr;
        avformat_free_context(m_spdif_fmt); m_spdif_fmt = nullptr;
        eAlsaOutput::instance()->stop();
        return -1;
    }
    m_spdif_fmt->pb = m_spdif_avio;
    m_spdif_fmt->flags |= AVFMT_FLAG_CUSTOM_IO;

    AVDictionary *opts = NULL;
    /* For DTS-HD: prefer max rate so the muxer picks the largest period
     * that fits, giving us actual DTS-HD passthrough vs falling back to
     * core. 192k matches our wire rate. */
    if (stream_codec == AV_CODEC_ID_DTS)
        av_dict_set(&opts, "dtshd_rate", "192000", 0);
    rc = avformat_write_header(m_spdif_fmt, &opts);
    av_dict_free(&opts);
    if (rc < 0) {
        eDebug("[eIec61937] avformat_write_header: %d", rc);
        freeHBR();
        eAlsaOutput::instance()->stop();
        return -1;
    }
    m_hbr_header_written = true;
    m_hbr_packet_pts = 0;
    m_hbr_out.reserve(HBR_AVIO_BUFSIZE);

    eDebug("[eIec61937] HBR start codec=%d (digital_codec=%d) 192k/8ch",
           codec_id, digital_codec_val);
    return 0;
}

int eIec61937Passthrough::start(int codec_id, int sample_rate, bool hbr)
{
    (void)sample_rate;
    if (m_codec_id) stop();

    m_codec_id = codec_id;
    m_hbr_mode = hbr;

    int rc = m_hbr_mode ? startHBR(codec_id) : startStandard(codec_id);
    if (rc < 0) {
        m_codec_id = 0;
        m_hbr_mode = false;
    }
    return rc;
}

void eIec61937Passthrough::freeHBR()
{
    if (m_spdif_fmt && m_hbr_header_written) {
        av_write_trailer(m_spdif_fmt);
        m_hbr_header_written = false;
    }
    if (m_spdif_avio) {
        /* avio_context_free frees the AVIOContext but NOT the underlying
         * buffer — we free that manually. Per docs the muxer may have
         * reallocated the buffer, so the live pointer is in avio->buffer. */
        uint8_t *live_buf = m_spdif_avio->buffer;
        avio_context_free(&m_spdif_avio);
        if (live_buf) av_free(live_buf);
        m_avio_buffer = nullptr;
    } else if (m_avio_buffer) {
        av_free(m_avio_buffer);
        m_avio_buffer = nullptr;
    }
    if (m_spdif_fmt) {
        avformat_free_context(m_spdif_fmt);
        m_spdif_fmt = nullptr;
    }
    m_spdif_stream = nullptr;
    m_hbr_out.clear();
}

/* Sysfs reset is owned by AVSwitch.py / tsparser. */
void eIec61937Passthrough::stop()
{
    if (m_hbr_mode) freeHBR();
    eAlsaOutput::instance()->stop();
    eAlsaOutput::instance()->switchDevice("dreamhdmi");
    m_codec_id = 0;
    m_hbr_mode = false;
}

int eIec61937Passthrough::pushFrameStandard(const uint8_t *frame, size_t len, int64_t pts_90k)
{
    if (len + 8 > m_burst_size) {
        eDebug("[eIec61937] frame %zu > burst %zu, drop", len, m_burst_size);
        return -1;
    }

    uint8_t buf[32768];
    if (m_burst_size > sizeof(buf)) {
        eDebug("[eIec61937] burst %zu > buf %zu", m_burst_size, sizeof(buf));
        return -1;
    }
    memset(buf, 0, m_burst_size);

    /* AC3 Pc bits 8-10 = bsmod from frame[5] - AVRs validate this. */
    uint16_t pc = m_data_type;
    if (m_codec_id == AV_CODEC_ID_AC3 && len >= 6)
        pc |= (uint16_t)(frame[5] & 0x07) << 8;
    buf[0] = 0x72; buf[1] = 0xF8;                 /* Pa = 0xF872 */
    buf[2] = 0x1F; buf[3] = 0x4E;                 /* Pb = 0x4E1F */
    buf[4] = (uint8_t)(pc & 0xFF);
    buf[5] = (uint8_t)((pc >> 8) & 0xFF);
    uint32_t bits = (uint32_t)(len * 8);          /* Pd = size in BITS */
    buf[6] = (uint8_t)(bits & 0xFF);
    buf[7] = (uint8_t)((bits >> 8) & 0xFF);

    /* Byte-swap payload (SPDIF byte order) */
    size_t i;
    for (i = 0; i + 1 < len; i += 2) {
        buf[8 + i]     = frame[i + 1];
        buf[8 + i + 1] = frame[i];
    }
    if (len & 1)
        buf[8 + len - 1] = frame[len - 1];

    return eAlsaOutput::instance()->pushData(buf, (int)m_burst_size, pts_90k);
}

int eIec61937Passthrough::drainHBROut(int64_t pts_90k)
{
    if (m_hbr_out.empty()) return 0;
    /* HBR ALSA frame = 16 bytes (8ch * S16). Push whole frames; keep <16 byte tail. */
    size_t bytes = m_hbr_out.size();
    size_t frames = bytes / 16;
    if (frames == 0) return 0;
    size_t aligned_bytes = frames * 16;

    int rc = eAlsaOutput::instance()->pushData(m_hbr_out.data(), (int)aligned_bytes, pts_90k);
    if (aligned_bytes < bytes)
        m_hbr_out.erase(m_hbr_out.begin(), m_hbr_out.begin() + aligned_bytes);
    else
        m_hbr_out.clear();
    return rc;
}

int eIec61937Passthrough::pushFrameHBR(const uint8_t *frame, size_t len, int64_t pts_90k)
{
    if (!m_spdif_fmt) return -1;

    AVPacket *pkt = av_packet_alloc();
    if (!pkt) return -1;
    /* AVPacket takes a copy via av_packet_make_writable; simpler to use
     * av_new_packet so the muxer can write/realloc without touching us. */
    if (av_new_packet(pkt, (int)len) < 0) {
        av_packet_free(&pkt);
        return -1;
    }
    memcpy(pkt->data, frame, len);
    pkt->stream_index = m_spdif_stream->index;
    /* PTS in stream timebase. spdif muxer mostly uses size-based timing,
     * but feed something monotonic so it doesn't complain. */
    pkt->pts = pts_90k;
    pkt->dts = pts_90k;

    int rc = av_write_frame(m_spdif_fmt, pkt);
    av_packet_free(&pkt);
    if (rc < 0) {
        char errbuf[128];
        av_strerror(rc, errbuf, sizeof(errbuf));
        eDebug("[eIec61937] HBR av_write_frame: %s", errbuf);
        return -1;
    }
    /* Flush so AVIO write_cb is called for any buffered output. */
    avio_flush(m_spdif_avio);
    return drainHBROut(pts_90k);
}

int eIec61937Passthrough::pushFrame(const uint8_t *frame, size_t len, int64_t pts_90k)
{
    if (!frame || len == 0) return -1;
    return m_hbr_mode ? pushFrameHBR(frame, len, pts_90k)
                      : pushFrameStandard(frame, len, pts_90k);
}
