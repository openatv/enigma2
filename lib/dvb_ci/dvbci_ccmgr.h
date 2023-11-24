#ifndef __dvbci_dvbci_ccmgr_h
#define __dvbci_dvbci_ccmgr_h

#include <memory>
#include <openssl/x509.h>
#include <lib/dvb_ci/dvbci_session.h>

#include <openssl/dh.h>
void DH_get0_key(const DH *dh, const BIGNUM **pub_key, const BIGNUM **priv_key);
int DH_set0_pqg(DH *dh, BIGNUM *p, BIGNUM *q, BIGNUM *g);
void DH_set_flags(DH *dh, int flags);

class eDVBCICcSessionImpl;

class eDVBCICcSession: public eDVBCISession
{
	eDVBCISlot *m_slot;
	int m_descrambler_fd;
	uint8_t m_current_ca_demux_id;

	// CI+ credentials
	enum
	{
		BRAND_ID = 1,

		HOST_ID = 5,
		CICAM_ID = 6,
		HOST_BRAND_CERT = 7,
		CICAM_BRAND_CERT = 8,

		KP = 12,
		DHPH = 13,
		DHPM = 14,
		HOST_DEV_CERT = 15,
		CICAM_DEV_CERT = 16,
		SIGNATURE_A = 17,
		SIGNATURE_B = 18,
		AUTH_NONCE = 19,
		NS_HOST = 20,
		NS_MODULE = 21,
		AKH = 22,
		AKM = 23,

		URI_MESSAGE = 25,
		PROGRAM_NUMBER = 26,
		URI_CONFIRM = 27,
		KEY_REGISTER = 28,
		URI_VERSIONS = 29,
		STATUS_FIELD = 30,
		SRM_DATA = 31,
		SRM_CONFIRM = 32,

		CRITICAL_SEC_UPDATE = 49,

		MAX_ELEMENTS = 50
	};

	struct ciplus_element
	{
		uint8_t *m_data = NULL;
		uint32_t m_size;
		bool m_valid;
		void init()
		{
			invalidate();
		};
		void invalidate()
		{
			if (m_data)
				free(m_data);
			m_data = NULL;
			m_size = 0;
			m_valid = false;
		};
		void set(const uint8_t *data, uint32_t size)
		{
			if (m_data)
				free(m_data);
			m_data = (uint8_t *)malloc(size);
			if (m_data)
			{
				memcpy(m_data, data, size);
				m_size = size;
				m_valid = true;
			}
			else
			{
				m_size = 0;
				m_valid = false;
			}
		};
	};

	struct ciplus_elements
	{
		ciplus_element m_elements[MAX_ELEMENTS];
		const uint32_t m_datatype_sizes[MAX_ELEMENTS] = {
			0, 50, 0, 0, 0, 8, 8, 0,
			0, 0, 0, 0, 32, 256, 256, 0,
			0, 256, 256, 32, 8, 8, 32, 32,
			0, 8, 2, 32, 1, 32, 1, 0,
			32
		};
		void init()
		{
			unsigned int i;

			for (i = 1; i < MAX_ELEMENTS; i++)
				m_elements[i].invalidate();
		};
		struct ciplus_element* get(unsigned int id)
		{
			if ((id < 1) || (id >= MAX_ELEMENTS))
			{
				eWarning("[CI RCC] invalid id %u", id);
				return NULL;
			}
			return &m_elements[id];
		};
		uint8_t* get_ptr(unsigned int id)
		{
			struct ciplus_element *e = get(id);
			if (e == NULL)
				return NULL;

			if (!e->m_valid)
			{
				eWarning("[CI RCC] %u not valid", id);
				return NULL;
			}

			if (!e->m_data)
			{
				eWarning("[CI RCC] %u doesn't exist", id);
				return NULL;
			}

			return e->m_data;
		};
		unsigned int get_buf(uint8_t *dest, unsigned int id)
		{
			struct ciplus_element *e = get(id);
			if (e == NULL)
				return 0;

			if (!e->m_valid)
			{
				eWarning("[CI RCC] %u not valid", id);
				return 0;
			}

			if (!e->m_data)
			{
				eWarning("[CI RCC] %d doesn't exist", id);
				return 0;
			}

			if (dest)
				memcpy(dest, e->m_data, e->m_size);

			return e->m_size;
		};
		unsigned int get_req(uint8_t *dest, unsigned int id)
		{
			unsigned int len = get_buf(&dest[3], id);

			if (len == 0)
			{
				eWarning("[CI RCC] can not get %u", id);
				return 0;
			}

			dest[0] = id;
			dest[1] = len >> 8;
			dest[2] = len;

			return 3 + len;
		};
		bool set(unsigned int id, const uint8_t *data, uint32_t size)
		{
			struct ciplus_element *e = get(id);
			if (!e)
				return false;

			if ((m_datatype_sizes[id] != 0) && (m_datatype_sizes[id] != size))
			{
				eWarning("[CI RCC] size %u of id %u doesn't match", size, id);
				return false;
			}

			e->set(data, size);

			return e->m_valid;
		};
		void invalidate(unsigned int id)
		{
			struct ciplus_element *e = get(id);
			if (e)
				e->invalidate();
		};
		bool valid(unsigned int id)
		{
			struct ciplus_element *e = get(id);
			return e && e->m_valid;
		};
	} m_ci_elements;

