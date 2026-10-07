
#if defined(__CYGWIN__) || defined(CUSTUM)
#include "../base/eerror.h"
#include "../base/cfile.h"
#include "tsparser.h"

#include <pthread.h>
#include <sched.h>
#else
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/base/esimpleconfig.h>
#include <lib/dvb/tsparser.h>
#include <lib/dvb/decoder.h>     /* full eAudioDecoder definition */
#include <lib/dvb/audiomanager.h>
#include <lib/base/cfile.h>
#endif

#include <poll.h>
#include <fcntl.h>
#include <sys/ioctl.h>

static bool FastMpegCheck(const uint8_t *p)
{
    if (p[0] != 0xFF)			// 11bit frame sync
        return false;
    if ((p[1] & 0xE0) != 0xE0)
        return false;
    if ((p[1] & 0x18) == 0x08)	// version ID - 01 reserved
        return false;
    if (!(p[1] & 0x06))			// layer description - 00 reserved
        return false;
    if ((p[2] & 0xF0) == 0xF0)	// bit rate index - 1111 reserved
        return false;
    if ((p[2] & 0x0C) == 0x0C)	// sampling rate index - 11 reserved
        return false;
    return true;
}


static bool MpegCheck(const uint8_t *p, unsigned int size,
                      unsigned int &frameSize, unsigned int &channels,
                      unsigned int &samplingRate)
{
    frameSize = size;
    if (size < 4)
        return true;

    int cmode = (p[3] >> 6) & 0x03;
    int mpeg2 = !(p[1] & 0x08) && (p[1] & 0x10);
    int mpeg25 = !(p[1] & 0x08) && !(p[1] & 0x10);
    int layer = 4 - ((p[1] >> 1) & 0x03);
    int padding = (p[2] >> 1) & 0x01;

    // channel mode = [ stereo, joint stereo, dual channel, mono]
    channels = cmode == 0x03 ? 1 : 2;

    samplingRate = MpegSampleRateTable[(p[2] >> 2) & 0x03];
    if (!samplingRate)
        return false;

    samplingRate >>= mpeg2;		// MPEG 2 half rate
    samplingRate >>= mpeg25;	// MPEG 2.5 quarter rate

    int bit_rate =
        BitRateTable[mpeg2 | mpeg25][layer - 1][(p[2] >> 4) & 0x0F];
    if (!bit_rate)
        return false;

    switch (layer)
    {
    case 1:
        frameSize = (12000 * bit_rate) / samplingRate;
        frameSize = (frameSize + padding) * 4;
        break;
    case 2:
    case 3:
    default:
        frameSize = (144000 * bit_rate) / samplingRate;
        frameSize = frameSize + padding;
        break;
    }

    if (frameSize + 4 > size)
    {
        frameSize = size;
        channels = 0;
        samplingRate = 0;
        return true;
    }

    if (FastMpegCheck(p + frameSize))
        return true;

    return false;
}

static bool fastTrueHdHint(const uint8_t *p, unsigned int size);

static bool FastAc3Check(const uint8_t *p)
{

    if (p[0] != 0x0B)			// 16bit sync
        return false;
    if (p[1] != 0x77)
        return false;

    return true;
}


static bool Ac3Check(const uint8_t *p, unsigned int size,
                     unsigned int &frameSize, unsigned int &channels,
                     unsigned int &samplingRate)
{

    frameSize = size;
    if (size < 5)
        return true;

    int acmod;
    bool lfe;
    int fscod = (p[4] & 0xC0) >> 6;
    samplingRate = Ac3SampleRateTable[fscod];



    if (p[5] > (10 << 3))		// E-AC-3
    {
        if (fscod == 0x03)
        {
            int fscod2 = (p[4] & 0x30) >> 4;
            if (fscod2 == 0x03)
                return false;		// invalid fscod & fscod2

            samplingRate = Ac3SampleRateTable[fscod2] / 2;
        }

        acmod = (p[4] & 0x0E) >> 1;	// number of channels, LFE excluded
        lfe = p[4] & 0x01;

        frameSize = ((p[2] & 0x07) << 8) + p[3] + 1;
        frameSize *= 2;
    }
    else						// AC-3
    {
        if (fscod == 0x03)		// invalid sample rate
            return false;

        int frmsizcod = p[4] & 0x3F;
        if (frmsizcod > 37)		// invalid frpame size
            return false;

        acmod = p[6] >> 5;		// number of channels, LFE excluded

        int lfe_bptr = 51;		// position of LFE bit in header for 2.0
        if ((acmod & 0x01) && (acmod != 0x01))
            lfe_bptr += 2;		// skip center mix level
        if (acmod & 0x04)
            lfe_bptr += 2;		// skip surround mix level
        if (acmod == 0x02)
            lfe_bptr += 2;		// skip surround mode
        lfe = (p[lfe_bptr / 8] & (1 << (7 - (lfe_bptr % 8))));

        // invalid is checked above
        frameSize = Ac3FrameSizeTable[frmsizcod][fscod] * 2;
    }

    channels =
        acmod == 0x00 ? 2 : 	// Ch1, Ch2
        acmod == 0x01 ? 1 : 	// C
        acmod == 0x02 ? 2 : 	// L, R
        acmod == 0x03 ? 3 : 	// L, C, R
        acmod == 0x04 ? 3 : 	// L, R, S
        acmod == 0x05 ? 4 : 	// L, C, R, S
        acmod == 0x06 ? 4 : 	// L, R, RL, RR
        acmod == 0x07 ? 5 : 0;	// L, C, R, RL, RR

    if (lfe)
        channels++;

    if (frameSize + 5 > size)
    {
        frameSize = size;
        channels = 0;
        samplingRate = 0;
        return true;
    }

    if (FastAc3Check(p + frameSize))
        return true;

    return false;
}

