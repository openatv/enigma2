/* DVB CI Content Control Manager */

#include <lib/dvb_ci/dvbci_ccmgr.h>

#include <lib/dvb_ci/aes_xcbc_mac.h>
#include <lib/dvb_ci/descrambler.h>
#include <lib/dvb_ci/dvbci_ccmgr_helper.h>

#include <openssl/aes.h>


eDVBCICcSession::eDVBCICcSession(eDVBCISlot *slot, int version):
	m_slot(slot), m_akh_index(0),
	m_root_ca_store(nullptr), m_cust_cert(nullptr), m_device_cert(nullptr),
	m_ci_cust_cert(nullptr), m_ci_device_cert(nullptr),
	m_rsa_device_key(nullptr), m_dh(nullptr)
{
	uint8_t buf[32], host_id[8];

	m_slot->setCCManager(this);
	m_descrambler_fd = descrambler_init();
	parameter_init(m_dh_p, m_dh_g, m_dh_q, m_s_key, m_key_data, m_iv);

	m_ci_elements.init();

	memset(buf, 0, 1);
	if (!m_ci_elements.set(STATUS_FIELD, buf, 1))
		eWarning("[CI RCC] can not set status");

	memset(buf, 0, 32);
	buf[31] = 0x01; // URI_PROTOCOL_V1
	if (version == 2)
		buf[31] |= 0x02; // URI_PROTOCOL_V2

	if (!m_ci_elements.set(URI_VERSIONS, buf, 32))
		eWarning("[CI RCC] can not set uri_versions");

	if (!get_authdata(host_id, m_dhsk, buf, m_slot->getSlotID(), m_akh_index))
	{
		memset(buf, 0, sizeof(buf));
		m_akh_index = 5;
	}

	if (!m_ci_elements.set(AKH, buf, 32))
		eWarning("[CI RCC] can not set AKH");

	if (!m_ci_elements.set(HOST_ID, host_id, 8))
		eWarning("[CI RCC] can not set host_id");
}

eDVBCICcSession::~eDVBCICcSession()
{
	m_slot->setCCManager(0);
	descrambler_deinit(m_descrambler_fd);

	if (m_root_ca_store)
		X509_STORE_free(m_root_ca_store);
	if (m_cust_cert)
		X509_free(m_cust_cert);
	if (m_device_cert)
		X509_free(m_device_cert);
	if (m_ci_cust_cert)
		X509_free(m_ci_cust_cert);
	if (m_ci_device_cert)
		X509_free(m_ci_device_cert);
	if (m_rsa_device_key)
		RSA_free(m_rsa_device_key);
	if (m_dh)
		DH_free(m_dh);

	m_ci_elements.init();
}

int eDVBCICcSession::receivedAPDU(const unsigned char *tag, const void *data, int len)
{
	eTraceNoNewLineStart("[CI CC] SESSION(%d)/CC %02x %02x %02x: ", session_nb, tag[0], tag[1], tag[2]);
	for (int i=0; i<len; i++)
		eTraceNoNewLine("%02x ", ((const unsigned char*)data)[i]);
	eTraceNoNewLine("\n");

	if ((tag[0] == 0x9f) && (tag[1] == 0x90))
	{
		switch (tag[2])
		{
			case 0x01: cc_open_req(); break;
			case 0x03: cc_data_req((const uint8_t *)data, len); break;
			case 0x05: cc_sync_req((const uint8_t *)data, len); break;
			case 0x07: cc_sac_data_req((const uint8_t *)data, len); break;
			case 0x09: cc_sac_sync_req((const uint8_t *)data, len); break;
			default:
				eWarning("[CI RCC] unknown APDU tag %02x", tag[2]); break;
		}
	}

	return 0;
}

int eDVBCICcSession::doAction()
{
	switch (state) {
	case stateStarted:
		break;
	default:
		eWarning("[CI CC] unknown state");
		break;
	}
	return 0;
}

void eDVBCICcSession::send(const unsigned char *tag, const void *data, int len)
{
	sendAPDU(tag, data, len);
}

void eDVBCICcSession::addProgram(uint16_t program_number, std::vector<uint16_t>& pids)
{
	eDebugNoNewLineStart("[CI CC] SESSION(%d)/ADD PROGRAM %04x: ", session_nb, program_number);
	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		eDebugNoNewLine("%02x ", *it);
	eDebugNoNewLine("\n");

	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		descrambler_set_pid(m_descrambler_fd, m_slot->getSlotID(), 1, *it);
}