	/* DHSK */
	uint8_t m_dhsk[256];

	/* KS_host */
	uint8_t m_ks_host[32];

	/* derived keys */
	uint8_t m_sek[16];
	uint8_t m_sak[16];

	/* AKH checks - module performs 5 tries to get correct AKH */
	unsigned int m_akh_index;

	/* Root CA */
	X509_STORE *m_root_ca_store;

	/* Host certificates */
	X509 *m_cust_cert;
	X509 *m_device_cert;

	/* Module certificates */
	X509 *m_ci_cust_cert;
	X509 *m_ci_device_cert;

	/* private key of device-cert */
	RSA *m_rsa_device_key;

	/* DH parameters */
	DH *m_dh;
	uint8_t m_dh_p[256];
	uint8_t m_dh_g[256];
	uint8_t m_dh_q[32];

	/* AES parameters */
	uint8_t m_s_key[16];
	uint8_t m_key_data[16];
	uint8_t m_iv[16];

	/* descrambler key */
	bool m_descrambler_new_key;
	uint8_t m_descrambler_key_iv[32];
	uint8_t m_descrambler_odd_even;

	int receivedAPDU(const unsigned char *tag, const void *data, int len);
	int doAction();

	void cc_open_req();
	void cc_data_req(const uint8_t *data, unsigned int len);
	void cc_sync_req(const uint8_t *data, unsigned int len);
	void cc_sac_data_req(const uint8_t *data, unsigned int len);
	void cc_sac_sync_req(const uint8_t *data, unsigned int len);
	void cc_sac_send(const uint8_t *tag, uint8_t *data, unsigned int pos);

	int data_get_loop(const uint8_t *data, unsigned int datalen, unsigned int items);
	int data_req_loop(uint8_t *dest, unsigned int dest_len, const uint8_t *data, unsigned int data_len, unsigned int items);

	int data_req_handle_new(unsigned int id);
	int data_get_handle_new(unsigned int id);

	void generate_key_seed();
	void generate_ns_host();
	int generate_SAK_SEK();
	int generate_akh();
	bool check_dh_challenge();
	int compute_dh_key();
	int generate_dh_key();
	int generate_sign_A();
	int restart_dh_challenge();
	int generate_uri_confirm();
	void check_new_key();

	bool sac_check_auth(const uint8_t *data, unsigned int len);
	int sac_gen_auth(uint8_t *out, uint8_t *in, unsigned int len);
	int sac_crypt(uint8_t *dst, const uint8_t *src, unsigned int len, int encrypt);

	X509 *import_ci_certificates(unsigned int id);
	int check_ci_certificates();

	bool ci_element_set_certificate(unsigned int id, X509 *cert);
	bool ci_element_set_hostid_from_certificate(unsigned int id, X509 *cert);

	void set_descrambler_key();

public:
	eDVBCICcSession(eDVBCISlot *tslot, int version);
	~eDVBCICcSession();

	void send(const unsigned char *tag, const void *data, int len);
	void addProgram(uint16_t program_number, std::vector<uint16_t>& pids);
	void removeProgram(uint16_t program_number, std::vector<uint16_t>& pids);
};

#endif