static bool FastLatmCheck(const uint8_t *p)
{
    if (p[0] != 0x56)			// 11bit sync
        return false;
    if ((p[1] & 0xE0) != 0xE0)
        return false;
    return true;
}

static bool LatmCheck(const uint8_t *p, unsigned int size,
                      unsigned int &frameSize, unsigned int &channels,
                      unsigned int &samplingRate)
{
    frameSize = size;
    if (size < 3)
        return true;

    // to do: determine channels
    channels = 2;

    // to do: determine sampling rate
    samplingRate = 48000;

    // 13 bit frame size without header
    frameSize = ((p[1] & 0x1F) << 8) + p[2];
    frameSize += 3;

    if (frameSize + 2 > size)
    {
        frameSize = size;
        channels = 0;
        samplingRate = 0;
        return true;
    }

    if (FastLatmCheck(p + frameSize))
        return true;

    return false;
}


static bool FastAdtsCheck(const uint8_t *p)
{
    if (p[0] != 0xFF)			// 12bit sync
        return false;
    if ((p[1] & 0xF6) != 0xF0)	// sync + layer must be 0
        return false;
    if ((p[2] & 0x3C) == 0x3C)	// sampling frequency index != 15
        return false;
    return true;
}

static bool AdtsCheck(const uint8_t *p, unsigned int size,
                      unsigned int &frameSize, unsigned int &channels,
                      unsigned int &samplingRate)
{
    frameSize = size;
    if (size < 6)
        return true;

    samplingRate = Mpeg4SampleRateTable[(p[2] >> 2) & 0x0F];

    frameSize = (p[3] & 0x03) << 11;
    frameSize |= (p[4] & 0xFF) << 3;
    frameSize |= (p[5] & 0xE0) >> 5;

    int cConf = (p[2] & 0x01) << 7;
    cConf |= (p[3] & 0xC0) >> 6;
    channels =
        cConf == 0x00 ? 0 : // defined in AOT specific config
        cConf == 0x01 ? 1 : // C
        cConf == 0x02 ? 2 : // L, R
        cConf == 0x03 ? 3 : // C, L, R
        cConf == 0x04 ? 4 : // C, L, R, RC
        cConf == 0x05 ? 5 : // C, L, R, RL, RR
        cConf == 0x06 ? 6 : // C, L, R, RL, RR, LFE
        cConf == 0x07 ? 8 : // C, L, R, SL, SR, RL, RR, LFE
        0;

    if (!samplingRate || !channels)
        return false;

    if (frameSize + 3 > size)
    {
        frameSize = size;
        channels = 0;
        samplingRate = 0;
        return true;
    }

    if (FastAdtsCheck(p + frameSize))
        return true;

    return false;
}

///
///	Fast check for DTS Audio Data Transport Stream.
///
///	0x7FFE8001....  DTS audio
///
static bool FastDtsCheck(const uint8_t *p)
{
    if (p[0] != 0x7F)			// 32bit sync
        return false;
    if (p[1] != 0xFE)
        return false;
    if (p[2] != 0x80)
        return false;
    if (p[3] != 0x01)
        return false;
    return true;
}