void eDVBCICcSession::removeProgram(uint16_t program_number, std::vector<uint16_t>& pids)
{
	eDebugNoNewLineStart("[CI CC] SESSION(%d)/REMOVE PROGRAM %04x: ", session_nb, program_number);
	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		eDebugNoNewLine("%02x ", *it);
	eDebugNoNewLine("\n");

	for (std::vector<uint16_t>::iterator it = pids.begin(); it != pids.end(); ++it)
		descrambler_set_pid(m_descrambler_fd, m_slot->getSlotID(), 0, *it);
}

void eDVBCICcSession::cc_open_req()
{
	const uint8_t tag[3] = { 0x9f, 0x90, 0x02 };
	const uint8_t bitmap = 0x01;
	send(tag, &bitmap, 1);
}

void eDVBCICcSession::cc_data_req(const uint8_t *data, unsigned int len)
{
	uint8_t cc_data_cnf_tag[3] = { 0x9f, 0x90, 0x04 };
	uint8_t dest[BUFSIZ];
	int dt_nr;
	int id_bitmask;
	int answ_len;
	unsigned int rp = 0;

	if (len < 2)
	{
		eWarning("[CI RCC] too short data");
		return;
	}

	id_bitmask = data[rp++];

	dt_nr = data[rp++];
	rp += data_get_loop(&data[rp], len - rp, dt_nr);

	if (len < rp + 1)
		return;

	dt_nr = data[rp++];

	unsigned int dest_len = sizeof(dest);
	if (dest_len < 2)
	{
		eWarning("[CI RCC] not enough space");
		return;
	}

	dest[0] = id_bitmask;
	dest[1] = dt_nr;

	answ_len = data_req_loop(&dest[2], dest_len - 2, &data[rp], len - rp, dt_nr);
	if (answ_len <= 0)
	{
		eWarning("[CI RCC] can not get data");
		return;
	}

	answ_len += 2;

	send(cc_data_cnf_tag, dest, answ_len);
}

void eDVBCICcSession::cc_sync_req(const uint8_t *data, unsigned int len)
{
	const uint8_t tag[3] = { 0x9f, 0x90, 0x06 };
	const uint8_t status = 0x00;    /* OK */

	send(tag, &status, 1);
}

void eDVBCICcSession::cc_sac_data_req(const uint8_t *data, unsigned int len)
{
	const uint8_t data_cnf_tag[3] = { 0x9f, 0x90, 0x08 };
	uint8_t dest[BUFSIZ];
	uint8_t tmp[len];
	int id_bitmask, dt_nr;
	unsigned int serial;
	int answ_len;
	int pos = 0;
	unsigned int rp = 0;

	if (len < 10)
		return;

	eTraceNoNewLineStart("[CI RCC] cc_sac_data_req: ");
	traceHexdump(data, len);

	memcpy(tmp, data, 8);
	sac_crypt(&tmp[8], &data[8], len - 8, AES_DECRYPT);
	data = tmp;

	if (!sac_check_auth(data, len))
	{
		eWarning("[CI RCC] check_auth of message failed");
		return;
	}

	serial = UINT32(&data[rp], 4);
	//eDebug("%u\n", serial);

	/* skip serial & header */
	rp += 8;

	id_bitmask = data[rp++];

	/* handle data loop */
	dt_nr = data[rp++];
	rp += data_get_loop(&data[rp], len - rp, dt_nr);

	if (len < rp + 1)
	{
		eWarning("[CI RCC] check_auth of message too short");
		return;
	}

	dt_nr = data[rp++];

	/* create answer */
	unsigned int dest_len = sizeof(dest);

	if (dest_len < 10)
	{
		eWarning("[CI RCC] not enough space");
		return;
	}

	pos += BYTE32(&dest[pos], serial);
	pos += BYTE32(&dest[pos], 0x01000000);

	dest[pos++] = id_bitmask;
	dest[pos++] = dt_nr;    /* dt_nbr */

	answ_len = data_req_loop(&dest[pos], dest_len - 10, &data[rp], len - rp, dt_nr);
	if (answ_len <= 0)
	{
		eWarning("[CI RCC] can not get data");
		return;
	}
	pos += answ_len;

	cc_sac_send(data_cnf_tag, dest, pos);
}

