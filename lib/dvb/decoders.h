#ifndef __LIB_COMPONENTS_DECODER_H
#define __LIB_COMPONENTS_DECODER_H




extern "C" {
#include <libavformat/avformat.h>
#include <libavdevice/avdevice.h>
#include <libavcodec/avcodec.h>
#include <libswresample/swresample.h>
#include <libavutil/opt.h>
#include <libavutil/channel_layout.h>
#include <libavutil/samplefmt.h>
#include <libavutil/mem.h>
}
#if defined(__CYGWIN__) || defined(CUSTUM)
#include <cstdint>
#include <cstdio>
#include "../dvb/alsa.h"
#include "../dvb/ringbuffer.h"
#else
#include <lib/dvb/alsa.h>
#include <lib/dvb/ringbuffer.h>
#endif

class eAudioDecoder
{

public:
    eAudioDecoder();
    ~eAudioDecoder();
    bool started;


    int start(int sample_rate, int channels, int bit_rate, enum AVCodecID codec_id);
    int decode(const AVPacket *avpkt);
    
    unsigned int m_channels;
    unsigned int m_sample_rate;
    unsigned int m_bits;

    class AVCodec		 *m_codec;
    class AVCodecContext *m_codec_ctx;
    class SwrContext     *m_swr_ctx;
    
    eAlsaOutput *m_AlsaOutput;
    unsigned int m_alsa_channels;
    unsigned int m_alsa_sample_rate;
    
    
    uint16_t m_spdif[24576 / 2];		///< SPDIF output buffer
    int m_spdifindex;			///< index into SPDIF output buffer
    int m_spdifcount;			///< SPDIF repeat counter
    

};

#endif //__LIB_COMPONENTS_DECODER_H