static bool DtsCheck(const uint8_t *p, unsigned int size,
                     unsigned int &frameSize, unsigned int &channels,
                     unsigned int &samplingRate)
{
    frameSize = size;
    if (size < 8)
        return true;

    frameSize = ((p[5] & 0x03) << 12) + (p[6] << 4) + ((p[7] & 0xF0) >> 4);
    frameSize++;

    samplingRate = DtsSampleRateTable[(p[8] & 0x3C) >> 2];

    int amode = ((p[7] & 0x0F) << 2) + ((p[8] & 0xC0) >> 6);
    channels =
        amode == 0x00 ? 1 : 	// mono
        amode == 0x02 ? 2 : 	// L, R
        amode == 0x03 ? 2 : 	// (L + R), (L - R)
        amode == 0x04 ? 2 : 	// LT, RT
        amode == 0x05 ? 3 : 	// L, R, C
        amode == 0x06 ? 3 : 	// L, R, S
        amode == 0x08 ? 4 : 	// L, R, RL, RR
        amode == 0x09 ? 5 : 0;	// L, C, R, RL, RR

    if (!samplingRate || !channels)
        return false;

    if (p[10] & 0x06)
        channels++;

    if (frameSize + 4 > size)
    {
        frameSize = size;
        channels = 0;
        samplingRate = 0;
        return true;
    }

    if (FastDtsCheck(p + frameSize))
        return true;

    return false;
}

/* AC-4 (ETSI TS 103 190) raw_frame sync: 0xAC40 (no CRC) or 0xAC41 (+CRC16). */
static bool FastAc4Check(const uint8_t *p)
{
    if (p[0] != 0xAC)
        return false;
    if (p[1] != 0x40 && p[1] != 0x41)
        return false;
    return true;
}

static bool Ac4Check(const uint8_t *p, unsigned int size,
                     unsigned int &frameSize, unsigned int &channels,
                     unsigned int &samplingRate)
{
    frameSize = size;
    if (size < 7)
        return true;

    /* sync(2)+size(2), ext-size(3) if size==0xFFFF, CRC(2) only for 0xAC41. */
    unsigned int hdr = 4;
    unsigned int payload = (p[2] << 8) | p[3];
    if (payload == 0xFFFF) {
        if (size < 8) { frameSize = size; channels = 0; samplingRate = 0; return true; }
        payload = ((unsigned int)p[4] << 16) | ((unsigned int)p[5] << 8) | p[6];
        hdr = 7;
    }
    frameSize = hdr + payload + (p[1] == 0x41 ? 2u : 0u);

    /* Need 2 bytes past frame for next-sync verification. */
    if (frameSize + 2 > size) {
        frameSize = size;
        channels = 0;
        samplingRate = 0;
        return true;
    }

    /* Defaults keep dispatch happy; decoder reports real values post-decode. */
    channels = 2;
    samplingRate = 48000;

    if (FastAc4Check(p + frameSize))
        return true;

    return false;
}

static enum AVCodecID FastCheck(const uint8_t *p)
{
    return 	FastMpegCheck(p)  ? AV_CODEC_ID_MP2      :
            FastAc3Check (p)  ? AV_CODEC_ID_AC3      :
            FastAdtsCheck(p)  ? AV_CODEC_ID_AAC      :
            FastLatmCheck(p)  ? AV_CODEC_ID_AAC_LATM :
            FastDtsCheck (p)  ? AV_CODEC_ID_DTS      :
            FastAc4Check (p)  ? AV_CODEC_ID_AC4      :
            AV_CODEC_ID_NONE;
}

static const char* CodecStr(enum AVCodecID codec)
{
    return  (codec == AV_CODEC_ID_MP2)      ? "MPEG"     :
            (codec == AV_CODEC_ID_AC3)      ? "AC3"      :
            (codec == AV_CODEC_ID_EAC3)     ? "E-AC3"    :
            (codec == AV_CODEC_ID_TRUEHD)   ? "TrueHD"   :
            (codec == AV_CODEC_ID_AAC)      ? "AAC"      :
            (codec == AV_CODEC_ID_AAC_LATM) ? "AAC-LATM" :
            (codec == AV_CODEC_ID_DTS)      ? "DTS"      :
            (codec == AV_CODEC_ID_AC4)      ? "AC4"      : "unknown";
}