void eDVBCICcSession::cc_sac_sync_req(const uint8_t *data, unsigned int len)
{
	const uint8_t sync_cnf_tag[3] = { 0x9f, 0x90, 0x10 };
	uint8_t dest[64];
	unsigned int serial;
	int pos = 0;

	eTraceNoNewLineStart("[CI RCC] cc_sac_sync_req: ");
	traceHexdump(data, len);

	serial = UINT32(data, 4);
	eTrace("[CI RCC] serial %u\n", serial);

	pos += BYTE32(&dest[pos], serial);
	pos += BYTE32(&dest[pos], 0x01000000);

	/* status OK */
	dest[pos++] = 0;

	cc_sac_send(sync_cnf_tag, dest, pos);
}

void eDVBCICcSession::cc_sac_send(const uint8_t *tag, uint8_t *data, unsigned int pos)
{
	if (pos < 8)
	{
		eWarning("[CI RCC] too short data");
		return;
	}

	pos += add_padding(&data[pos], pos - 8, 16);
	BYTE16(&data[6], pos - 8);      /* len in header */

	pos += sac_gen_auth(&data[pos], data, pos);
	sac_crypt(&data[8], &data[8], pos - 8, AES_ENCRYPT);

	send(tag, data, pos);

	return;
}

int eDVBCICcSession::data_get_loop(const uint8_t *data, unsigned int datalen, unsigned int items)
{
	unsigned int i;
	int dt_id, dt_len;
	unsigned int pos = 0;

	for (i = 0; i < items; i++)
	{
		if (pos + 3 > datalen)
			return 0;

		dt_id = data[pos++];
		dt_len = data[pos++] << 8;
		dt_len |= data[pos++];

		if (pos + dt_len > datalen)
			return 0;

		eTraceNoNewLineStart("[CI RCC] set element %d: ", dt_id);
		traceHexdump(&data[pos], dt_len);

		m_ci_elements.set(dt_id, &data[pos], dt_len);

		data_get_handle_new(dt_id);

		pos += dt_len;
	}

	return pos;
}

int eDVBCICcSession::data_req_loop(uint8_t *dest, unsigned int dest_len, const uint8_t *data, unsigned int data_len, unsigned int items)
{
	int dt_id;
	unsigned int i;
	int pos = 0;
	unsigned int len;

	if (items > data_len)
		return -1;

	for (i = 0; i < items; i++)
	{
		dt_id = data[i];
		data_req_handle_new(dt_id);    /* check if there is any action needed before we answer */

		len = m_ci_elements.get_buf(NULL, dt_id);
		if ((len + 3) > dest_len)
		{
			eWarning("[CI RCC] req element %d: not enough space", dt_id);
			return -1;
		}

		len = m_ci_elements.get_req(dest, dt_id);
		if (len > 0)
		{
			eTraceNoNewLineStart("[CI RCC] req element %d: ", dt_id);
			traceHexdump(&dest[3], len - 3);
		}

		pos += len;
		dest += len;
		dest_len -= len;
	}

	return pos;
}

int eDVBCICcSession::data_get_handle_new(unsigned int id)
{
	switch (id)
	{
		case CICAM_BRAND_CERT:
		case DHPM:
		case CICAM_DEV_CERT:
//		case CICAM_ID:
		case SIGNATURE_B:
			if (check_ci_certificates())
				break;

			check_dh_challenge();
			break;

		case AUTH_NONCE:
			restart_dh_challenge();
			break;

		case NS_MODULE:
			generate_ns_host();
			generate_key_seed();
			generate_SAK_SEK();
			break;

		case CICAM_ID:
		case KP:
		case KEY_REGISTER:
			check_new_key();
			break;

		case PROGRAM_NUMBER:
		case URI_MESSAGE:
			generate_uri_confirm();
			break;

		default:
			eWarning("[CI RCC] unhandled id %u", id);
			break;
	}

	return 0;
}

