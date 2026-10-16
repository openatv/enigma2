#include <lib/dvb/audiomanager.h>
#include <lib/base/eerror.h>

#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <fstream>
#include <sstream>

eAudioManager *eAudioManager::s_instance = nullptr;

eAudioManager *eAudioManager::getInstance()
{
    if (!s_instance) s_instance = new eAudioManager();
    return s_instance;
}

eAudioManager::eAudioManager()
{
    load();
}

void eAudioManager::reload()
{
    m_tags.clear();
    load();
}

/* aud_cap: one CEA-861 CodingType per line, comma-separated
 * fields (codec name, channels, sample rates, bit depth/bitrate). */
void eAudioManager::load()
{
    std::ifstream f("/sys/class/amhdmitx/amhdmitx0/aud_cap");
    if (!f.is_open()) {
        eDebug("[eAudioManager] aud_cap unreadable — assume PCM-only sink");
        m_tags.insert(TAG_PCM);
        return;
    }
    std::string line;
    while (std::getline(f, line)) {
        /* First non-empty token = codec name. Skip header. */
        size_t i = 0;
        while (i < line.size() && isspace((unsigned char)line[i])) ++i;
        if (i >= line.size()) continue;
        size_t j = i;
        while (j < line.size() && line[j] != ',') ++j;
        std::string name = line.substr(i, j - i);
        /* trim trailing space */
        while (!name.empty() && isspace((unsigned char)name.back())) name.pop_back();

        int tag = -1;
        if      (name == "PCM")            tag = TAG_PCM;
        else if (name == "AC-3" || name == "AC3") tag = TAG_AC3;
        else if (name == "MPEG-1" || name == "MP1") tag = TAG_MP1;
        else if (name == "MP3")            tag = TAG_MP3;
        else if (name == "MPEG2" || name == "MP2")  tag = TAG_MP2;
        else if (name == "AAC-LC" || name == "AAC") tag = TAG_AACLC;
        else if (name == "DTS")            tag = TAG_DTS;
        else if (name == "ATRAC")          tag = TAG_ATRAC;
        else if (name == "OneBitAudio")    tag = TAG_ONEBIT;
        else if (name == "Dobly_Digital+" || name == "Dolby_Digital+"
                 || name == "EAC3" || name == "E-AC-3") tag = TAG_EAC3;
        else if (name == "DTS-HD")         tag = TAG_DTSHD;
        else if (name == "TrueHD" || name == "MAT") tag = TAG_TRUEHD;
        else if (name == "DST")            tag = TAG_DST;
        else if (name == "WMA-Pro" || name == "WMAPro") tag = TAG_WMAPRO;
        else if (name == "AC-4" || name == "AC4") tag = TAG_AC4;
        if (tag > 0) {
            m_tags.insert(tag);
            /* HBR carrier (192k/8ch) requires sink to advertise 192 kHz. */
            if (line.find("192") != std::string::npos)
                m_hbr_tags.insert(tag);
        }
    }
    if (m_tags.empty()) m_tags.insert(TAG_PCM);
    std::stringstream ss, ss_hbr;
    for (int t : m_tags) ss << t << ' ';
    for (int t : m_hbr_tags) ss_hbr << t << ' ';
    eDebug("[eAudioManager] HDMI codec tags: %s | HBR-capable: %s",
           ss.str().c_str(),
           m_hbr_tags.empty() ? "(none)" : ss_hbr.str().c_str());
}

bool eAudioManager::hasFormat(enum AVCodecID codec_id)
{
    if (codec_id == AV_CODEC_ID_NONE) return true;
    int tag = -1;
    switch (codec_id) {
        case AV_CODEC_ID_AC3:    tag = TAG_AC3;    break;
        case AV_CODEC_ID_EAC3:   tag = TAG_EAC3;   break;
        case AV_CODEC_ID_DTS:    tag = TAG_DTS;    break;
        case AV_CODEC_ID_MP1:    tag = TAG_MP1;    break;
        case AV_CODEC_ID_MP2:    tag = TAG_MP2;    break;
        case AV_CODEC_ID_MP3:    tag = TAG_MP3;    break;
        case AV_CODEC_ID_AAC:    tag = TAG_AACLC;  break;
        case AV_CODEC_ID_TRUEHD: tag = TAG_TRUEHD; break;
        case AV_CODEC_ID_AC4:    tag = TAG_AC4;    break;
        default:                 return true;
    }
    return m_tags.count(tag) > 0;
}

bool eAudioManager::needsHBR(enum AVCodecID codec_id)
{
    /* HBR-capable iff sink lists the codec AND advertises 192 kHz. */
    if (codec_id == AV_CODEC_ID_TRUEHD)
        return m_hbr_tags.count(TAG_TRUEHD) > 0;
    if (codec_id == AV_CODEC_ID_DTS)
        return m_hbr_tags.count(TAG_DTSHD) > 0;
    return false;
}