void eTsParser::parse(const uint8_t * data, int size,  int is_start)
{
    const uint8_t *p;
    const uint8_t *q;

    if (is_start)  			// start of pes packet
    {
        if (m_pes.Index && m_pes.Skip)
        {
            // copy remaining bytes down
            m_pes.Index -= m_pes.Skip;
            memmove(m_pes.Buffer, m_pes.Buffer + m_pes.Skip, m_pes.Index);
            m_pes.Skip = 0;
        }
        m_pes.State = PES_SYNC;
        m_pes.HeaderIndex = 0;
        m_pes.PTS = AV_NOPTS_VALUE;	// reset if not yet used
        m_pes.DTS = AV_NOPTS_VALUE;
    }
    // cleanup, if too much cruft
    if (m_pes.Skip > PES_MAX_PAYLOAD / 2)
    {
        // copy remaining bytes down
        m_pes.Index -= m_pes.Skip;
        memmove(m_pes.Buffer, m_pes.Buffer + m_pes.Skip, m_pes.Index);
        m_pes.Skip = 0;
    }

    p = data;
    do
    {
        int n;

        switch (m_pes.State)
        {
        case PES_SKIP:		// skip this packet
            return;

        case PES_START:		// at start of pes packet payload
        case PES_INIT:		// find start of audio packet
            n = m_pes.Size - m_pes.Index;
            if (n > size)
                n = size;

            memcpy(m_pes.Buffer + m_pes.Index, p, n);
            m_pes.Index += n;
            p += n;
            size -= n;


            q = m_pes.Buffer + m_pes.Skip;
            n = m_pes.Index - m_pes.Skip;

            while ((n >= 5) && (!m_stop))
            {
                enum AVCodecID codec_id = AV_CODEC_ID_NONE;
                unsigned int channels = 0;
                unsigned int frameSize = 0;
                unsigned int samplingRate = 0;


                switch (FastCheck(q))
                {
                case AV_CODEC_ID_MP2:
                    if (MpegCheck(q, n, frameSize, channels, samplingRate))
                        codec_id = AV_CODEC_ID_MP2;
                    break;

                case AV_CODEC_ID_AC3:
                    if (Ac3Check(q, n, frameSize, channels, samplingRate))
                    {
                        codec_id = AV_CODEC_ID_AC3;
                        if (n > 5 && q[5] > (10 << 3))
                            codec_id = AV_CODEC_ID_EAC3;

                    }
                    break;

                case AV_CODEC_ID_AAC:
                    if (AdtsCheck(q, n, frameSize, channels, samplingRate))
                        codec_id = AV_CODEC_ID_AAC;
                    break;

                case AV_CODEC_ID_AAC_LATM:
                    if (LatmCheck(q, n, frameSize, channels, samplingRate))
                        codec_id = AV_CODEC_ID_AAC_LATM;
                    break;

                case AV_CODEC_ID_DTS:
                    if (DtsCheck(q, n, frameSize, channels, samplingRate))
                        codec_id = AV_CODEC_ID_DTS;
                    break;

                case AV_CODEC_ID_AC4:
                    if (Ac4Check(q, n, frameSize, channels, samplingRate))
                        codec_id = AV_CODEC_ID_AC4;
                    break;
                }

                /* TrueHD fallback. The MLP parser would corrupt its own
                 * state if fed sliding 1-byte windows of unrelated bytes,
                 * which would in turn desync AC3/MP2 detection on the next
                 * iteration. So gate the parse call on a cheap byte-scan
                 * for the major-sync magic — only spend cycles in the
                 * parser when there's a real chance the window is TrueHD.
                 * On a failed parse, drop the parser so the next attempt
                 * starts from a clean slate. */
                if (codec_id == AV_CODEC_ID_NONE && n >= 64 && fastTrueHdHint(q, n)) {
                    if (trueHdCheck(q, n, frameSize, channels, samplingRate))
                        codec_id = AV_CODEC_ID_TRUEHD;
                    else
                        freeTrueHdParser();
                }

                if(frameSize == n &&
                        channels == 0 &&
                        samplingRate == 0)// need more bytes
                    break;


                if (frameSize > 0 &&  frameSize != n && channels != 0 && samplingRate != 0 && codec_id != AV_CODEC_ID_NONE)
                {
                    /* Route via /sys/class/audiodsp/digital_raw - Python AVSwitch
                     * writes it live on menu toggle. Cache on parseInt failure.
                     *
                     * Per-codec override from Audio Settings (when set by user):
                     *   config.av.transcodeac3plus  (EAC3)
                     *   config.av.dtshd             (DTS, also covers DTS-HD core)
                     * Values: "passthrough" forces bitstream regardless of global
                     *         "downmix"     forces PCM-decode regardless of global
                     *         empty/other   keeps the global toggle. */
                    bool wantPassthrough = false;
                    if (codec_id == AV_CODEC_ID_AC3
                     || codec_id == AV_CODEC_ID_EAC3
                     || codec_id == AV_CODEC_ID_DTS
                     || codec_id == AV_CODEC_ID_TRUEHD
                     || codec_id == AV_CODEC_ID_AC4) {
                        static bool s_cached_wp = false;
                        int dgraw = -1;
                        CFile::parseInt(&dgraw, "/sys/class/audiodsp/digital_raw");
                        if (dgraw >= 0)
                            s_cached_wp = (dgraw != 0);
                        wantPassthrough = s_cached_wp;

                        std::string ov;
                        if (codec_id == AV_CODEC_ID_EAC3)
                            ov = eSimpleConfig::getString("config.av.transcodeac3plus", "");
                        else if (codec_id == AV_CODEC_ID_DTS)
                            ov = eSimpleConfig::getString("config.av.dtshd", "");
                        else if (codec_id == AV_CODEC_ID_TRUEHD)
                            ov = eSimpleConfig::getString("config.av.truehd", "");
                        else if (codec_id == AV_CODEC_ID_AC4)
                            ov = eSimpleConfig::getString("config.av.ac4", "");
                        if      (ov == "passthrough") wantPassthrough = true;
                        else if (ov == "downmix")     wantPassthrough = false;
                        else if (ov == "hdmi_best")   wantPassthrough = true;  /* let sink-cap below decide */
                        else if (ov == "force_ac3")   wantPassthrough = false; /* EAC3 → PCM → re-encode to AC3 */

                        /* sink-capability gate: PCM fallback if AVR can't decode */
                        if (wantPassthrough
                            && !eAudioManager::getInstance()->hasFormat((enum AVCodecID)codec_id))
                            wantPassthrough = false;
                    }

                    /* Force re-init when user toggles downmix while a stream
                     * runs with unchanged codec_id. */
                    bool route_mismatch =
                        (wantPassthrough && !m_ePassthrough) ||
                        (!wantPassthrough && m_ePassthrough);
                    if (route_mismatch && m_pes.codec_id == codec_id) {
                        eDebug("[eTsParser] downmix setting toggled, restart route");
                        m_pes.codec_id = AV_CODEC_ID_NONE;
                    }

                    if (m_pes.codec_id != codec_id)
                    {
                        eDebug("[eTsParser] codec (%s) (%dHz *%d) size(%d) frame(0x%02X%02X%02X%02X%02X%02X%02X%02X) -> %s",
                               CodecStr(codec_id), samplingRate, channels, frameSize,
                               q[0], q[1], q[2], q[3], q[4], q[5], q[6], q[7],
                               wantPassthrough ? "PASSTHROUGH" : "PCM-DECODE");

                        if(m_eAudioDecoder) { delete m_eAudioDecoder; m_eAudioDecoder = NULL; }
                        if(m_ePassthrough)  { delete m_ePassthrough;  m_ePassthrough  = NULL; }

                        /* Real route change to PCM-DECODE: reset codec + spdif
                         * format mixer to 0 so HDMI link is PCM-consistent
                         * (iec61937 destructor leaves them alone). */
                        if (!wantPassthrough) {
                            FILE *f = fopen("/sys/class/audiodsp/digital_codec", "w");
                            if (f) { fputs("0\n", f); fclose(f); }
                            snd_ctl_t *ctl = nullptr;
                            if (snd_ctl_open(&ctl, "hw:0", 0) == 0) {
                                snd_ctl_elem_id_t  *id;  snd_ctl_elem_id_alloca(&id);
                                snd_ctl_elem_value_t *val; snd_ctl_elem_value_alloca(&val);
                                snd_ctl_elem_id_set_interface(id, SND_CTL_ELEM_IFACE_MIXER);
                                snd_ctl_elem_id_set_name(id, "Audio spdif format");
                                snd_ctl_elem_value_set_id(val, id);
                                snd_ctl_elem_value_set_enumerated(val, 0, 0);
                                snd_ctl_elem_write(ctl, val);
                                snd_ctl_close(ctl);
                            }
                        }

                        if (wantPassthrough) {
                            /* HBR upgrade: TrueHD is HBR-only, DTS upgrades
                             * to DTS-HD MA when the sink advertises DTS-HD. */
                            bool wantHBR = false;
                            if (codec_id == AV_CODEC_ID_TRUEHD)
                                wantHBR = true;
                            else if (codec_id == AV_CODEC_ID_DTS)
                                wantHBR = eAudioManager::getInstance()->needsHBR(AV_CODEC_ID_DTS);
                            m_ePassthrough = new eIec61937Passthrough();
                            if (m_ePassthrough->start(codec_id, samplingRate, wantHBR) < 0) {
                                /* HBR failed → retry with standard mode (DTS core fallback). */
                                if (wantHBR && codec_id == AV_CODEC_ID_DTS) {
                                    eDebug("[eTsParser] HBR start failed, fall back to DTS-core passthrough");
                                    if (m_ePassthrough->start(codec_id, samplingRate, false) < 0) {
                                        delete m_ePassthrough; m_ePassthrough = NULL;
                                        wantPassthrough = false;
                                    }
                                } else {
                                    delete m_ePassthrough; m_ePassthrough = NULL;
                                    wantPassthrough = false;  /* fall back to PCM */
                                }
                            }
                        }
                        if (!wantPassthrough) {
                            m_eAudioDecoder = new eAudioDecoder();
                            /* AAC / EAC3 -> AC3 transcode for older AVRs that
                             * prefer AC3 bitstream over LPCM on S/PDIF.
                             * Only kicks in when sink advertises AC3. */
                            const bool aac_force = (codec_id == AV_CODEC_ID_AAC || codec_id == AV_CODEC_ID_AAC_LATM)
                                && eSimpleConfig::getString("config.av.transcodeaac", "") == "force_ac3";
                            const bool eac3_force = (codec_id == AV_CODEC_ID_EAC3)
                                && eSimpleConfig::getString("config.av.transcodeac3plus", "") == "force_ac3";
                            if ((aac_force || eac3_force)
                                && eAudioManager::getInstance()->hasFormat(AV_CODEC_ID_AC3)) {
                                m_eAudioDecoder->m_transcode_to = AV_CODEC_ID_AC3;
                            }
                            if (m_eAudioDecoder->start(samplingRate, channels, BYTES_PER_SAMPLE, codec_id) < 0) {
                                delete m_eAudioDecoder;
                                m_eAudioDecoder = NULL;
                                break;
                            }
                        }
                        m_pes.codec_id = codec_id;
                    }

                    if (codec_id == AV_CODEC_ID_AC4) {
                        /* Decoder and IEC 61937-13 burst both want raw_ac4_frame. */
                        unsigned int hdr = ((q[2] << 8 | q[3]) == 0xFFFF) ? 7u : 4u;
                        unsigned int crc = (q[1] == 0x41) ? 2u : 0u;
                        const uint8_t *raw = q + hdr;
                        unsigned int rawSize = frameSize - hdr - crc;
                        if (m_ePassthrough)
                            m_ePassthrough->pushFrame(raw, rawSize, m_pes.PTS);
                        else if (m_eAudioDecoder)
                            m_eAudioDecoder->decode((uint8_t *)raw, rawSize, m_pes.PTS, m_pes.DTS);
                    } else if (m_ePassthrough) {
                        m_ePassthrough->pushFrame((const uint8_t *)q, frameSize, m_pes.PTS);
                    } else if (m_eAudioDecoder) {
                        m_eAudioDecoder->decode((uint8_t *)q, frameSize, m_pes.PTS, m_pes.DTS);
                    }

                    //m_pes.PTS = AV_NOPTS_VALUE;
                    //m_pes.DTS = AV_NOPTS_VALUE;
                    m_pes.Skip += frameSize;
                    break;
                }
                //  if (m_pes.codec_id != AV_CODEC_ID_NONE)
                //     eDebug("[eTsParser] skip @%d %02x", m_pes.Skip, q[0]);

                // try next byte
                ++m_pes.Skip;
                ++q;
                --n;
            }
            break;

        case PES_SYNC:		// wait for pes sync
            n = PES_START_CODE_SIZE - m_pes.HeaderIndex;
            if (n > size)
                n = size;
            memcpy(m_pes.Header + m_pes.HeaderIndex, p, n);
            m_pes.HeaderIndex += n;
            p += n;
            size -= n;

            // have complete packet start code
            if (m_pes.HeaderIndex >= PES_START_CODE_SIZE)
            {
                unsigned code;
                // bad mpeg pes packet start code prefix 0x00001xx
                if (m_pes.Header[0] || m_pes.Header[1] || m_pes.Header[2] != 0x01)
                {
                    m_pes.State = PES_SKIP;
                    return;
                }
                code = m_pes.Header[3];
                if (code != m_pes.StartCode)
                    m_pes.StartCode = code;

                m_pes.State = PES_HEADER;
                m_pes.HeaderSize = PES_HEADER_SIZE;
            }
            break;

        case PES_HEADER:		// parse PES header
            n = m_pes.HeaderSize - m_pes.HeaderIndex;
            if (n > size)
                n = size;
            memcpy(m_pes.Header + m_pes.HeaderIndex, p, n);
            m_pes.HeaderIndex += n;
            p += n;
            size -= n;

            // have header upto size bits
            if (m_pes.HeaderIndex == PES_HEADER_SIZE)
            {
                if ((m_pes.Header[6] & 0xC0) != 0x80)
                {
                    m_pes.State = PES_SKIP;
                    return;
                }
                // have pes extension
                if (!m_pes.Header[8])
                    goto empty_header;

                m_pes.HeaderSize += m_pes.Header[8];
                // have complete header
            }
            else if (m_pes.HeaderIndex == m_pes.HeaderSize)
            {

                if ((m_pes.Header[7] & 0xC0) == 0x80)
                {
                    m_pes.PTS =
                        (int64_t) (data[9] & 0x0E) << 29 | data[10] << 22 |
                        (data[11] & 0xFE) << 14 | data[12] << 7 | (data[13] & 0xFE) >> 1;
                }
                else if ((m_pes.Header[7] & 0xC0) == 0xC0)
                {
                    m_pes.PTS =
                        (int64_t) (data[9] & 0x0E) << 29 | data[10] << 22 |
                        (data[11] & 0xFE) << 14 | data[12] << 7 | (data[13]
                                & 0xFE) >> 1;

                    m_pes.DTS =
                        (int64_t) (data[14] & 0x0E) << 29 | data[15] << 22
                        | (data[16] & 0xFE) << 14 | data[17] << 7 |
                        (data[18] & 0xFE) >> 1;
                }

empty_header:
                m_pes.State = PES_INIT;
                if (m_pes.StartCode == 0xBD)  //PES_PRIVATE_STREAM1 0xBD
                    m_pes.State = PES_START;

            }
            break;
        }
    }
    while ((size > 0) && (m_stop == 0));
}