int eDVBCICcSession::data_req_handle_new(unsigned int id)
{
	switch (id)
	{
		case 22:
		{
			uint8_t akh[32], host_id[8];

			memset(akh, 0, sizeof(akh));

			if (m_akh_index != 5)
			{
				if (!get_authdata(host_id, m_dhsk, akh, m_slot->getSlotID(), m_akh_index++))
					m_akh_index = 5;

				if (!m_ci_elements.set(AKH, akh, 32))
					eWarning("[CI RCC] can not set AKH in elements");

				if (!m_ci_elements.set(HOST_ID, host_id, 8))
					eWarning("[CI RCC] can not set host_id in elements");
			}
			break;
		}
		default:
			break;
	}

	return 0;
}

int eDVBCICcSession::generate_akh()
{
	uint8_t akh[32];
	SHA256_CTX sha;

	SHA256_Init(&sha);
	SHA256_Update(&sha, m_ci_elements.get_ptr(CICAM_ID), m_ci_elements.get_buf(NULL, CICAM_ID));
	SHA256_Update(&sha, m_ci_elements.get_ptr(HOST_ID), m_ci_elements.get_buf(NULL, HOST_ID));
	SHA256_Update(&sha, m_dhsk, 256);
	SHA256_Final(akh, &sha);

	m_ci_elements.set(AKH, akh, sizeof(akh));

	return 0;
}

int eDVBCICcSession::compute_dh_key()
{
	int len = DH_size(m_dh);
	if (len > 256)
	{
		eWarning("[CI RCC] too long shared key");
		return -1;
	}

	BIGNUM *bn_in = BN_bin2bn(m_ci_elements.get_ptr(DHPM), 256, NULL);

#if 0
	// verify DHPM
	BN_CTX *ctx = BN_CTX_new();
	BIGNUM *out = BN_new();

	if (BN_cmp(BN_value_one(), bn_in) >= 0)
		eWarning("[CI RCC] DHPM <= 1!!!");

	if (BN_cmp(bn_in, m_dh->p) >= 0)
		eWarning("[CI RCC] DHPM >= dh_p!!!");

	BN_mod_exp(out, bn_in, m_dh->q, m_dh->p, ctx);
	if (BN_cmp(out, BN_value_one()) != 0)
		eWarning("[CI RCC] DHPM ^ dh_q mod dh_p != 1!!!");

	BN_free(out);
	BN_CTX_free(ctx);
#endif

	int codes = 0;
	int ok = DH_check_pub_key(m_dh, bn_in, &codes);
	if (ok == 0)
		eDebug("[CI RCC] check_pub_key failed");
	if (codes & DH_CHECK_PUBKEY_TOO_SMALL)
		eDebug("[CI RCC] too small public key");
	if (codes & DH_CHECK_PUBKEY_TOO_LARGE)
		eDebug("[CI RCC] too large public key");

	int gap = 256 - len;
	memset(m_dhsk, 0, gap);
	DH_compute_key(m_dhsk + gap, bn_in, m_dh);

	BN_free(bn_in);

	return 0;
}

bool eDVBCICcSession::check_dh_challenge()
{
	if (!m_ci_elements.valid(AUTH_NONCE))
		return false;

	if (!m_ci_elements.valid(CICAM_ID))
		return false;

	if (!m_ci_elements.valid(DHPM))
		return false;

	if (!m_ci_elements.valid(SIGNATURE_B))
		return false;

	compute_dh_key();
	generate_akh();

	m_akh_index = 5;

	eDebug("[CI RCC] writing...");
	write_authdata(m_slot->getSlotID(), m_ci_elements.get_ptr(HOST_ID), m_dhsk, m_ci_elements.get_ptr(AKH));

	return true;
}

