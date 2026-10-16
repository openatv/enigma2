#ifndef __LIB_DVB_IEC61937_H_
#define __LIB_DVB_IEC61937_H_

#include <stdint.h>
#include <stddef.h>
#include <vector>
#include <alsa/asoundlib.h>

struct AVFormatContext;
struct AVIOContext;
struct AVStream;

/* IEC61937 bitstream passthrough to HDMI/SPDIF via ALSA. Standard mode
 * (48k/2ch) for AC3/EAC3/DTS; HBR mode (192k/8ch via libavformat spdif
 * muxer) for TrueHD/DTS-HD MA. AVR does the decode. */
class eIec61937Passthrough
{
public:
    eIec61937Passthrough();
    ~eIec61937Passthrough();

    /* codec_id is an FFmpeg AV_CODEC_ID_*: AC3, EAC3, DTS, TRUEHD.
     * hbr=true upgrades DTS to DTS-HD MA (192k/8ch); TRUEHD is always HBR. */
    int  start(int codec_id, int sample_rate, bool hbr = false);
    void stop();

    /* Push one raw codec ES frame. Returns 0 on success, <0 on error. */
    int  pushFrame(const uint8_t *frame, size_t len, int64_t pts_90k);

    bool active() const { return m_codec_id != 0; }
    bool hbr()    const { return m_hbr_mode; }

private:
    int        m_codec_id;
    bool       m_hbr_mode;

    /* IEC61937 burst spacing in bytes for this codec (zero-padded). */
    size_t     m_burst_size;
    uint16_t   m_data_type;   /* IEC61937 Pc value */

    /* HBR / libavformat-spdif muxer state */
    AVFormatContext *m_spdif_fmt;
    AVIOContext     *m_spdif_avio;
    uint8_t         *m_avio_buffer;       /* owned by AVIOContext, freed via avio_context_free */
    AVStream        *m_spdif_stream;
    std::vector<uint8_t> m_hbr_out;       /* bytes accumulated by spdif_write_cb */
    bool             m_hbr_header_written;
    int64_t          m_hbr_packet_pts;    /* re-used per av_write_frame */

    int  startStandard(int codec_id);
    int  startHBR(int codec_id);
    int  pushFrameStandard(const uint8_t *frame, size_t len, int64_t pts_90k);
    int  pushFrameHBR(const uint8_t *frame, size_t len, int64_t pts_90k);
    void freeHBR();
    int  drainHBROut(int64_t pts_90k);

    void writeSysfs(const char *path, const char *value);
    /* Set the AMlogic ALSA mixer 'Audio spdif format' enum:
     * 0=2CH PCM, 1=DTS RAW, 2=Dolby Digital (AC3), 3=DTS,
     * 4=DD+ (EAC3), 5=DTS-HD, 6=Multi-channel LPCM, 7=TrueHD. */
    void setSpdifFormat(unsigned int item);

    /* Custom AVIOContext sink — collects muxer output into m_hbr_out. */
    static int spdif_write_cb(void *opaque, const uint8_t *buf, int buf_size);
};

#endif /* __LIB_DVB_IEC61937_H_ */
