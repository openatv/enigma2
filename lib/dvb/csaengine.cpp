#include <lib/dvb/csaengine.h>
#include <lib/base/eerror.h>
#include <dlfcn.h>
#include <string.h>
#include <time.h>

#define CSA_DEBUG 0
#if CSA_DEBUG
#define CSA_LOG(...) eDebug(__VA_ARGS__)
#else
#define CSA_LOG(...) do {} while (0)
#endif

#define BYTE_HEX(b) ((unsigned int)(b) & 0xFF)

DEFINE_REF(eDVBCSAEngine);

// Global API object
csa_dlopen_api g_csa_api = {
	0,      // handle
	false,  // tried
	false,  // available
	0, 0, 0, 0, 0
};

bool csa_load_library()
{
	// Already loaded successfully?
	if (g_csa_api.available)
		return true;

	// Already tried and failed?
	if (g_csa_api.tried)
		return false;

	g_csa_api.tried = true;

	const char *candidates[] = {
		"libdvbcsa.so.1",
		"libdvbcsa.so",
		0
	};

	const char *loaded_name = nullptr;

	for (int i = 0; candidates[i]; ++i)
	{
		g_csa_api.handle = dlopen(candidates[i], RTLD_NOW | RTLD_LOCAL);
		if (g_csa_api.handle)
		{
			loaded_name = candidates[i];
			break;
		}
	}

	if (!g_csa_api.handle)
	{
		eDebug("[eDVBCSAEngine] libdvbcsa not found, software CSA is disabled");
		return false;
	}

	// Resolve symbols
	g_csa_api.key_alloc   = (dvbcsa_bs_key_alloc_f)  dlsym(g_csa_api.handle, "dvbcsa_bs_key_alloc");
	g_csa_api.key_free    = (dvbcsa_bs_key_free_f)   dlsym(g_csa_api.handle, "dvbcsa_bs_key_free");
	g_csa_api.key_set_ecm = (dvbcsa_bs_key_set_ecm_f)dlsym(g_csa_api.handle, "dvbcsa_bs_key_set_ecm");
	g_csa_api.get_ecm_table = (dvbcsa_get_ecm_table_f)dlsym(g_csa_api.handle, "dvbcsa_get_ecm_table");
	g_csa_api.batch_size  = (dvbcsa_bs_batch_size_f) dlsym(g_csa_api.handle, "dvbcsa_bs_batch_size");
	g_csa_api.decrypt     = (dvbcsa_bs_decrypt_f)    dlsym(g_csa_api.handle, "dvbcsa_bs_decrypt");

	if (!g_csa_api.key_alloc   ||
		!g_csa_api.key_free    ||
		!g_csa_api.key_set_ecm ||
		!g_csa_api.batch_size  ||
		!g_csa_api.decrypt)
	{
		eWarning("[eDVBCSAEngine] %s loaded but missing required symbols, software CSA is disabled", loaded_name);
		dlclose(g_csa_api.handle);
		g_csa_api.handle    = 0;
		g_csa_api.available = false;
		return false;
	}

	g_csa_api.available = true;

	eDebug("[eDVBCSAEngine] %s successfully loaded, software CSA enabled", loaded_name);

	return true;
}

eDVBCSAEngine::eDVBCSAEngine()
	: m_key_even{nullptr, nullptr}
	, m_key_odd{nullptr, nullptr}
	, m_batch_size(0)
{
}

eDVBCSAEngine::~eDVBCSAEngine()
{
	if (g_csa_api.available && g_csa_api.key_free)
	{
		for (int i = 0; i < 2; ++i)
		{
			if (m_key_even[i])
			{
				g_csa_api.key_free(m_key_even[i]);
				m_key_even[i] = nullptr;
			}
			if (m_key_odd[i])
			{
				g_csa_api.key_free(m_key_odd[i]);
				m_key_odd[i] = nullptr;
			}
		}
	}
}