// callback
void my_ffmpeg_log(void *ptr, int level, const char *fmt, va_list vl)
{
    /// Here you can set a more detailed level
    if (level < AV_LOG_VERBOSE)
    {
        static char message[8192];
        const char *module = NULL;

        if (ptr)
        {
            AVClass *avc = *(AVClass**) ptr;
            if (avc->item_name)
                module = avc->item_name(ptr);
        }
        vsnprintf(message, sizeof(message), fmt, vl);
        eDebug("[libav] %s %s",module ? module : "", message);
    }
}

int eTsParser::play(const uint8_t * data, int size)
{
    const uint8_t *p = data;;
    int pid;

    while ((size >= TS_PACKET_SIZE) && (!m_pause) && (!m_stop))
    {
        int payload;

        if (p[0] != TS_PACKET_SYNC)
            return size;

        if (p[1] & 0x80)  		// error indicator
            goto next_packet;

        // skip adaptation field
        switch (p[3] & 0x30)  		// adaption field
        {
        case 0x00:			// reserved
        case 0x20:			// adaptation field only
        default:
            goto next_packet;
        case 0x10:			// only payload
            payload = 4;
            break;
        case 0x30:			// skip adapation field
            payload = 5 + p[4];
            // illegal length, ignore packet
            if (payload >= TS_PACKET_SIZE)
                goto next_packet;
            break;
        }

        pid = ((p[1] << 8) + p[2]) & 0x1fff;
        //eDebug("[eTsParser] audio pid %04X", pid);
        parse(p + payload, TS_PACKET_SIZE - payload, p[1] & 0x40);

next_packet:
        p += TS_PACKET_SIZE;
        size -= TS_PACKET_SIZE;
    }
    return p - data;
}


