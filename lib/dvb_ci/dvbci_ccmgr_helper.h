#ifndef __RES_CONTENT_CTRL_HELPER_H
#define __RES_CONTENT_CTRL_HELPER_H

#include <openssl/x509.h>
#include <openssl/x509v3.h>

void traceHexdump(const uint8_t *data, unsigned int len);
int get_random(uint8_t *dest, int len);
int add_padding(uint8_t *dest, unsigned int len, unsigned int blocklen);
void str2bin(uint8_t *dst, char *data, int len);
uint32_t UINT32(const uint8_t *in, unsigned int len);
int BYTE32(uint8_t *dest, uint32_t val);
int BYTE16(uint8_t *dest, uint16_t val);
bool get_authdata(uint8_t *host_id, uint8_t *dhsk, uint8_t *akh, unsigned int slot, unsigned int index);
bool write_authdata(unsigned int slot, const uint8_t *host_id, const uint8_t *dhsk, const uint8_t *akh);
bool parameter_init(unsigned int slot, uint8_t* dh_p, uint8_t* dh_g, uint8_t* dh_q, uint8_t* s_key, uint8_t* key_data, uint8_t* iv);
RSA *rsa_privatekey_open(const char *filename);
int verify_cb(int ok, X509_STORE_CTX *ctx);
X509 *certificate_load_and_check(X509_STORE *store, const char *filename);
X509 *certificate_import_and_check(X509_STORE *store, const uint8_t *data, int len);
bool ciplus_cert_param_files_exists();

#endif
