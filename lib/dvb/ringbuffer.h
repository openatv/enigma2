#ifndef __RING_BUFFER_H__
#define __RING_BUFFER_H__
#include <string.h>
#include <sys/types.h>
#include <stddef.h>
#define GCC_VERSION (__GNUC__ * 10000 \
	+ __GNUC_MINOR__ * 100 \
	+ __GNUC_PATCHLEVEL__)

//	gcc before 4.7 didn't support atomic builtins,
//	use alsa atomic functions.
#if GCC_VERSION < 40700

#include <alsa/iatomic.h>

#else

typedef volatile int atomic_t;

#define atomic_set(ptr, val) \
    __atomic_store_n(ptr, val, __ATOMIC_SEQ_CST)

#define atomic_read(ptr) \
    __atomic_load_n(ptr, __ATOMIC_SEQ_CST)

#define atomic_inc(ptr) \
    __atomic_add_fetch(ptr, 1, __ATOMIC_SEQ_CST)

#define atomic_dec(ptr) \
    __atomic_sub_fetch(ptr, 1, __ATOMIC_SEQ_CST)

#define atomic_add(val, ptr) \
    __atomic_add_fetch(ptr, val, __ATOMIC_SEQ_CST)

#define atomic_sub(val, ptr) \
    __atomic_sub_fetch(ptr, val, __ATOMIC_SEQ_CST)

#endif

#if defined(__CYGWIN__) || defined(CUSTUM)
#include <cstdint>
#endif


typedef struct
{
    ssize_t size;
    uint8_t *wr;
    const uint8_t *rd;
    uint8_t *ptr;
    const uint8_t *ptr_end;
    atomic_t filled;

} ring_buffer_t;

class eRingBuffer
{

public:
    eRingBuffer(const ssize_t size);
    ~eRingBuffer();

    void reset();
    size_t write_advance(size_t cnt);
    size_t write(const uint8_t *buf, size_t cnt);
    size_t get_write_pointer(uint8_t **wp);
    size_t read_advance(size_t cnt);
    size_t read( uint8_t *buf, size_t cnt);
    size_t get_read_pointer(const uint8_t **rp);
    size_t free_bytes();
    size_t used_bytes();

private:
    ring_buffer_t m_ringBuffer;
};

#endif