int eDVBCICcSession::generate_dh_key()
{
	uint8_t dhph[256];
	int len;
	unsigned int gap;
	BIGNUM *p, *g , *q;
	const BIGNUM *pub_key;

	m_dh = DH_new();

	p = BN_bin2bn(m_dh_p, sizeof(m_dh_p), 0);
	g = BN_bin2bn(m_dh_g, sizeof(m_dh_g), 0);
	q = BN_bin2bn(m_dh_q, sizeof(m_dh_q), 0);
	DH_set0_pqg(m_dh, p, q, g);
	DH_set_flags(m_dh, DH_FLAG_NO_EXP_CONSTTIME);

	DH_generate_key(m_dh);

	DH_get0_key(m_dh, &pub_key, NULL);
	len = BN_num_bytes(pub_key);
	if (len > 256)
	{
		eWarning("[CI RCC] too long public key");
		return -1;
	}

#if 0
	// verify DHPH
	BN_CTX *ctx = BN_CTX_new();
	BIGNUM *out = BN_new();

	if (BN_cmp(BN_value_one(), m_dh->pub_key) >= 0)
		eWarning("[CI RCC] DHPH <= 1!!!");
	if (BN_cmp(m_dh->pub_key, m_dh->p) >= 0)
		eWarning("[CI RCC] DHPH >= dh_p!!!");
	BN_mod_exp(out, m_dh->pub_key, m_dh->q, m_dh->p, ctx);
	if (BN_cmp(out, BN_value_one()) != 0)
		eWarning("[CI RCC] DHPH ^ dh_q mod dh_p != 1!!!");

	BN_free(out);
	BN_CTX_free(ctx);
#endif

	gap = 256 - len;
	memset(dhph, 0, gap);
	BN_bn2bin(pub_key, &dhph[gap]);

	m_ci_elements.set(DHPH, dhph, sizeof(dhph));

	return 0;
}

int eDVBCICcSession::generate_sign_A()
{
	unsigned char dest[302];
	uint8_t hash[20];
	unsigned char dbuf[256];
	unsigned char sign_A[256];

	if (!m_ci_elements.valid(AUTH_NONCE))
		return -1;

	if (!m_ci_elements.valid(DHPH))
		return -1;

	dest[0x00] = 0x00; /* version */
	dest[0x01] = 0x00;
	dest[0x02] = 0x08; /* len (bits) */
	dest[0x03] = 0x01; /* version data */

	dest[0x04] = 0x01; /* msg_label */
	dest[0x05] = 0x00;
	dest[0x06] = 0x08; /* len (bits) */
	dest[0x07] = 0x02; /* message data */

	dest[0x08] = 0x02; /* auth_nonce */
	dest[0x09] = 0x01;
	dest[0x0a] = 0x00; /* len (bits) */
	memcpy(&dest[0x0b], m_ci_elements.get_ptr(AUTH_NONCE), 32);

	dest[0x2b] = 0x04; /* DHPH */
	dest[0x2c] = 0x08;
	dest[0x2d] = 0x00; /* len (bits) */
	memcpy(&dest[0x2e], m_ci_elements.get_ptr(DHPH), 256);

	SHA1(dest, 0x12e, hash);

	m_rsa_device_key = rsa_privatekey_open("/etc/ciplus/device.pem");
	if (!m_rsa_device_key)
	{
		eWarning("[CI RCC] can not read private key");
		return -1;
	}

	RSA_padding_add_PKCS1_PSS(m_rsa_device_key, dbuf, hash, EVP_sha1(), 20);
	RSA_private_encrypt(sizeof(dbuf), dbuf, sign_A, m_rsa_device_key, RSA_NO_PADDING);

	m_ci_elements.set(SIGNATURE_A, sign_A, sizeof(sign_A));

	return 0;
}

int eDVBCICcSession::restart_dh_challenge()
{
	if (!m_ci_elements.valid(AUTH_NONCE))
		return -1;

	//eDebug("[CI RCC] rechecking...");

	m_root_ca_store = X509_STORE_new();
	if (!m_root_ca_store)
	{
		eWarning("[CI RCC] can not create root_ca");
		return -1;
	}

	if (X509_STORE_load_locations(m_root_ca_store, "/etc/ciplus/root.pem", NULL) != 1)
	{
		eWarning("[CI RCC] can not load root_ca");
		return -1;
	}

	m_cust_cert = certificate_load_and_check(m_root_ca_store, "/etc/ciplus/customer.pem");
	m_device_cert = certificate_load_and_check(m_root_ca_store, "/etc/ciplus/device.pem");

	if (!m_cust_cert || !m_device_cert)
	{
		eWarning("[CI RCC] can not check loader certificates");
		return -1;
	}

	if (!ci_element_set_certificate(HOST_BRAND_CERT, m_cust_cert))
		eWarning("[CI RCC] can not store brand certificate");

	if (!ci_element_set_certificate(HOST_DEV_CERT, m_device_cert))
		eWarning("[CI RCC] can not store device certificate");

	if (!ci_element_set_hostid_from_certificate(HOST_ID, m_device_cert))
		eWarning("[CI RCC] can not store HOST_ID");

	m_ci_elements.invalidate(CICAM_ID);
	m_ci_elements.invalidate(DHPM);
	m_ci_elements.invalidate(SIGNATURE_B);
	m_ci_elements.invalidate(AKH);

	generate_dh_key();
	generate_sign_A();

	return 0;
}