bool eDVBCSAEngine::init()
{
	if (!csa_load_library())
	{
		eWarning("[eDVBCSAEngine] init: csa_load_library failed");
		return false;
	}

	m_batch_size = g_csa_api.batch_size();

	for (int i = 0; i < 2; ++i)
	{
		m_key_even[i] = g_csa_api.key_alloc();
		m_key_odd[i] = g_csa_api.key_alloc();
		if (!m_key_even[i] || !m_key_odd[i])
		{
			eWarning("[eDVBCSAEngine] init: key_alloc failed");
			return false;
		}
	}

	// Pre-allocate batch arrays
	m_batch_even.resize(m_batch_size + 1);
	m_batch_odd.resize(m_batch_size + 1);

	eDebug("[eDVBCSAEngine] init: batch_size=%d", m_batch_size);

	return true;
}

int eDVBCSAEngine::getBatchSize()
{
	if (!g_csa_api.available || !g_csa_api.batch_size)
		return 0;
	return g_csa_api.batch_size();
}

std::string eDVBCSAEngine::getLibraryName()
{
	std::string path = getLibraryPath();
	if (path.empty())
		return "";

	// Extract filename from path
	size_t lastSlash = path.rfind('/');
	std::string filename = (lastSlash != std::string::npos) ? path.substr(lastSlash + 1) : path;

	// Remove everything from ".so"
	size_t soPos = filename.find(".so");
	if (soPos != std::string::npos)
	{
		return filename.substr(0, soPos);
	}

	return filename;
}

std::string eDVBCSAEngine::getLibraryPath()
{
	if (!g_csa_api.available || !g_csa_api.handle)
		return "";

	// Use dladdr to get the path of a symbol from the library
	Dl_info info;
	if (dladdr((void*)g_csa_api.key_alloc, &info) && info.dli_fname)
		return info.dli_fname;

	return "";
}

std::string eDVBCSAEngine::getLibraryVersion()
{
	std::string path = getLibraryPath();
	if (path.empty())
		return "";

	char resolved[PATH_MAX];
	if (!realpath(path.c_str(), resolved))
		return "";

	std::string full(resolved);
	std::string marker = ".so.";
	size_t pos = full.rfind(marker);
	if (pos != std::string::npos)
	{
		return full.substr(pos + marker.length());
	}

	return "";
}

void eDVBCSAEngine::setKey(int parity, uint8_t ecm_mode, const uint8_t* cw)
{
	if (!cw)
		return;
	if (!m_key_even[0] || !m_key_even[1] || !m_key_odd[0] || !m_key_odd[1])
		return;
	if (!g_csa_api.available || !g_csa_api.key_set_ecm)
		return;

	CSA_LOG("[eDVBCSAEngine] setKey: parity=%d ecm_mode=%u CW=%02X %02X %02X %02X %02X %02X %02X %02X",
			parity, ecm_mode,
			BYTE_HEX(cw[0]), BYTE_HEX(cw[1]), BYTE_HEX(cw[2]), BYTE_HEX(cw[3]),
			BYTE_HEX(cw[4]), BYTE_HEX(cw[5]), BYTE_HEX(cw[6]), BYTE_HEX(cw[7]));

	// Double-buffered key update: write to inactive slot, then swap index.
	// descramble() on the recorder thread reads the active slot via atomic index,
	// so it never sees a partially-written key schedule.
	if (parity == 0) // even
	{
		int active = m_key_even_idx.load(std::memory_order_relaxed); // S8417: only this thread writes it
		int inactive = 1 - active;
		g_csa_api.key_set_ecm(ecm_mode, cw, m_key_even[inactive]);
		m_key_even_idx.store(inactive, std::memory_order_release); // S8417: publishes key write above
		m_gen_even.fetch_add(1, std::memory_order_release); // S8417: publishes idx store above
		m_key_even_set.store(true, std::memory_order_release); // S8417: publishes idx store above
	}
	else // odd
	{
		int active = m_key_odd_idx.load(std::memory_order_relaxed); // S8417: only this thread writes it
		int inactive = 1 - active;
		g_csa_api.key_set_ecm(ecm_mode, cw, m_key_odd[inactive]);
		m_key_odd_idx.store(inactive, std::memory_order_release); // S8417: publishes key write above
		m_gen_odd.fetch_add(1, std::memory_order_release); // S8417: publishes idx store above
		m_key_odd_set.store(true, std::memory_order_release); // S8417: publishes idx store above
	}

	if (g_csa_api.get_ecm_table)
	{
		static uint8_t last_logged_table = 0xFF;
		uint8_t table_used = g_csa_api.get_ecm_table();
		if (table_used != last_logged_table)
		{
			eDebug("[eDVBCSAEngine] libdvbcsa using table 0x%02X", table_used);
			last_logged_table = table_used;
		}
	}
}

