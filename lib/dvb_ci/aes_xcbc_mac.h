#ifndef __AES_XCBC_H_
#define __AES_XCBC_H_

#include <openssl/aes.h>

struct aes_xcbc_mac_ctx {
	uint8_t K[3][16];
	uint8_t IV[16];
	AES_KEY key;
	int buflen;
};

int aes_xcbc_mac_init(struct aes_xcbc_mac_ctx *ctx, const uint8_t *key);
int aes_xcbc_mac_process(struct aes_xcbc_mac_ctx *ctx, const uint8_t *in, unsigned int len);
int aes_xcbc_mac_done(struct aes_xcbc_mac_ctx *ctx, uint8_t *out);

#endif