int eDVBCICcSession::generate_uri_confirm()
{
	SHA256_CTX sha;
	uint8_t uck[32];
	uint8_t uri_confirm[32];

	//eDebug("[CI RCC] uri_confirm...");

	// UCK
	SHA256_Init(&sha);
	SHA256_Update(&sha, m_sak, 16);
	SHA256_Final(uck, &sha);

	// uri_confirm
	SHA256_Init(&sha);
	SHA256_Update(&sha, m_ci_elements.get_ptr(URI_MESSAGE), m_ci_elements.get_buf(NULL, URI_MESSAGE));
	SHA256_Update(&sha, uck, 32);
	SHA256_Final(uri_confirm, &sha);

	m_ci_elements.set(URI_CONFIRM, uri_confirm, 32);

	return 0;
}

void eDVBCICcSession::check_new_key()
{
	AES_KEY aes_ctx;
	uint8_t dec[32];
	uint8_t *kp;
	uint8_t slot;
	unsigned int i;

	if (!m_ci_elements.valid(KP))
		return;

	if (!m_ci_elements.valid(KEY_REGISTER))
		return;

	//eDebug("[CI RCC] key checking...");

	kp = m_ci_elements.get_ptr(KP);
	m_ci_elements.get_buf(&slot, KEY_REGISTER);

	AES_set_encrypt_key(m_s_key, 128, &aes_ctx);
	for (i = 0; i < 32; i += 16)
		AES_ecb_encrypt(&kp[i], &dec[i], &aes_ctx, 1);

	for (i = 0; i < 32; i++)
		dec[i] ^= kp[i];

	if (slot != 0 && slot != 1)
		slot = 1;

	descrambler_set_key(m_descrambler_fd, m_slot->getSlotID(), slot, dec);

	m_ci_elements.invalidate(KP);
	m_ci_elements.invalidate(KEY_REGISTER);
}

void eDVBCICcSession::generate_key_seed()
{
	SHA256_CTX sha;

	SHA256_Init(&sha);
	SHA256_Update(&sha, &m_dhsk[240], 16);
	SHA256_Update(&sha, m_ci_elements.get_ptr(AKH), m_ci_elements.get_buf(NULL, AKH));
	SHA256_Update(&sha, m_ci_elements.get_ptr(NS_HOST), m_ci_elements.get_buf(NULL, NS_HOST));
	SHA256_Update(&sha, m_ci_elements.get_ptr(NS_MODULE), m_ci_elements.get_buf(NULL, NS_MODULE));
	SHA256_Final(m_ks_host, &sha);
}

void eDVBCICcSession::generate_ns_host()
{
	uint8_t buf[8];
	get_random(buf, sizeof(buf));
	m_ci_elements.set(NS_HOST, buf, sizeof(buf));
}

int eDVBCICcSession::generate_SAK_SEK()
{
	AES_KEY key;
	uint8_t dec[32];
	int i;

	AES_set_encrypt_key(m_key_data, 128, &key);

	for (i = 0; i < 2; i++)
		AES_ecb_encrypt(&m_ks_host[16 * i], &dec[16 * i], &key, 1);

	for (i = 0; i < 16; i++)
		m_sek[i] = m_ks_host[i] ^ dec[i];

	for (i = 0; i < 16; i++)
		m_sak[i] = m_ks_host[16 + i] ^ dec[16 + i];

	return 0;
}

bool eDVBCICcSession::sac_check_auth(const uint8_t *data, unsigned int len)
{
	struct aes_xcbc_mac_ctx ctx;
	uint8_t calced_signature[16];

	if (len < 16)
	{
		eWarning("[CI RCC] signature too short");
		return false;
	}

	aes_xcbc_mac_init(&ctx, m_sak);
	aes_xcbc_mac_process(&ctx, (uint8_t *)"\x04", 1); /* header len */
	aes_xcbc_mac_process(&ctx, data, len - 16);
	aes_xcbc_mac_done(&ctx, calced_signature);

	if (memcmp(&data[len - 16], calced_signature, 16))
	{
		eWarning("[CI RCC] signature wrong");
		return false;
	}

	//eDebug("[CI RCC] auth ok!");

	return true;
}