void eDVBCSAEngine::clearKeys()
{
	m_key_even_set = false;
	m_key_odd_set = false;
	m_last_parity = -1;
	m_bound_gen[0] = 0;
	m_bound_gen[1] = 0;
	m_prev_run_gen[0] = 0;
	m_prev_run_gen[1] = 0;
	m_run_suspect = false;
	m_probe_armed = false;
}

/* Try a key on one payload: does a PES start code come out? Only valid where
 * the payload unit start indicator is set. */
bool eDVBCSAEngine::probeKey(const dvbcsa_bs_key_t* key, const unsigned char* pkt, int offset) const
{
	if (!key || offset >= 188 || 188 - offset < 4)
		return false;

	unsigned char scratch[188];
	const int plen = 188 - offset;
	memcpy(scratch, pkt + offset, plen);

	dvbcsa_bs_batch_s one[2];
	one[0].data = scratch;
	one[0].len = plen;
	one[1].data = nullptr;
	g_csa_api.decrypt(key, one, 184);

	return scratch[0] == 0x00 && scratch[1] == 0x00 && scratch[2] == 0x01;
}

// TS Packet Helpers
bool eDVBCSAEngine::isPacketValid(const unsigned char* pkt)
{
	return pkt[0] == 0x47;
}

unsigned char eDVBCSAEngine::getScrambledBits(const unsigned char* pkt)
{
	return pkt[3] >> 6;
}

int eDVBCSAEngine::getPayloadOffset(const unsigned char* pkt)
{
	unsigned char adapt_field = (pkt[3] & ~0xDF) >> 5;

	if (adapt_field)
		return 4 + 1 + pkt[4];    // header (4) + length byte + adaptation field
	else
		return 4;                 // header only
}

void eDVBCSAEngine::clearTSC(unsigned char* pkt)
{
	if (pkt)
		pkt[3] &= 0x3F;
}

void eDVBCSAEngine::setNullPacket(unsigned char* pkt)
{
	// PID 0x1FFF, the decoder ignores null packets
	clearTSC(pkt);
	pkt[1] = 0x1F;
	pkt[2] = 0xFF;
}

void eDVBCSAEngine::logBadPacket(const char* reason, const unsigned char* pkt, int offset, int len)
{
	++m_bad_packets;
	if (m_bad_packets > 20 && m_bad_packets % 500)
		return;
	if (len - offset >= 5)
		eWarning("[eDVBCSAEngine] bad packet #%u (%s): offset=%d len=%d tei=%d hdr=%02X %02X %02X %02X %02X", m_bad_packets, reason, offset, len,
			(pkt[1] & 0x80) ? 1 : 0, BYTE_HEX(pkt[0]), BYTE_HEX(pkt[1]), BYTE_HEX(pkt[2]), BYTE_HEX(pkt[3]), BYTE_HEX(pkt[4]));
	else
		eWarning("[eDVBCSAEngine] bad packet #%u (%s): offset=%d len=%d", m_bad_packets, reason, offset, len);
}

// Descrambling
/* Slot for generation "want": current is now & 1, previous the other. Older
 * is overwritten, so return nothing and let the packets be nulled. */
