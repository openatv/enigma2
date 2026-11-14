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
	: m_batch_size(0)
{
}

eDVBCSAEngine::~eDVBCSAEngine()
{
	if (g_csa_api.available && g_csa_api.key_free)
	{
		for (int p = 0; p < 2; ++p)
		{
			if (m_parity[p].key)
			{
				g_csa_api.key_free(m_parity[p].key);
				m_parity[p].key = nullptr;
			}
			if (m_parity[p].waiting)
			{
				g_csa_api.key_free(m_parity[p].waiting);
				m_parity[p].waiting = nullptr;
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

	for (int p = 0; p < 2; ++p)
	{
		m_parity[p].key = g_csa_api.key_alloc();
		m_parity[p].waiting = g_csa_api.key_alloc();
		if (!m_parity[p].key || !m_parity[p].waiting)
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
	if (!g_csa_api.available || !g_csa_api.key_set_ecm)
		return;

	const int par = parity ? 1 : 0;
	ParityState &st = m_parity[par];
	if (!st.key || !st.waiting)
		return;

	// an all-zero half is no word for this parity
	if (!memcmp(cw, "\x00\x00\x00\x00\x00\x00\x00\x00", 8))
		return;

	CSA_LOG("[eDVBCSAEngine] setKey: parity=%d ecm_mode=%u CW=%02X %02X %02X %02X %02X %02X %02X %02X",
			parity, ecm_mode,
			BYTE_HEX(cw[0]), BYTE_HEX(cw[1]), BYTE_HEX(cw[2]), BYTE_HEX(cw[3]),
			BYTE_HEX(cw[4]), BYTE_HEX(cw[5]), BYTE_HEX(cw[6]), BYTE_HEX(cw[7]));

	bool missing = false;

	{
		std::lock_guard<std::mutex> lock(m_lock);

		// every ECM repeats the word in force; the table is part of the key
		if (st.has_waiting)
		{
			if (st.mode_waiting == ecm_mode && !memcmp(st.cw_waiting, cw, 8))
			{
				CSA_LOG("[eDVBCSAEngine] setKey: parity=%d repeats the word already waiting", parity);
				return;
			}
		}
		else if (st.live && st.mode == ecm_mode && !memcmp(st.cw, cw, 8))
		{
			CSA_LOG("[eDVBCSAEngine] setKey: parity=%d repeats the word in force", parity);
			return;
		}

		/* The word the packets coming out still need stays, so a new one waits. */
		if (m_cur_parity == par && st.live && !st.run_dead)
		{
			g_csa_api.key_set_ecm(ecm_mode, cw, st.waiting);
			memcpy(st.cw_waiting, cw, 8);
			st.mode_waiting = ecm_mode;
			st.has_waiting = true;
		}
		else
		{
			g_csa_api.key_set_ecm(ecm_mode, cw, st.key);
			memcpy(st.cw, cw, 8);
			st.mode = ecm_mode;
			st.has_waiting = false;
			st.live = true;

			// a word of the other parity marks where the missing one belonged
			missing = m_parity[par ^ 1].miss_pending;
			m_parity[par ^ 1].miss_pending = false;

			/* End the hold, so a released chunk can put this word to the test. */
			if (st.run_dead)
			{
				st.run_dead = false;
				st.probe_armed = true;
				st.probe_retry = false;
				st.reported = false;
				st.miss_pending = false;
				st.probe_tries = 0;
			}
		}
	}

	m_cw_seen[par].store(true);

	if (missing)
		eWarning("[eDVBCSAEngine] no %s cw arrived for this period", (par ^ 1) ? "odd" : "even");

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
	std::lock_guard<std::mutex> lock(m_lock);

	for (int p = 0; p < 2; ++p)
	{
		ParityState &st = m_parity[p];

		memset(st.cw, 0, 8);
		memset(st.cw_waiting, 0, 8);
		memset(st.cw_judged, 0, 8);
		st.mode = 0;
		st.mode_waiting = 0;
		st.period_start_us = 0;
		st.live = false;
		st.has_waiting = false;
		st.probe_armed = false;
		st.probe_retry = false;
		st.run_dead = false;
		st.reported = false;
		st.miss_pending = false;
		st.probe_tries = 0;
		m_cw_seen[p].store(false);
	}

	m_cur_parity = -1;
	m_turning = -1;
	m_turn_count = 0;
	// another service brings other PIDs, and a stale one could condemn a word
	m_pes_pid_count = 0;
}

/* Try a key on one payload: does a PES start code come out? Only where the
 * payload unit start indicator is set. */
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

uint16_t eDVBCSAEngine::getPid(const unsigned char* pkt)
{
	return (uint16_t)(((pkt[1] & 0x1F) << 8) | pkt[2]);
}

bool eDVBCSAEngine::knownPesPid(uint16_t pid) const
{
	for (int i = 0; i < m_pes_pid_count; ++i)
	{
		if (m_pes_pid[i] == pid)
			return true;
	}
	return false;
}

void eDVBCSAEngine::notePesPid(uint16_t pid)
{
	if (m_pes_pid_count < PES_PIDS && !knownPesPid(pid))
		m_pes_pid[m_pes_pid_count++] = pid;
}

static uint64_t csaMonotonicUs()
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000000ULL + (uint64_t)(ts.tv_nsec / 1000);
}

/* A parity that never had a word is a service we cannot open: holding for
 * it would freeze the zap for the length of the ceiling. */
bool eDVBCSAEngine::holdPlayback() const
{
	return (m_parity[0].live && m_parity[0].run_dead)
		|| (m_parity[1].live && m_parity[1].run_dead);
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

void eDVBCSAEngine::discardPayload(unsigned char* pkt)
{
	const unsigned char aflen = (pkt[3] & 0x20) ? pkt[4] : 0;

	clearTSC(pkt);

	// a pcr is six bytes behind the flags, so a shorter field carries none
	if (aflen >= 7 && aflen <= 183 && (pkt[5] & 0x10))
	{
		memset(pkt + 5 + aflen, 0xFF, 188 - 5 - aflen);  // stuffing
		pkt[4] = 183;
		pkt[3] = (pkt[3] & ~0x30) | 0x20;  // adaptation field only
		pkt[1] &= ~0x40;                   // no payload start
	}
	else
		setNullPacket(pkt);
}

void eDVBCSAEngine::takeWaiting(int parity)
{
	ParityState &st = m_parity[parity];

	if (!st.has_waiting)
		return;

	// the schedules are swapped, not recomputed
	dvbcsa_bs_key_t* spare = st.key;
	st.key = st.waiting;
	st.waiting = spare;
	memcpy(st.cw, st.cw_waiting, 8);
	st.mode = st.mode_waiting;
	st.has_waiting = false;
	st.live = true;
}

void eDVBCSAEngine::enterPeriod(int parity)
{
	ParityState &st = m_parity[parity];

	m_cur_parity = parity;
	st.period_start_us = csaMonotonicUs();
	st.probe_armed = true;
	st.probe_retry = false;
	st.run_dead = false;
	st.reported = false;
	st.probe_tries = 0;
	++m_periods;
}

/* The register in force has to prove itself on the first judgable payload of
 * a period: a word that does not open it is on its way or unusable. */
void eDVBCSAEngine::probePeriodKey(int parity, const unsigned char* pkt, int offset,
	dvbcsa_bs_batch_s* batch, int& cnt)
{
	ParityState &st = m_parity[parity];
	const uint16_t pid = getPid(pkt);
	const char *name = parity ? "odd" : "even";
	int late = 0;
	bool bad = false;

	{
		std::lock_guard<std::mutex> lock(m_lock);

		if (!st.probe_armed || !st.live)
			return;

		if (st.probe_tries >= PROBE_LIMIT)
		{
			// nothing here can judge the word, so let the period run on it
			st.probe_armed = false;
			st.probe_retry = false;
			return;
		}

		++st.probe_tries;

		if (probeKey(st.key, pkt, offset))
		{
			notePesPid(pid);

			// it had gone without an opening word, and the stream waited that long
			if (st.run_dead)
			{
				// the credit can put the start ahead of now, and the clock is unsigned
				const uint64_t now_us = csaMonotonicUs();

				late = now_us > st.period_start_us
					? (int)((now_us - st.period_start_us) / 1000) : 0;
				st.run_dead = false;
				st.miss_pending = false;
			}

			memcpy(st.cw_judged, st.cw, 8);
			st.probe_armed = false;
			st.probe_retry = false;
		}
		else if (!knownPesPid(pid))
		{
			// no payload of this PID ever opened, so the miss says nothing
			eDebug("[eDVBCSAEngine] probe passed over: pid=%04X holds no PES start, %s, period %u",
				pid, name, m_periods);
		}
		else if (!st.probe_retry)
		{
			// one miss can be the payload, judge on the second
			st.probe_retry = true;
		}
		else if (st.has_waiting)
		{
			/* The register is past this period; what was collected belongs to the one
			 * before and goes out with it. */
			if (cnt > 0)
			{
				batch[cnt].data = nullptr;
				g_csa_api.decrypt(st.key, batch, 184);
				cnt = 0;
			}
			takeWaiting(parity);
			st.probe_retry = false;
		}
		else
		{
			/* No word opens this period. Its packets still go out under the
			 * register: noise only looks bad, a gap starves the decoder. */
			st.run_dead = true;
			st.probe_retry = false;

			if (!st.reported)
			{
				st.reported = true;
				/* Another word than the last means unusable, the same means none came. */
				if (memcmp(st.cw_judged, st.cw, 8))
					bad = true;
				else
					st.miss_pending = true;
			}
		}
	}

	if (late > 0)
		eWarning("[eDVBCSAEngine] %s cw arrived %dms into its period", name, late);

	if (bad)
		eWarning("[eDVBCSAEngine] %s cw does not open this period, pid=%04X", name, pid);
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
		const int parity = even ? 0 : 1;
		ParityState &st = m_parity[parity];
		dvbcsa_bs_batch_s* batch = even ? pcks_even : pcks_odd;
		int& cnt = even ? even_cnt : odd_cnt;
		int offset = getPayloadOffset(pkt);

		/* The pids do not turn at the same instant, so the parity flaps at a
		 * boundary. A real period fills the buffer with its parity at once,
		 * the stragglers arrive singly. */
		if (parity != m_cur_parity)
		{
			if (parity != m_turning)
			{
				m_turning = parity;
				m_turn_count = 0;
			}

			if (++m_turn_count >= PERIOD_MIN_PACKETS)
			{
				std::lock_guard<std::mutex> lock(m_lock);

				// Flush before the word changes.
				if (cnt > 0)
				{
					batch[cnt].data = nullptr;
					g_csa_api.decrypt(st.key, batch, 184);
					cnt = 0;
				}

				enterPeriod(parity);
			}
		}
		else
			m_turn_count = 0;

		/* Payload start, payload present, not marked damaged in transit, and
		 * of the period that counts as running: a straggler judged inside the
		 * run that has not been acknowledged yet would be timed against the
		 * period before. */
		if (parity == m_cur_parity && st.probe_armed
			&& (pkt[1] & 0x40) && (pkt[3] & 0x10) && !(pkt[1] & 0x80)
			&& offset < 188)
			probePeriodKey(parity, pkt, offset, batch, cnt);

		if (!(pkt[3] & 0x10))
		{
			// Adaptation field only, nothing to descramble
			clearTSC(pkt);
		}
		else if (!st.live || st.run_dead)
		{
			/* Nothing opens this period, so nothing here can be handed out. */
			discardPayload(pkt);
		}
		else if (offset >= 188)
		{
			// Never pass an invalid payload length to libdvbcsa, it aborts on it
			logBadPacket("adaptation field too long", pkt, i, len);
			discardPayload(pkt);
		}
		else
		{
			// Word in force: descramble and clear TSC
			clearTSC(pkt);
			batch[cnt].data = pkt + offset;
			batch[cnt].len  = 188 - offset;
			cnt++;
		}

		if (cnt == m_batch_size)
		{
			std::lock_guard<std::mutex> lock(m_lock);
			batch[cnt].data = nullptr;
			g_csa_api.decrypt(st.key, batch, 184);
			CSA_LOG("[eDVBCSAEngine] decrypt %s batch (%d)", even ? "even" : "odd", m_batch_size);
			cnt = 0;
		}

		i += 188;
	}

	if (even_cnt > 0 || odd_cnt > 0)
	{
		std::lock_guard<std::mutex> lock(m_lock);

		if (even_cnt > 0)
		{
			pcks_even[even_cnt].data = NULL;
			g_csa_api.decrypt(m_parity[0].key, pcks_even, 184);
			CSA_LOG("[eDVBCSAEngine] decrypt remaining even packets=%d", even_cnt);
		}

		if (odd_cnt > 0)
		{
			pcks_odd[odd_cnt].data = NULL;
			g_csa_api.decrypt(m_parity[1].key, pcks_odd, 184);
			CSA_LOG("[eDVBCSAEngine] decrypt remaining odd packets=%d", odd_cnt);
		}
	}

	CSA_LOG("[eDVBCSAEngine] descramble done");
}
