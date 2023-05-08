#ifndef __LIB_DVB_TSPARSER_H
#define __LIB_DVB_TSPARSER_H



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
#include "../dvb/decoders.h"
#include "../base/thread.h"
#else
#include <lib/dvb/decoders.h>
#include <lib/base/thread.h>
#include <lib/base/object.h>
#include <lib/dvb/demux.h>
#endif


enum
{
    PES_INIT,				///< unknown codec
    PES_SKIP,				///< skip packet
    PES_SYNC,				///< search packet sync byte
    PES_HEADER,				///< copy header
    PES_START,				///< pes packet start found
    PES_PAYLOAD,			///< copy payload
};

#define PES_START_CODE_SIZE 6
#define PES_HEADER_SIZE 9
#define PES_MAX_HEADER_SIZE (PES_HEADER_SIZE + 256)
#define PES_MAX_PAYLOAD	(512 * 1024)
#define TS_PACKET_SIZE	188
#define TS_PACKET_SYNC	0x47

typedef struct _pes_demux_
{
    int State;
    uint8_t Header[PES_MAX_HEADER_SIZE];
    int HeaderIndex;
    int HeaderSize;
    uint8_t *Buffer;
    int Index;
    int Skip;
    int Size;
    uint8_t StartCode;
    uint64_t PTS;
    uint64_t DTS;
    enum AVCodecID codec_id;
} pes_demux;


///
const uint16_t BitRateTable[2][3][16] =
{
    {
        // MPEG Version 1
        {0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0},
        {0, 32, 48, 56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320, 384, 0},
        {0, 32, 40, 48,  56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320, 0}
    },
    {
        // MPEG Version 2 & 2.5
        {0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0},
        {0,  8, 16, 24, 32, 40, 48,  56,  64,  80,  96, 112, 128, 144, 160, 0},
        {0,  8, 16, 24, 32, 40, 48,  56,  64,  80,  96, 112, 128, 144, 160, 0}
    }
};


const uint16_t MpegSampleRateTable[4] =
{ 44100, 48000, 32000, 0 };


const uint32_t Mpeg4SampleRateTable[16] =
{
    96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050,
    16000, 12000, 11025,  8000,  7350,     0,     0,     0
};


const uint16_t Ac3SampleRateTable[4] =
{ 48000, 44100, 32000, 0 };


const uint16_t Ac3FrameSizeTable[38][3] =
{
    {  64,   69,   96}, {  64,   70,   96}, {  80,   87,  120}, { 80,  88,  120},
    {  96,  104,  144}, {  96,  105,  144}, { 112,  121,  168}, {112, 122,  168},
    { 128,  139,  192}, { 128,  140,  192}, { 160,  174,  240}, {160, 175,  240},
    { 192,  208,  288}, { 192,  209,  288}, { 224,  243,  336}, {224, 244,  336},
    { 256,  278,  384}, { 256,  279,  384}, { 320,  348,  480}, {320, 349,  480},
    { 384,  417,  576}, { 384,  418,  576}, { 448,  487,  672}, {448, 488,  672},
    { 512,  557,  768}, { 512,  558,  768}, { 640,  696,  960}, {640, 697,  960},
    { 768,  835, 1152}, { 768,  836, 1152}, { 896,  975, 1344}, {896, 976, 1344},
    {1024, 1114, 1536}, {1024, 1115, 1536}, {1152, 1253, 1728},
    {1152, 1254, 1728}, {1280, 1393, 1920}, {1280, 1394, 1920},
};


const uint32_t DtsSampleRateTable[16] =
{
    0,  8000, 16000, 32000, 64000,
    0, 11025, 22050, 44100, 88200,
    0, 12000, 24000, 48000, 96000, 0
};

/* ------------------------------------------------------------------------- */

#define AV_CH_LAYOUT(ch) ( \
		ch == 1 ? AV_CH_LAYOUT_MONO    : \
		ch == 2 ? AV_CH_LAYOUT_STEREO  : \
		ch == 3 ? AV_CH_LAYOUT_2POINT1 : \
		ch == 6 ? AV_CH_LAYOUT_5POINT1 : 0)

#define AV_SAMPLE_STR(fmt) ( \
		fmt == AV_SAMPLE_FMT_U8   ? "U8"             : \
		fmt == AV_SAMPLE_FMT_S16  ? "S16"            : \
		fmt == AV_SAMPLE_FMT_S32  ? "S32"            : \
		fmt == AV_SAMPLE_FMT_FLT  ? "float"          : \
		fmt == AV_SAMPLE_FMT_DBL  ? "double"         : \
		fmt == AV_SAMPLE_FMT_U8P  ? "U8, planar"     : \
		fmt == AV_SAMPLE_FMT_S16P ? "S16, planar"    : \
		fmt == AV_SAMPLE_FMT_S32P ? "S32, planar"    : \
		fmt == AV_SAMPLE_FMT_FLTP ? "float, planar"  : \
		fmt == AV_SAMPLE_FMT_DBLP ? "double, planar" : "unknown")

/* ------------------------------------------------------------------------- */

#if defined(__CYGWIN__) || defined(CUSTUM)
typedef uint64_t pts_t;
#endif

class eTsParser: public eThread
{
    pes_demux m_pes_demux;

public:
    eTsParser();
    ~eTsParser();
    void thread();

    eAudioDecoder *m_eAudioDecoder;
    void set_pts();
    void set_latency();
    void parse(const uint8_t * data, int size,  int is_start);
    int play(const uint8_t * data, int size);


    int startPid(int fd_demux);
    void stop();
    void flush();
    void freeze();
    void unfreeze();
    void setChannel(int channel);
    int getPTS(pts_t &now);
    
private:
    int m_stop;
    int m_fd_demux;
    bool m_pause;

};

#endif //__LIB_DVB_TSPARSER_H
