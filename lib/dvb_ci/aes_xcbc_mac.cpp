#include <stdint.h>
#include <string.h>
#include <openssl/aes.h>

#include "aes_xcbc_mac.h"

int aes_xcbc_mac_init(struct aes_xcbc_mac_ctx *ctx, const uint8_t *key)
{
	AES_KEY aes_key;
	int y, x;

	AES_set_encrypt_key(key, 128, &aes_key);

	for (y = 0; y < 3; y++) {
		for (x = 0; x < 16; x++)
			ctx->K[y][x] = y + 1;
		AES_ecb_encrypt(ctx->K[y], ctx->K[y], &aes_key, 1);
	}

	/* setup K1 */
	AES_set_encrypt_key(ctx->K[0], 128, &ctx->key);

	memset(ctx->IV, 0, 16);
	ctx->buflen = 0;

	return 0;
}

int aes_xcbc_mac_process(struct aes_xcbc_mac_ctx *ctx, const uint8_t *in, unsigned int len)
{
	while (len) {
		if (ctx->buflen == 16) {
			AES_ecb_encrypt(ctx->IV, ctx->IV, &ctx->key, 1);
			ctx->buflen = 0;
		}
		ctx->IV[ctx->buflen++] ^= *in++;
		--len;
	}

	return 0;
}

int aes_xcbc_mac_done(struct aes_xcbc_mac_ctx *ctx, uint8_t *out)
{
	int i;

	if (ctx->buflen == 16) {
		/* K2 */
		for (i = 0; i < 16; i++)
			ctx->IV[i] ^= ctx->K[1][i];
	} else {
		ctx->IV[ctx->buflen] ^= 0x80;
		/* K3 */
		for (i = 0; i < 16; i++)
			ctx->IV[i] ^= ctx->K[2][i];
	}

	AES_ecb_encrypt(ctx->IV, ctx->IV, &ctx->key, 1);
	memcpy(out, ctx->IV, 16);

	return 0;
}
