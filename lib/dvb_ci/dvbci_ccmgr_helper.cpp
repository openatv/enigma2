#include <fcntl.h>
#include <openssl/pem.h>
#include <openssl/aes.h>

#include <lib/dvb_ci/dvbci_ccmgr_helper.h>

#include <lib/base/eerror.h>


// misc helper functions

void traceHexdump(const uint8_t *data, unsigned int len)
{
	while (len--)
		eTraceNoNewLine("%02x ", *data++);
	eTraceNoNewLine("\n");
}

int get_random(uint8_t *dest, int len)
{
	int fd;
	const char *urnd = "/dev/urandom";

	fd = open(urnd, O_RDONLY);
	if (fd <= 0)
	{
		eWarning("[CI RCC] cannot open %s", urnd);
		return -1;
	}

	if (read(fd, dest, len) != len)
	{
		eWarning("[CI RCC] cannot read from %s", urnd);
		close(fd);
		return -2;
	}

	close(fd);

	return len;
}

int add_padding(uint8_t *dest, unsigned int len, unsigned int blocklen)
{
	uint8_t padding = 0x80;
	int count = 0;

	while (len & (blocklen - 1))
	{
		*dest++ = padding;
		++len;
		++count;
		padding = 0;
	}

	return count;
}

int get_bin_from_nibble(int in)
{
	if ((in >= '0') && (in <= '9'))
		return in - 0x30;

	if ((in >= 'A') && (in <= 'Z'))
		return in - 0x41 + 10;

	if ((in >= 'a') && (in <= 'z'))
		return in - 0x61 + 10;

	eWarning("[CI RCC] unsupported chars in device id");

	return 0;
}

void str2bin(uint8_t *dst, char *data, int len)
{
	int i;

	for (i = 0; i < len; i += 2)
		*dst++ = (get_bin_from_nibble(data[i]) << 4) | get_bin_from_nibble(data[i + 1]);
}

uint32_t UINT32(const uint8_t *in, unsigned int len)
{
	uint32_t val = 0;
	unsigned int i;

	for (i = 0; i < len; i++)
	{
		val <<= 8;
		val |= *in++;
	}

	return val;
}

int BYTE32(uint8_t *dest, uint32_t val)
{
	*dest++ = val >> 24;
	*dest++ = val >> 16;
	*dest++ = val >> 8;
	*dest++ = val;

	return 4;
}

int BYTE16(uint8_t *dest, uint16_t val)
{
	*dest++ = val >> 8;
	*dest++ = val;
	return 2;
}

// storage & load of authenticated data (HostID & DHSK & AKH)

#ifndef FILENAME_MAX
#define FILENAME_MAX 256
#endif
#define MAX_PAIRS 10
#define PAIR_SIZE (8 + 256 + 32)

void get_authdata_filename(char *dest, size_t len, unsigned int slot)
{
	snprintf(dest, len, "/etc/ciplus/ci_auth_slot_%u.bin", slot);
}

bool get_authdata(uint8_t *host_id, uint8_t *dhsk, uint8_t *akh, unsigned int slot, unsigned int index)
{
	char filename[FILENAME_MAX];
	int fd;
	uint8_t chunk[PAIR_SIZE];
	unsigned int i;

	if (index >= MAX_PAIRS)
		return false;

	get_authdata_filename(filename, sizeof(filename), slot);

	fd = open(filename, O_RDONLY);
	if (fd <= 0)
	{
		eDebug("[CI%d RCC] can not open %s", slot, filename);
		return false;
	}

	for (i = 0; i <= index; i++)
	{
		if (read(fd, chunk, sizeof(chunk)) != sizeof(chunk))
		{
			eDebug("[CI%d RCC] can not read auth_data", slot);
			close(fd);
			return false;
		}
	}

	close(fd);

	memcpy(host_id, chunk, 8);
	memcpy(dhsk, &chunk[8], 256);
	memcpy(akh, &chunk[8 + 256], 32);

	return true;
}