eTsParser::eTsParser():
    m_eAudioDecoder(0),
    m_ePassthrough(0),
    m_stop(1),
    m_fd_demux(-1),
    m_pause(false),
    m_truehd_parser(NULL),
    m_truehd_pctx(NULL)
{
    // initialize:
    av_log_set_callback(&my_ffmpeg_log);
    memset(&m_pes, 0, sizeof(m_pes));
    m_pes.Size = PES_MAX_PAYLOAD;
    //m_pes.Buffer = (uint8_t*) malloc(/*PES_MAX_PAYLOAD*/ AUDIO_INBUF_SIZE + INPUT_BUFFER_PADDING_SIZE);
    m_pes.Buffer = (uint8_t*) malloc(PES_MAX_PAYLOAD + INPUT_BUFFER_PADDING_SIZE);
    m_pes.State = PES_INIT;
    m_pes.Index = 0;
    m_pes.Skip = 0;
    m_pes.StartCode = -1;
    m_pes.PTS = AV_NOPTS_VALUE;
    m_pes.DTS = AV_NOPTS_VALUE;
    m_pes.codec_id = AV_CODEC_ID_NONE;
}


eTsParser::~eTsParser()
{
    eDebug("[eTsParser] delete eTsParser");
    stop();
    freeTrueHdParser();
}

