#include <lib/dvb/csaengine.h>
#include <lib/base/eerror.h>
#include <dlfcn.h>

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
		eWarning("[CSAEngine] libdvbcsa not found (dlopen failed)");
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
		eWarning("[CSAEngine] %s loaded but missing required symbols", loaded_name);
		dlclose(g_csa_api.handle);
		g_csa_api.handle    = 0;
		g_csa_api.available = false;
		return false;
	}

	g_csa_api.available = true;

	eDebug("[CSAEngine] %s successfully loaded, software CSA enabled", loaded_name);

	return true;
}

eDVBCSAEngine::eDVBCSAEngine()
	: m_key_even(nullptr)
	, m_key_odd(nullptr)
	, m_batch_size(0)
{
}

eDVBCSAEngine::~eDVBCSAEngine()
{
	if (g_csa_api.available && g_csa_api.key_free)
	{
		if (m_key_even)
		{
			g_csa_api.key_free(m_key_even);
			m_key_even = nullptr;
		}
		if (m_key_odd)
		{
			g_csa_api.key_free(m_key_odd);
			m_key_odd = nullptr;
		}
	}
}

bool eDVBCSAEngine::init()
{
	if (!csa_load_library())
	{
		eWarning("[CSAEngine] init: csa_load_library failed");
		return false;
	}

	m_batch_size = g_csa_api.batch_size();
	m_key_even = g_csa_api.key_alloc();
	m_key_odd = g_csa_api.key_alloc();

	if (!m_key_even || !m_key_odd)
	{
		eWarning("[CSAEngine] init: key_alloc failed");
		return false;
	}

	// Pre-allocate batch arrays
	m_batch_even.resize(m_batch_size + 1);
	m_batch_odd.resize(m_batch_size + 1);

	eDebug("[CSAEngine] init: batch_size=%d", m_batch_size);

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
	if (!m_key_even || !m_key_odd)
		return;
	if (!g_csa_api.available || !g_csa_api.key_set_ecm)
		return;

	CSA_LOG("[CSAEngine] setKey: parity=%d ecm_mode=%u CW=%02X %02X %02X %02X %02X %02X %02X %02X",
			parity, ecm_mode,
			BYTE_HEX(cw[0]), BYTE_HEX(cw[1]), BYTE_HEX(cw[2]), BYTE_HEX(cw[3]),
			BYTE_HEX(cw[4]), BYTE_HEX(cw[5]), BYTE_HEX(cw[6]), BYTE_HEX(cw[7]));

	// Lock-free key update
	if (parity == 0) // even
	{
		g_csa_api.key_set_ecm(ecm_mode, cw, m_key_even);
		m_key_even_set = true;
	}
	else // odd
	{
		g_csa_api.key_set_ecm(ecm_mode, cw, m_key_odd);
		m_key_odd_set = true;
	}

	if (g_csa_api.get_ecm_table)
	{
		static uint8_t last_logged_table = 0xFF;
		uint8_t table_used = g_csa_api.get_ecm_table();
		if (table_used != last_logged_table)
		{
			eDebug("[CSAEngine] libdvbcsa using table 0x%02X", table_used);
			last_logged_table = table_used;
		}
	}
}

void eDVBCSAEngine::clearKeys()
{
	m_key_even_set = false;
	m_key_odd_set = false;
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

unsigned char eDVBCSAEngine::getPayloadOffset(const unsigned char* pkt)
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

// Descrambling
void eDVBCSAEngine::descramble(unsigned char* packets, int len)
{
	if (!packets || len <= 0)
		return;
	if (!m_key_even || !m_key_odd || m_batch_size <= 0)
		return;
	if (!g_csa_api.available || !g_csa_api.decrypt)
		return;
	if (m_batch_even.empty() || m_batch_odd.empty())
		return;

	int i        = 0;
	int even_cnt = 0;
	int odd_cnt  = 0;

	// Use pre-allocated member vectors
	dvbcsa_bs_batch_s* pcks_even = m_batch_even.data();
	dvbcsa_bs_batch_s* pcks_odd = m_batch_odd.data();

	CSA_LOG("[CSAEngine] descramble: len=%d batch_size=%d", len, m_batch_size);

	const bool even_set = m_key_even_set;
	const bool odd_set = m_key_odd_set;

	while (i < len)
	{
		unsigned char *pkt = packets + i;

		if (!isPacketValid(pkt))
		{
			CSA_LOG("[CSAEngine] decrypt sync error at offset=%d", i);
			return;
		}

		unsigned char offset    = getPayloadOffset(pkt);
		unsigned char scrambled = getScrambledBits(pkt);

		if (scrambled == 2) // even
		{
			if (even_set)
			{
				// Key available: descramble and clear TSC
				clearTSC(pkt);
				pcks_even[even_cnt].data = pkt + offset;
				pcks_even[even_cnt].len  = 188 - offset;
				even_cnt++;
			}
			else
			{
				// No key: convert to null packet (PID 0x1FFF), Decoder will ignore null packets - no glitches
				clearTSC(pkt);
				pkt[1] = 0x1F;
				pkt[2] = 0xFF;
			}
		}
		else if (scrambled == 3) // odd
		{
			if (odd_set)
			{
				// Key available: descramble and clear TSC
				clearTSC(pkt);
				pcks_odd[odd_cnt].data = pkt + offset;
				pcks_odd[odd_cnt].len  = 188 - offset;
				odd_cnt++;
			}
			else
			{
				// No key: convert to null packet (PID 0x1FFF), Decoder will ignore null packets - no glitches
				clearTSC(pkt);
				pkt[1] = 0x1F;
				pkt[2] = 0xFF;
			}
		}

		// flush even batch
		if (even_cnt == m_batch_size)
		{
			pcks_even[even_cnt].data = NULL;
			if (even_set)
				g_csa_api.decrypt(m_key_even, pcks_even, 184);
			CSA_LOG("[CSAEngine] decrypt even batch (%d)", m_batch_size);
			even_cnt = 0;
		}

		// flush odd batch
		if (odd_cnt == m_batch_size)
		{
			pcks_odd[odd_cnt].data = NULL;
			if (odd_set)
				g_csa_api.decrypt(m_key_odd, pcks_odd, 184);
			CSA_LOG("[CSAEngine] decrypt odd batch (%d)", m_batch_size);
			odd_cnt = 0;
		}

		i += 188;
	}

	// flush remaining even
	if (even_cnt > 0)
	{
		pcks_even[even_cnt].data = NULL;
		if (even_set)
			g_csa_api.decrypt(m_key_even, pcks_even, 184);
		CSA_LOG("[CSAEngine] decrypt remaining even packets=%d", even_cnt);
	}

	// flush remaining odd
	if (odd_cnt > 0)
	{
		pcks_odd[odd_cnt].data = NULL;
		if (odd_set)
			g_csa_api.decrypt(m_key_odd, pcks_odd, 184);
		CSA_LOG("[CSAEngine] decrypt remaining odd packets=%d", odd_cnt);
	}

	CSA_LOG("[CSAEngine] descramble done");
}
