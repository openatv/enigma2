#ifndef CRC32_H
#define CRC32_H

/* $Id: crc32.h,v 1.1 2003-10-17 15:35:49 tmbinc Exp $ */

#include <stdint.h>

extern const uint32_t crc32_table[256];

/* Return a 32-bit CRC of the contents of the buffer. */

static inline uint32_t
crc32(uint32_t val, const void *ss, int len)
{
	const unsigned char *s =(const unsigned char *) ss;
        while (--len >= 0)
//                val = crc32_table[(val ^ *s++) & 0xff] ^ (val >> 8);
                val = (val << 8) ^ crc32_table[(val >> 24) ^ *s++];
        return val;
}

#endif
