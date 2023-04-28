#ifndef __LIB_DRIVER_ALSA_H_
#define __LIB_DRIVER_ALSA_H_


#if defined(__CYGWIN__) || defined(CUSTUM)
#include "../base/thread.h"
#include "../base/elock.h"
#include "../dvb/ringbuffer.h"
#else
#include <lib/base/thread.h>
#include <lib/base/elock.h>
#include <lib/dvb/ringbuffer.h>
#endif

#ifdef __CYGWIN__
#define USE_OSS
#else
#define USE_ALSA
#endif 

#ifdef USE_OSS
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <sys/soundcard.h>
#ifndef SNDCTL_DSP_HALT_OUTPUT
#  if defined(SNDCTL_DSP_RESET_OUTPUT)
#    define SNDCTL_DSP_HALT_OUTPUT SNDCTL_DSP_RESET_OUTPUT
#  elif defined(SNDCTL_DSP_RESET)
#    define SNDCTL_DSP_HALT_OUTPUT SNDCTL_DSP_RESET
#  else
#    error "No valid SNDCTL_DSP_HALT_OUTPUT found."
#  endif
#endif
#include <poll.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#endif
#ifdef USE_ALSA
#include <alsa/asoundlib.h>
#endif

/// default ring buffer size ~2s 8ch 16bit (3 * 5 * 7 * 8)
#define MAX_AUDIO_FRAME_SIZE  (3 * 5 * 7 * 8 * 1 * 1000)

class eAlsaOutput: public eThread, public eSingleLock
{

protected:
#ifdef USE_ALSA
    snd_pcm_t* handle;
#endif
#ifdef USE_OSS
    int handle;
    uint64_t oss_fragment_time;
#endif
    uint64_t frame_fill;
    unsigned int m_rate;
    unsigned int  m_channels;
    unsigned int  m_bits;
    unsigned int  m_passthrough;


public:
    eAlsaOutput(const char *device_name);
    virtual ~eAlsaOutput();
    void thread();
    void set_volume(int16_t * samples, int count);
    int pcm_write();
    eRingBuffer *m_eRingBuffer;
    int pushData(uint8_t *data, int size);
    bool running() const;
    int start(unsigned int rate, unsigned int channels, unsigned int bits, unsigned int passthrough);
    void stop();
    
private:
    int m_stop;
};

#endif // __LIB_DRIVER_ALSA_H_