void eTsParser::freeTrueHdParser()
{
    if (m_truehd_parser) { av_parser_close(m_truehd_parser); m_truehd_parser = NULL; }
    if (m_truehd_pctx)   { avcodec_free_context(&m_truehd_pctx); }
}

/* Cheap byte-scan for the Dolby TrueHD MLP major-sync magic
 * (F8 72 6F BA). When absent the libavcodec parser will not lock, so
 * gating the expensive parse call on this hint keeps the hot path
 * (per-iteration AC3/MP2 detection) fast and — crucially — avoids
 * mutating the parser's internal state on garbage bytes. False
 * positives are extremely rare (4-byte distinctive magic). */
static bool fastTrueHdHint(const uint8_t *p, unsigned int size)
{
    static const uint8_t magic[4] = { 0xF8, 0x72, 0x6F, 0xBA };
    if (size < 4) return false;
    unsigned int scan = size > 256 ? 256 : size;
    for (unsigned int i = 0; i + 4 <= scan; ++i)
        if (p[i] == 0xF8 && memcmp(p + i, magic, 4) == 0) return true;
    return false;
}

/* Frame-splitter for Dolby TrueHD (MLP). No fixed sync-at-offset-0
 * like AC3/DTS, so use libavcodec's MLP parser to find access-unit
 * boundaries and read sample_rate / channel-count from the major sync
 * header. Returns true ONLY on a complete frame — partial parses and
 * sync failures return false so the caller can reset the parser
 * cleanly and not desync the outer per-byte advance loop. */