int eDVBCICcSession::sac_gen_auth(uint8_t *out, uint8_t *in, unsigned int len)
{
	struct aes_xcbc_mac_ctx ctx;

	aes_xcbc_mac_init(&ctx, m_sak);
	aes_xcbc_mac_process(&ctx, (uint8_t *)"\x04", 1); /* header len */
	aes_xcbc_mac_process(&ctx, in, len);
	aes_xcbc_mac_done(&ctx, out);

	return 16;
}

int eDVBCICcSession::sac_crypt(uint8_t *dst, const uint8_t *src, unsigned int len, int encrypt)
{
	AES_KEY key;
	uint8_t iv[16];
	memcpy(iv, m_iv, 16); // use copy as iv is changed by AES_cbc_encrypt

	if (encrypt)
		AES_set_encrypt_key(m_sek, 128, &key);
	else
		AES_set_decrypt_key(m_sek, 128, &key);

	AES_cbc_encrypt(src, dst, len, &key, iv, encrypt);

	return 0;
}

X509 *eDVBCICcSession::import_ci_certificates(unsigned int id)
{
	X509 *cert;

	if (!m_ci_elements.valid(id))
	{
		eWarning("[CI RCC] %u not valid", id);
		return NULL;
	}

	cert = certificate_import_and_check(m_root_ca_store, m_ci_elements.get_ptr(id), m_ci_elements.get_buf(NULL, id));
	if (!cert)
	{
		eWarning("[CI RCC] can not verify certificate %u", id);
		return NULL;
	}

	return cert;
}

int eDVBCICcSession::check_ci_certificates()
{
	if (!m_ci_elements.valid(CICAM_BRAND_CERT))
		return -1;

	if (!m_ci_elements.valid(CICAM_DEV_CERT))
		return -1;

	if ((m_ci_cust_cert = import_ci_certificates(CICAM_BRAND_CERT)) == NULL)
	{
		eWarning("[CI RCC] can not import CICAM brand certificate");
		return -1;
	}

	if ((m_ci_device_cert = import_ci_certificates(CICAM_DEV_CERT)) == NULL)
	{
		eWarning("[CI RCC] can not import CICAM device certificate");
		return -1;
	}

	if (!ci_element_set_hostid_from_certificate(CICAM_ID, m_ci_device_cert))
	{
		eWarning("[CI RCC] can not store CICAM_ID");
		return -1;
	}

	return 0;
}

bool eDVBCICcSession::ci_element_set_certificate(unsigned int id, X509 *cert)
{
	unsigned char *cert_der = NULL;
	int cert_len;

	cert_len = i2d_X509(cert, &cert_der);
	if (cert_len <= 0)
	{
		eWarning("[CI RCC] can not encode certificate");
		return false;
	}

	if (!m_ci_elements.set(id, cert_der, cert_len)) {
		eWarning("[CI RCC] can not store certificate id %u", id);
		return false;
	}

	OPENSSL_free(cert_der);

	return true;
}

bool eDVBCICcSession::ci_element_set_hostid_from_certificate(unsigned int id, X509 *cert)
{
	X509_NAME *subject;
	char hostid[16 + 1];
	uint8_t bin_hostid[8];

	if ((id != 5) && (id != 6))
	{
		eWarning("[CI RCC] wrong datatype_id %u for device id", id);
		return false;
	}

	subject = X509_get_subject_name(cert);
	X509_NAME_get_text_by_NID(subject, NID_commonName, hostid, sizeof(hostid));

	if (strlen(hostid) != 16)
	{
		eWarning("[CI RCC] bad device id");
		return false;
	}

	//eDebug("[CI RCC] DEVICE_ID: %s", hostid);

	str2bin(bin_hostid, hostid, 16);

	if (!m_ci_elements.set(id, bin_hostid, sizeof(bin_hostid)))
	{
		eWarning("[CI RCC] can not store device id %u", id);
		return false;
	}

	return true;
}
