#ifndef __LIB_DVB_AUDIOMANAGER_H_
#define __LIB_DVB_AUDIOMANAGER_H_

#include <string>
#include <vector>
#include <set>
#include <libavcodec/avcodec.h>

/* HDMI sink audio capability detection via /sys/class/amhdmitx/aud_cap. */
class eAudioManager
{
public:
    static eAudioManager *getInstance();

    /* True when sink advertises this codec; PCM always true. */
    bool hasFormat(enum AVCodecID codec_id);

    /* True for codecs that require HDMI HBR (192k/8ch): TrueHD always,
     * DTS-HD when the sink advertises it. */
    bool needsHBR(enum AVCodecID codec_id);

    /* Re-read aud_cap (HDMI hotplug). */
    void reload();

    /* For UI/debug. */
    const std::set<int> &availableTags() const { return m_tags; }

private:
    eAudioManager();
    void load();

    /* CodingType IDs as exposed in aud_cap (CEA-861 audio_format_code). */
    enum {
        TAG_PCM    = 1,
        TAG_AC3    = 2,
        TAG_MP1    = 3,
        TAG_MP3    = 4,
        TAG_MP2    = 5,
        TAG_AACLC  = 6,
        TAG_DTS    = 7,
        TAG_ATRAC  = 8,
        TAG_ONEBIT = 9,
        TAG_EAC3   = 10,
        TAG_DTSHD  = 11,
        TAG_TRUEHD = 12,
        TAG_DST    = 13,
        TAG_WMAPRO = 14,
        TAG_AC4    = 15,
    };

    std::set<int> m_tags;
    /* Subset of m_tags whose aud_cap line carries 192 kHz (HBR-capable). */
    std::set<int> m_hbr_tags;
    static eAudioManager *s_instance;
};

#endif /* __LIB_DVB_AUDIOMANAGER_H_ */