bool eTsParser::trueHdCheck(const uint8_t *p, unsigned int size,
                            unsigned int &frameSize, unsigned int &channels,
                            unsigned int &samplingRate)
{
    frameSize = 0; channels = 0; samplingRate = 0;
    if (!m_truehd_parser) {
        m_truehd_parser = av_parser_init(AV_CODEC_ID_TRUEHD);
        if (!m_truehd_parser) return false;
        const AVCodec *c = avcodec_find_decoder(AV_CODEC_ID_TRUEHD);
        m_truehd_pctx = avcodec_alloc_context3(c);
        if (!m_truehd_pctx) { av_parser_close(m_truehd_parser); m_truehd_parser = NULL; return false; }
    }
    uint8_t *out_data = NULL;
    int out_size = 0;
    int consumed = av_parser_parse2(m_truehd_parser, m_truehd_pctx,
                                    &out_data, &out_size,
                                    p, (int)size,
                                    AV_NOPTS_VALUE, AV_NOPTS_VALUE, 0);
    if (consumed <= 0 || out_size <= 0) return false;
    frameSize    = (unsigned int)consumed;
    samplingRate = m_truehd_pctx->sample_rate ? m_truehd_pctx->sample_rate : 48000;
#if LIBAVCODEC_VERSION_INT >= AV_VERSION_INT(59, 37, 100)
    channels     = m_truehd_pctx->ch_layout.nb_channels ? m_truehd_pctx->ch_layout.nb_channels : 2;
#else
    channels     = m_truehd_pctx->channels ? m_truehd_pctx->channels : 2;
#endif
    return channels > 0 && samplingRate > 0;
}


int eTsParser::startPid(int fd_demux)
{
    m_fd_demux = fd_demux;
    m_stop = 0;
    run();
    return 0;
}

void eTsParser::stop()
{

    if (m_stop == 1)
        return;

    m_stop = 1;

    eDebug("[eTsParser] stop eTsParser");

    /* Wake any blocked pushData before joining - avoids deadlock on kill(). */
    if (m_eAudioDecoder && m_eAudioDecoder->m_AlsaOutput)
        m_eAudioDecoder->m_AlsaOutput->stop();
    if (m_ePassthrough)
        m_ePassthrough->stop();

    kill();

    av_log_set_callback(&av_log_default_callback);

    if(m_pes.Buffer)
    {
        free(m_pes.Buffer);
        m_pes.Buffer = NULL;
    }

    if(m_eAudioDecoder)
    {
        delete m_eAudioDecoder;
        m_eAudioDecoder = NULL;
    }

    if(m_ePassthrough)
    {
        delete m_ePassthrough;
        m_ePassthrough = NULL;
    }

}

void eTsParser::flush()
{

}

void eTsParser::freeze()
{
    m_pause = true;
}

void eTsParser::unfreeze()
{
    m_pause = false;
}

void eTsParser::setChannel(int channel)
{

}

int eTsParser::getPTS(pts_t &now)
{
    now = m_pes.PTS;
    return 0;
}


void eTsParser::thread()
{

    unsigned int tsPktNum = 0;
    uint8_t tsBuffer[INBUF_SIZE]; //1022 * TS_PACKET_SIZE
    struct pollfd fds;
    int rc;

    hasStarted();

    {
        struct sched_param sp = { 0 };
        sp.sched_priority = sched_get_priority_min(SCHED_FIFO);
        pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);
    }

    fcntl(m_fd_demux, F_SETFL, O_NONBLOCK);
    fds.fd = m_fd_demux;
    fds.events = (POLLIN | POLLPRI);

    while(!m_stop)
    {
        rc = poll(&fds, 1, 200);
        if(rc < 0)
        {
            if(errno == EINTR)
                continue;
            else
                goto to_end;
        }
        else if (rc == 0)
        {
            continue;
        }
        else if (rc > 0)
        {

            if (fds.revents & (POLLIN | POLLPRI))
            {
                tsPktNum = read(m_fd_demux, tsBuffer, sizeof(tsBuffer));
                if (tsPktNum <= 0)
                {
                    if ((errno == EWOULDBLOCK) | (errno == EAGAIN))
                        continue;
                    goto to_end;
                }

                play(tsBuffer, tsPktNum);
            }

            if (fds.revents & (POLLHUP | POLLNVAL))
            {
                goto to_end;
            }
        }
    }

to_end:
    eDebug("[eTsParser] stop Thread");

}