bool write_authdata(unsigned int slot, const uint8_t *host_id, const uint8_t *dhsk, const uint8_t *akh)
{
	char filename[FILENAME_MAX];
	int fd;
	uint8_t buf[PAIR_SIZE * MAX_PAIRS];
	int entries;

	for (entries = 0; entries < MAX_PAIRS; entries++)
	{
		int offset = PAIR_SIZE * entries;
		if (!get_authdata(&buf[offset], &buf[offset + 8], &buf[offset + 8 + 256], slot, entries))
			break;

		/* check if we got this pair already */
		if (!memcmp(&buf[offset + 8 + 256], akh, 32))
		{
			eDebug("[CI%d RCC] data already stored", slot);
			return true;
		}
	}

	if (entries > 0)
	{
		if (entries == MAX_PAIRS)
			entries--;

		memmove(buf + PAIR_SIZE, buf, PAIR_SIZE * entries);
	}

	memcpy(buf, host_id, 8);
	memcpy(buf + 8, dhsk, 256);
	memcpy(buf + 8 + 256, akh, 32);
	entries++;

	eDebug("[CI%d RCC] %d entries for writing", slot, entries);

	get_authdata_filename(filename, sizeof(filename), slot);
	fd = open(filename, O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
	if (fd < 0)
	{
		eWarning("[CI%d RCC] can not open %s", slot, filename);
		return false;
	}

	if (write(fd, buf, PAIR_SIZE * entries) != PAIR_SIZE * entries)
		eWarning("[CI%d RCC] error in write", slot);

	close(fd);

	return true;
}

bool parameter_init(unsigned int slot, uint8_t* dh_p, uint8_t* dh_g, uint8_t* dh_q, uint8_t* s_key, uint8_t* key_data, uint8_t* iv)
{
	int fd;
	unsigned char buf[592];

	fd = open("/etc/ciplus/param", O_RDONLY);
	if (fd <= 0)
	{
		eDebug("[CI%d RCC] can not param file", slot);
		return false;
	}

	if (read(fd, buf, sizeof(buf)) != sizeof(buf))
	{
		eDebug("[CI%d RCC] can not read parameters", slot);
		close(fd);
		return false;
	}

	close(fd);

	memcpy(dh_p, buf, 256);
	memcpy(dh_g, &buf[256], 256);
	memcpy(dh_q, &buf[512], 32);
	memcpy(s_key, &buf[544], 16);
	memcpy(key_data, &buf[560], 16);
	memcpy(iv, &buf[576], 16);

	return true;
}

// CI+ certificates

RSA *rsa_privatekey_open(const char *filename)
{
	FILE *fp;
	RSA *r = NULL;

	fp = fopen(filename, "r");
	if (!fp)
	{
		eWarning("[CI RCC] can not open %s", filename);
		return NULL;
	}

	PEM_read_RSAPrivateKey(fp, &r, NULL, NULL);
	if (!r)
		eWarning("[CI RCC] can not read %s", filename);

	fclose(fp);

	return r;
}

X509 *certificate_open(const char *filename)
{
	FILE *fp;
	X509 *cert;

	fp = fopen(filename, "r");
	if (!fp)
	{
		eWarning("[CI RCC] can not open %s", filename);
		return NULL;
	}

	cert = PEM_read_X509(fp, NULL, NULL, NULL);
	if (!cert)
		eWarning("[CI RCC] can not read %s", filename);

	fclose(fp);

	return cert;
}

#if OPENSSL_VERSION_NUMBER < 0x10100000L
int DH_set0_pqg(DH *dh, BIGNUM *p, BIGNUM *q, BIGNUM *g)
{
	/* If the fields p and g in d are NULL, the corresponding input
	* parameters MUST be non-NULL.  q may remain NULL.
	*/
	if ((dh->p == NULL && p == NULL) || (dh->g == NULL && g == NULL))
		return 0;

	if (p != NULL)
	{
		BN_free(dh->p);
		dh->p = p;
	}
	if (q != NULL)
	{
		BN_free(dh->q);
		dh->q = q;
	}
	if (g != NULL)
	{
		BN_free(dh->g);
		dh->g = g;
	}

	if (q != NULL)
	{
		dh->length = BN_num_bits(q);
	}

	return 1;
}

void DH_get0_key(const DH *dh, const BIGNUM **pub_key, const BIGNUM **priv_key)
{
	if (pub_key != NULL)
		*pub_key = dh->pub_key;
	if (priv_key != NULL)
		*priv_key = dh->priv_key;
}

void DH_set_flags(DH *dh, int flags)
{
	dh->flags |= flags;
}
#endif

int verify_cb(int ok, X509_STORE_CTX *ctx)
{
	if (X509_STORE_CTX_get_error(ctx) == X509_V_ERR_CERT_NOT_YET_VALID)
	{
		time_t now = time(NULL);
		struct tm t;
		localtime_r(&now, &t);
		if (t.tm_year < 2024)
		{
			eDebug("[CI RCC] seems our system clock is wrong - ignore!");
			return 1;
		}
	}

	if (X509_STORE_CTX_get_error(ctx) == X509_V_ERR_CERT_HAS_EXPIRED)
		return 1;

	return 0;
}

bool certificate_validate(X509_STORE *store, X509 *cert)
{
	X509_STORE_CTX *store_ctx;
	int ret;

	store_ctx = X509_STORE_CTX_new();

	X509_STORE_CTX_init(store_ctx, store, cert, NULL);
	X509_STORE_CTX_set_verify_cb(store_ctx, verify_cb);
	X509_STORE_CTX_set_flags(store_ctx, X509_V_FLAG_IGNORE_CRITICAL);

	ret = X509_verify_cert(store_ctx);

	if (ret != 1)
		eWarning("[CI RCC] %s", X509_verify_cert_error_string(X509_STORE_CTX_get_error(store_ctx)));

	X509_STORE_CTX_free(store_ctx);

	return ret == 1;
}

X509 *certificate_load_and_check(X509_STORE *store, const char *filename)
{
	X509 *cert;

	cert = certificate_open(filename);
	if (!cert)
	{
		eWarning("[CI RCC] can not open %s", filename);
		return NULL;
	}

	if (!certificate_validate(store, cert))
	{
		eWarning("[CI RCC] can not validate %s", filename);
		X509_free(cert);
		return NULL;
	}

	X509_STORE_add_cert(store, cert);

	return cert;
}

X509 *certificate_import_and_check(X509_STORE *store, const uint8_t *data, int len)
{
	X509 *cert;

	cert = d2i_X509(NULL, &data, len);
	if (!cert)
	{
		eWarning("[CI RCC] can not read certificate");
		return NULL;
	}

	if (!certificate_validate(store, cert))
	{
		eWarning("[CI RCC] can not vaildate certificate\n");
		X509_free(cert);
		return NULL;
	}

	X509_STORE_add_cert(store, cert);

	return cert;
}

bool ciplus_cert_param_files_exists()
{
	if (access("/etc/ciplus/param", R_OK ) != -1 &&
		access("/etc/ciplus/root.pem", R_OK ) != -1 &&
		access("/etc/ciplus/device.pem", R_OK ) != -1 &&
		access("/etc/ciplus/customer.pem", R_OK ) != -1)
		return true;

	return false;
}