static dvbcsa_bs_key_t* keyForGeneration(dvbcsa_bs_key_t* const slots[2], uint32_t now, uint32_t want)
{
	if (!now)
		return nullptr;
	if (!want || want == now)
		return slots[now & 1];
	if (now - want == 1)
		return slots[want & 1];
	return nullptr;
}

void eDVBCSAEngine::descramble(unsigned char* packets, int len)
{
	if (!packets || len <= 0)
		return;
	if (m_batch_size <= 0)
		return;
	if (!g_csa_api.available || !g_csa_api.decrypt)
		return;
	if (m_batch_even.empty() || m_batch_odd.empty())
		return;

	// setKey() may swap slots from the CWHandler thread at any time.
	const bool even_set = m_key_even_set.load(std::memory_order_acquire); // S8417: pairs with release in setKey()
	const bool odd_set = m_key_odd_set.load(std::memory_order_acquire); // S8417: pairs with release in setKey()
	const uint32_t gen_even_now = m_gen_even.load(std::memory_order_acquire); // S8417: pairs with release in setKey()
	const uint32_t gen_odd_now = m_gen_odd.load(std::memory_order_acquire); // S8417: pairs with release in setKey()

	/* A suspect run bound the same generation as the previous run of its
	 * parity, so its own CW was missing: take a newer key once one appears. */
	if (m_run_suspect && m_last_parity >= 0)
	{
		const uint32_t now = m_last_parity ? gen_odd_now : gen_even_now;
		if (now != m_bound_gen[m_last_parity])
		{
			m_bound_gen[m_last_parity] = now;
			m_prev_run_gen[m_last_parity] = now;
			m_probe_armed = true;  // the new key still has to prove itself
		}
	}

	const dvbcsa_bs_key_t* key_even = even_set ? keyForGeneration(m_key_even, gen_even_now, m_bound_gen[0]) : nullptr;
	const dvbcsa_bs_key_t* key_odd = odd_set ? keyForGeneration(m_key_odd, gen_odd_now, m_bound_gen[1]) : nullptr;

	int i        = 0;
	int even_cnt = 0;
	int odd_cnt  = 0;

	// Use pre-allocated member vectors
	dvbcsa_bs_batch_s* pcks_even = m_batch_even.data();
	dvbcsa_bs_batch_s* pcks_odd = m_batch_odd.data();

	CSA_LOG("[eDVBCSAEngine] descramble: len=%d batch_size=%d", len, m_batch_size);

	while (i < len)
	{
		unsigned char *pkt = packets + i;

		const bool sync = isPacketValid(pkt);
		if (!sync || len - i < 188)
		{
			logBadPacket(sync ? "partial packet" : "sync loss", pkt, i, len);
			break;  // Still flush the batches collected so far
		}

		unsigned char scrambled = getScrambledBits(pkt);
		if (scrambled < 2) // clear or reserved
		{
			i += 188;
			continue;
		}

		const bool even = (scrambled == 2);
		const dvbcsa_bs_key_t* key = even ? key_even : key_odd;
		int offset = getPayloadOffset(pkt);

		/* New parity run, so a new crypto period: bind the newest key for
		 * that parity and hold it. Flush first, or a rebind would reach
		 * packets collected for the old key. */
		const int parity = even ? 0 : 1;
		if (parity != m_last_parity)
		{
			m_last_parity = parity;
			const uint32_t gen_now = even ? gen_even_now : gen_odd_now;
			/* Same generation twice: this period's CW is missing, unless the
			 * provider repeats the key - the check below tells apart. */
			m_run_suspect = m_prev_run_gen[parity] && gen_now == m_prev_run_gen[parity];
			m_prev_run_gen[parity] = gen_now;
			m_bound_gen[parity] = gen_now;

			int& cnt = even ? even_cnt : odd_cnt;
			dvbcsa_bs_batch_s* batch = even ? pcks_even : pcks_odd;
			const dvbcsa_bs_key_t*& bound = even ? key_even : key_odd;
			if (cnt > 0 && bound)
			{
				batch[cnt].data = nullptr;
				g_csa_api.decrypt(bound, batch, 184);
				cnt = 0;
			}

			const bool parity_set = even ? even_set : odd_set;
			dvbcsa_bs_key_t* const *slots = even ? m_key_even : m_key_odd;
			bound = parity_set ? keyForGeneration(slots, gen_now, m_bound_gen[parity]) : nullptr;
			key = bound;

			/* Bound key is two generations old and gone: null the run. */
			if (parity_set && !bound)
			{
				++m_expired_keys;
				if (m_expired_keys <= 20 || !(m_expired_keys % 500))
					eWarning("[eDVBCSAEngine] expired key #%u: parity=%d wants generation %u, now %u - nulling the period",
						m_expired_keys, parity, m_bound_gen[parity],
						even ? gen_even_now : gen_odd_now);
			}

			m_probe_armed = true;
		}

		/* Verify the bound key once, on a payload that must start with a PES
		 * start code. */
		if (m_probe_armed && key && (pkt[1] & 0x40) && (pkt[3] & 0x10) && offset < 188)
		{
			m_probe_armed = false;
			if (probeKey(key, pkt, offset))
				m_run_suspect = false;
			else if (!m_run_suspect)
			{
				/* In time, from the ECM, and still does not decrypt. */
				++m_dead_keys;
				if (m_dead_keys <= 20 || !(m_dead_keys % 500))
					eWarning("[eDVBCSAEngine] dead key #%u: parity=%d generation=%u does not decrypt its period",
						m_dead_keys, parity, m_bound_gen[parity]);
			}
		}

		if (!(pkt[3] & 0x10))
		{
			// Adaptation field only, nothing to descramble
			clearTSC(pkt);
		}
		else if (!key)
		{
			// No key: convert to null packet - no glitches
			setNullPacket(pkt);
		}
		else if (offset >= 188)
		{
			// Never pass an invalid payload length to libdvbcsa, it aborts on it
			logBadPacket("adaptation field too long", pkt, i, len);
			setNullPacket(pkt);
		}
		else
		{
			// Key available: descramble and clear TSC
			clearTSC(pkt);
			dvbcsa_bs_batch_s* batch = even ? pcks_even : pcks_odd;
			int& cnt = even ? even_cnt : odd_cnt;
			batch[cnt].data = pkt + offset;
			batch[cnt].len  = 188 - offset;
			cnt++;
		}

		// flush even batch
		if (even_cnt == m_batch_size)
		{
			pcks_even[even_cnt].data = NULL;
			g_csa_api.decrypt(key_even, pcks_even, 184);
			CSA_LOG("[eDVBCSAEngine] decrypt even batch (%d)", m_batch_size);
			even_cnt = 0;
		}

		// flush odd batch
		if (odd_cnt == m_batch_size)
		{
			pcks_odd[odd_cnt].data = NULL;
			g_csa_api.decrypt(key_odd, pcks_odd, 184);
			CSA_LOG("[eDVBCSAEngine] decrypt odd batch (%d)", m_batch_size);
			odd_cnt = 0;
		}

		i += 188;
	}

	// flush remaining even
	if (even_cnt > 0)
	{
		pcks_even[even_cnt].data = NULL;
		g_csa_api.decrypt(key_even, pcks_even, 184);
		CSA_LOG("[eDVBCSAEngine] decrypt remaining even packets=%d", even_cnt);
	}

	// flush remaining odd
	if (odd_cnt > 0)
	{
		pcks_odd[odd_cnt].data = NULL;
		g_csa_api.decrypt(key_odd, pcks_odd, 184);
		CSA_LOG("[eDVBCSAEngine] decrypt remaining odd packets=%d", odd_cnt);
	}

	CSA_LOG("[eDVBCSAEngine] descramble done");
}
