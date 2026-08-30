#include <lib/dvb/csasession.h>
#include <lib/dvb/csaengine.h>
#include <lib/dvb/cahandler.h>
#include <lib/dvb/cwhandler.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>

#include <cstdio>
#include <fstream>
#include <iomanip>
#include <sstream>

#ifdef DREAMNEXTGEN
#include <lib/dvb/alsa.h>
#endif

DEFINE_REF(eDVBCSASession);

static const uint8_t DEFAULT_ECM_MODE = 0x04;

// Static cache: Service -> CSA-ALT + ecm_mode + serviceId; survives session changes for faster channel switching
// Key: (onid << 32) | (tsid << 16) | sid
struct ServiceCsaInfo {
	bool is_csa_alt;      // true if CSA-ALT detected
	uint8_t ecm_mode;     // Lower nibble of ECM[len-1]
	bool valid;           // true if info has been detected
	uint32_t serviceId;   // Softcam's internal service ID (for CWHandler pre-registration)
	bool serviceId_valid; // true if serviceId has been seen
};
static std::map<uint64_t, ServiceCsaInfo> s_csa_cache;
static bool s_persistent_csa_cache_loaded = false;
static bool s_persistent_csa_cache_dirty = false;

static std::string persistentCsaCachePath()
{
	return eEnv::resolve("${sysconfdir}/enigma2/softcsa.cache");
}

// Keep positive CSA-ALT detections across GUI restarts so known services can
// select SoftCSA immediately without repeating unnecessary HW decoder setup.
static void loadPersistentCsaCache()
{
	if (s_persistent_csa_cache_loaded)
		return;

	s_persistent_csa_cache_loaded = true;
	std::ifstream in(persistentCsaCachePath());
	if (!in.good())
		return;

	unsigned int loaded = 0;
	std::string line;
	while (std::getline(in, line))
	{
		if (line.empty() || line[0] == '#')
			continue;

		unsigned long long key = 0;
		unsigned int ecm_mode = 0;
		unsigned int service_id = 0;
		std::istringstream fields(line);
		if (!(fields >> std::hex >> key >> ecm_mode >> service_id) || ecm_mode > 0x0F)
			continue;

		ServiceCsaInfo &info = s_csa_cache[static_cast<uint64_t>(key)];
		info.is_csa_alt = true;
		info.ecm_mode = static_cast<uint8_t>(ecm_mode);
		info.valid = true;
		info.serviceId = service_id;
		info.serviceId_valid = service_id != 0;
		++loaded;
	}

	eDebug("[eDVBCSASession] Loaded %u persistent CSA-ALT service(s)", loaded);
}

static void flushPersistentCsaCache()
{
	if (!s_persistent_csa_cache_dirty)
		return;

	const std::string path = persistentCsaCachePath();
	const std::string temporary_path = path + ".tmp";
	std::ofstream out(temporary_path, std::ios::trunc);
	if (!out.good())
	{
		eWarning("[eDVBCSASession] Failed to write persistent cache %s", temporary_path.c_str());
		return;
	}

	out << "# Enigma2 SoftCSA CSA-ALT cache v1\n";
	for (const auto &entry : s_csa_cache)
	{
		const ServiceCsaInfo &info = entry.second;
		if (!info.valid || !info.is_csa_alt)
			continue;

		out << std::hex << std::setfill('0')
			<< std::setw(16) << entry.first << ' '
			<< std::setw(2) << static_cast<unsigned int>(info.ecm_mode) << ' '
			<< std::setw(8) << (info.serviceId_valid ? info.serviceId : 0) << '\n';
	}
	out.close();

	if (!out.good() || std::rename(temporary_path.c_str(), path.c_str()) != 0)
	{
		eWarning("[eDVBCSASession] Failed to replace persistent cache %s", path.c_str());
		std::remove(temporary_path.c_str());
		return;
	}

	s_persistent_csa_cache_dirty = false;
}

// Helper: Check if CAID is VideoGuard
static bool caid_is_videoguard(uint16_t caid)
{
	return (caid >> 8) == 0x09;
}

// Helper: Detect CSA-ALT from ECM data
static bool detect_csa_alt_from_ecm(const uint8_t *ecm, uint16_t caid)
{
	if (!ecm)
		return false;

	return (caid_is_videoguard(caid)
	        && ecm[4] != 0
	        && (ecm[2] - ecm[4]) == 4);
}

// Helper: Create cache key from DVB triplet (SID/TSID/ONID - ignore namespace)
// This allows cache sharing between sessions with different namespaces
static uint64_t makeServiceKey(const eServiceReferenceDVB& ref)
{
	return ((uint64_t)ref.getOriginalNetworkID().get() << 32) |
	       ((uint64_t)ref.getTransportStreamID().get() << 16) |
	       (uint64_t)ref.getServiceID().get();
}

// Helper: Compare services by DVB triplet (SID/TSID/ONID - ignore namespace)
// This enables CW sharing between sessions with different namespaces
static bool dvbTripletMatch(const eServiceReferenceDVB& ref1, const eServiceReferenceDVB& ref2)
{
	return ref1.getServiceID() == ref2.getServiceID() &&
	       ref1.getTransportStreamID() == ref2.getTransportStreamID() &&
	       ref1.getOriginalNetworkID() == ref2.getOriginalNetworkID();
}

static bool extractTsPesPts(const unsigned char *packet, uint64_t &pts)
{
	if (!packet || packet[0] != 0x47 || !(packet[1] & 0x40))
		return false;

	const unsigned int adaptation_control = (packet[3] >> 4) & 0x03;
	if (adaptation_control == 0 || adaptation_control == 2)
		return false;

	unsigned int payload_offset = 4;
	if (adaptation_control == 3)
	{
		payload_offset += 1 + packet[4];
		if (payload_offset >= 188)
			return false;
	}

	const unsigned char *pes = packet + payload_offset;
	const unsigned int available = 188 - payload_offset;
	if (available < 14 || pes[0] != 0x00 || pes[1] != 0x00 || pes[2] != 0x01)
		return false;
	if (!(pes[7] & 0x80) || pes[8] < 5)
		return false;
	if (!(pes[9] & 0x01) || !(pes[11] & 0x01) || !(pes[13] & 0x01))
		return false;

	pts = (static_cast<uint64_t>(pes[9] & 0x0E) << 29)
		| (static_cast<uint64_t>(pes[10]) << 22)
		| (static_cast<uint64_t>(pes[11] & 0xFE) << 14)
		| (static_cast<uint64_t>(pes[12]) << 7)
		| (static_cast<uint64_t>(pes[13] & 0xFE) >> 1);
	return true;
}

static unsigned int ptsSpanMs(uint64_t first, uint64_t last)
{
	static const uint64_t PTS_WRAP = 1ULL << 33;
	const uint64_t span = last >= first ? last - first : PTS_WRAP - first + last;
	return static_cast<unsigned int>(span / 90);
}

static unsigned int ptsBufferedMs(uint64_t first, uint64_t last, uint64_t last_step)
{
	// A PTS marks the beginning of a PES block, so last-first omits the media
	// carried by the final block.  Include one observed interval (bounded to
	// 500ms) to avoid systematically underestimating coarse audio PES chunks.
	static const uint64_t MAX_TRAILING_STEP = 500ULL * 90;
	const uint64_t trailing = last_step < MAX_TRAILING_STEP ? last_step : MAX_TRAILING_STEP;
	return ptsSpanMs(first, last) + static_cast<unsigned int>(trailing / 90);
}

eDVBCSASession::eDVBCSASession(const eServiceReferenceDVB& ref)
	: m_service_ref(ref)
	, m_active(false)
	, m_ecm_pid(0)
	, m_caid(0)
	, m_ecm_mode(DEFAULT_ECM_MODE)
	, m_ecm_tail{}
	, m_ecm_mode_detected(false)
	, m_ecm_analyzed(false)
	, m_csa_alt(false)
	, m_cw_service_id(0)
	, m_cw_alt_service_id(0)
	, m_cw_handler_registered(false)
	, m_first_cw_signaled(false)
	, m_pending_cw{}
	, m_buffer_readiness_enabled(false)
	, m_buffer_video_pid(-1)
	, m_buffer_audio_pid(-1)
	, m_buffer_video{}
	, m_buffer_audio{}
{
	eDebug("[eDVBCSASession] Created for service %s", ref.toString().c_str());
}

void eDVBCSASession::configureBufferReadiness(int video_pid, int audio_pid)
{
	m_buffer_readiness_enabled.store(false, std::memory_order_release);
	std::lock_guard<std::mutex> lock(m_buffer_readiness_mutex);
	m_buffer_video_pid = video_pid;
	m_buffer_audio_pid = audio_pid;
	m_buffer_video = {};
	m_buffer_audio = {};
	const bool enabled = video_pid >= 0 || audio_pid >= 0;
	m_buffer_readiness_enabled.store(enabled, std::memory_order_release);
	if (enabled)
		eDebug("[eDVBCSASession] Buffer readiness reset: vpid=%04x apid=%04x",
			video_pid, audio_pid);
	else
		eDebug("[eDVBCSASession] Buffer readiness disabled");
}

eDVBCSASession::BufferReadiness eDVBCSASession::getBufferReadiness() const
{
	std::lock_guard<std::mutex> lock(m_buffer_readiness_mutex);
	BufferReadiness readiness = {};
	readiness.video_pid = m_buffer_video_pid;
	readiness.audio_pid = m_buffer_audio_pid;
	readiness.video_packets = m_buffer_video.packets;
	readiness.audio_packets = m_buffer_audio.packets;
	readiness.video_pts_valid = m_buffer_video.valid;
	readiness.audio_pts_valid = m_buffer_audio.valid;
	readiness.video_ms = m_buffer_video.valid
		? ptsBufferedMs(m_buffer_video.first, m_buffer_video.last, m_buffer_video.last_step) : 0;
	readiness.audio_ms = m_buffer_audio.valid
		? ptsBufferedMs(m_buffer_audio.first, m_buffer_audio.last, m_buffer_audio.last_step) : 0;
	return readiness;
}

void eDVBCSASession::updateBufferReadiness(const unsigned char *packets, int len)
{
	if (!packets || len < 188 || !m_buffer_readiness_enabled.load(std::memory_order_acquire))
		return;

	std::lock_guard<std::mutex> lock(m_buffer_readiness_mutex);
	if (!m_buffer_readiness_enabled.load(std::memory_order_acquire)
		|| (m_buffer_video_pid < 0 && m_buffer_audio_pid < 0))
		return;

	static const uint64_t MAX_PTS_STEP = 10ULL * 90000;
	static const uint64_t MAX_PTS_REORDER = 2ULL * 90000;
	static const uint64_t PTS_WRAP = 1ULL << 33;

	for (int offset = 0; offset + 188 <= len; offset += 188)
	{
		const unsigned char *packet = packets + offset;
		if (packet[0] != 0x47 || (packet[3] >> 6) != 0)
			continue;

		const int pid = ((packet[1] & 0x1F) << 8) | packet[2];
		PtsReadiness *state = nullptr;
		if (pid == m_buffer_video_pid)
			state = &m_buffer_video;
		else if (pid == m_buffer_audio_pid)
			state = &m_buffer_audio;
		if (!state)
			continue;

		++state->packets;
		uint64_t pts = 0;
		if (!extractTsPesPts(packet, pts))
			continue;

		if (!state->valid)
		{
			state->first = state->last = pts;
			state->last_step = 0;
			state->valid = true;
			continue;
		}

		const uint64_t forward = pts >= state->last
			? pts - state->last : PTS_WRAP - state->last + pts;
		if (forward <= MAX_PTS_STEP)
		{
			if (forward)
				state->last_step = forward;
			state->last = pts;
			continue;
		}

		const uint64_t backward = state->last >= pts
			? state->last - pts : PTS_WRAP - pts + state->last;
		if (backward <= MAX_PTS_REORDER)
		{
			// Presentation order can briefly move backwards for B-frames.
			// Keep the furthest buffered timestamp instead of resetting.
			continue;
		}

		// A discontinuity or stale data must not make the gate look ready.
		state->first = state->last = pts;
		state->last_step = 0;
	}
}

eDVBCSASession::~eDVBCSASession()
{
	eDebug("[eDVBCSASession] Destroyed for service %s", m_service_ref.toString().c_str());

	if (m_cw_handler_registered)
	{
		eDVBCWHandler::getInstance()->unregisterEngine(m_cw_service_id, m_engine);
		if (m_cw_alt_service_id)
			eDVBCWHandler::getInstance()->unregisterEngine(m_cw_alt_service_id, m_engine);
	}

	stopECMMonitor();

#ifdef DREAMNEXTGEN
	// Reset audio delay flag when session is destroyed
	eAlsaOutput::setSoftDecoderActive(0);
#endif
}

bool eDVBCSASession::init()
{
	// Create engine
	m_engine = new eDVBCSAEngine();
	if (!m_engine->init())
	{
		eWarning("[eDVBCSASession] Failed to initialize CSA engine");
		m_engine = nullptr;
		return false;
	}

	// Connect to eDVBCAHandler for CW reception
	eDVBCAHandler* ca = eDVBCAHandler::getInstance();
	if (!ca)
	{
		eWarning("[eDVBCSASession] eDVBCAHandler not available");
		return false;
	}

	CONNECT(ca->receivedCw, eDVBCSASession::onCwReceived);

	eDebug("[eDVBCSASession] Initialized - CSA-ALT detection via ECM analysis");
	return true;
}

// ==================== ECM Monitor ====================

void eDVBCSASession::startECMMonitor(iDVBDemux *demux, uint16_t ecm_pid, uint16_t caid)
{
	if (!demux)
		return;

	m_caid = caid;
	loadPersistentCsaCache();

	// Cache-driven early activation when CSA-ALT for this service is already
	// known. Disabled in Aggressive mode (audio race on dm900).
	const bool cache_early_activate_disabled =
		(eSimpleConfig::getInt("config.softcsa.decoderRelease", 0) == 2);

	if (!cache_early_activate_disabled)
	{
		uint64_t svc_key = makeServiceKey(m_service_ref);
		if (auto cache_it = s_csa_cache.find(svc_key); cache_it != s_csa_cache.end() && cache_it->second.valid)
		{
			const ServiceCsaInfo& info = cache_it->second;
			eDebug("[eDVBCSASession] ECM Monitor: Found cached info - CSA-ALT=%d, ecm_mode=0x%02X",
				info.is_csa_alt, info.ecm_mode);

			// Pre-load ecm_mode from cache
			m_ecm_mode = info.ecm_mode;
			m_ecm_mode_detected = true;

			const bool use_cached_alt = info.is_csa_alt && caid_is_videoguard(caid);
			m_csa_alt = use_cached_alt;

			if (use_cached_alt && !m_active)
			{
				if (shouldSuppressActivation && shouldSuppressActivation())
				{
					eDebug("[eDVBCSASession] ECM Monitor: CSA-ALT cached but activation suppressed (CI module)");
				}
				else
				{
					eDebug("[eDVBCSASession] ECM Monitor: Activating from cache (CSA-ALT)");
					setActive(true);
				}
			}

			if (!info.is_csa_alt)
			{
				m_ecm_analyzed = true;
				return;
			}

			// A positive cache entry starts SoftCSA immediately, but keep the ECM
			// monitor running once to validate it.  This automatically removes a
			// stale entry if the provider changes the CA system or scrambling mode.
			eDebug("[eDVBCSASession] ECM Monitor: Validating cached CSA-ALT info");
		}
	}

	// The first program-info event can contain the CAID while its ECM PID is
	// still the 0xFFFF placeholder.  Cache activation above must happen on that
	// event so updateDecoder() never starts the hardware decoder.  A later event
	// supplies the real ECM PID and starts validation normally.
	if (ecm_pid == 0 || ecm_pid == 0xFFFF)
	{
		eDebug("[eDVBCSASession] ECM Monitor: Waiting for valid ECM PID after cache lookup");
		return;
	}

	stopECMMonitor();
	m_ecm_pid = ecm_pid;

	// Create section reader
	ePtr<iDVBSectionReader> reader;
	if (demux->createSectionReader(eApp, reader) != 0 || !reader)
	{
		eWarning("[eDVBCSASession] ECM Monitor: Failed to create section reader");
		return;
	}

	m_ecm_reader = reader;

	// Connect callback
	m_ecm_reader->connectRead(sigc::mem_fun(*this, &eDVBCSASession::ecmDataReceived), m_ecm_conn);

	// Setup filter for ECM (table_id 0x80 and 0x81)
	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));
	mask.pid = ecm_pid;
	mask.data[0] = 0x80;  // Match table_id 0x80 (even) and 0x81 (odd)
	mask.mask[0] = 0xFE;  // Mask to match both 0x80 and 0x81
	mask.flags = 0;       // No CRC check for ECM

	if (m_ecm_reader->start(mask) != 0)
	{
		eWarning("[eDVBCSASession] ECM Monitor: Failed to start filter on PID %d", ecm_pid);
		m_ecm_reader = nullptr;
		return;
	}

	eDebug("[eDVBCSASession] ECM Monitor started on PID %d", ecm_pid);
}

void eDVBCSASession::stopECMMonitor()
{
	if (m_ecm_reader)
	{
		m_ecm_reader->stop();
		m_ecm_reader = nullptr;
		eDebug("[eDVBCSASession] ECM Monitor stopped");
	}
	m_ecm_conn = nullptr;
}

void eDVBCSASession::ecmDataReceived(const uint8_t *data)
{
	if (!data)
		return;

	// Parse ECM section length
	// ECM format: table_id (1) + section_syntax_indicator/length (2) + data...
	uint16_t section_length = ((data[1] & 0x0F) << 8) | data[2];
	uint16_t total_length = section_length + 3;  // +3 for header bytes

	if (total_length < 8 || total_length > 4096)
		return;

	// Store last 4 bytes for debugging
	memcpy(m_ecm_tail, &data[total_length - 4], 4);

	// Read last byte and extract lower nibble as ecm_mode
	uint8_t new_ecm_mode = m_ecm_tail[3] & 0x0F;

	if (!m_ecm_mode_detected || m_ecm_mode != new_ecm_mode)
	{
		m_ecm_mode = new_ecm_mode;
		m_ecm_mode_detected = true;
	}

	// Detect CSA-ALT from ECM
	if (!m_ecm_analyzed)
	{
		bool is_csa_alt = detect_csa_alt_from_ecm(data, m_caid);

		eDebug("[eDVBCSASession] ECM received (PMT): caid=0x%04X, ecm[2]=0x%02X, ecm[4]=0x%02X, ecm_mode=0x%02X, CSA-ALT=%d",
			m_caid, data[2], data[4], new_ecm_mode, is_csa_alt);

		// Update unified cache (preserve serviceId if already known). Only
		// rewrite the persistent positive-only view when that view changes.
		uint64_t svc_key = makeServiceKey(m_service_ref);
		auto& cached = s_csa_cache[svc_key];
		const bool persistent_cache_changed = cached.valid
			? cached.is_csa_alt != is_csa_alt
				|| (is_csa_alt && cached.ecm_mode != new_ecm_mode)
			: is_csa_alt;
		cached.is_csa_alt = is_csa_alt;
		cached.ecm_mode = new_ecm_mode;
		cached.valid = true;
		if (persistent_cache_changed)
			s_persistent_csa_cache_dirty = true;
		flushPersistentCsaCache();

		m_ecm_analyzed = true;
		m_csa_alt = is_csa_alt;

		if (is_csa_alt)
		{
			eDebug("[eDVBCSASession] CSA-ALT detected from ECM! Activating software descrambling");
			if (!m_active)
			{
				if (shouldSuppressActivation && shouldSuppressActivation())
				{
					eDebug("[eDVBCSASession] Activation suppressed (CI module handles decryption)");
				}
				else
				{
					setActive(true);
				}
			}
		}
		else
		{
			eDebug("[eDVBCSASession] ECM analyzed: Not CSA-ALT, hardware descrambling will be used");
			if (m_active)
			{
				eWarning("[eDVBCSASession] Cached CSA-ALT info is stale, returning to hardware descrambling");
				setActive(false);
				// setActive(false) resets the analysis state; retain the result of
				// this validation so eventNewProgramInfo does not start another reader.
				m_ecm_mode = new_ecm_mode;
				m_ecm_mode_detected = true;
				m_ecm_analyzed = true;
				m_csa_alt = false;
			}
		}

		stopECMMonitor();
	}
}

// ==================== Service Matching ====================

bool eDVBCSASession::matchesService(const eServiceReferenceDVB& ref) const
{
	return dvbTripletMatch(ref, m_service_ref);
}

void eDVBCSASession::setActive(bool active)
{
	if (m_active == active)
		return;

	m_active = active;

	if (m_active)
	{
		eDebug("[eDVBCSASession] ACTIVATED - CSA-ALT detected, SW-Descrambling active");
#ifdef DREAMNEXTGEN
		eAlsaOutput::setSoftDecoderActive(1);
#endif
		// Pre-register engine at CWHandler using cached serviceId.
		// This closes the CW gap during PiP swap: when the old session is
		// destroyed (unregistering its engine), the new session's engine is
		// already registered and receives CWs without interruption.
		if (!m_cw_handler_registered && m_engine)
		{
			uint64_t svc_key = makeServiceKey(m_service_ref);
			auto cache_it = s_csa_cache.find(svc_key);
			if (cache_it != s_csa_cache.end() && cache_it->second.serviceId_valid)
			{
				m_cw_service_id = cache_it->second.serviceId;
				eDVBCWHandler::getInstance()->registerEngine(m_cw_service_id, m_engine, m_ecm_mode);
				m_cw_handler_registered = true;
				eDebug("[eDVBCSASession] Pre-registered engine at CWHandler (cached serviceId=%u)", m_cw_service_id);
			}
		}

		// Replay buffered CW that arrived before activation
		if (m_pending_cw.valid)
		{
			eDebug("[eDVBCSASession] Replaying buffered CW: parity=%d", m_pending_cw.parity);
			onCwReceived(m_service_ref, m_pending_cw.parity, m_pending_cw.cw,
				m_pending_cw.caid, m_pending_cw.serviceId);
			m_pending_cw.valid = false;
		}
	}
	else
	{
		eDebug("[eDVBCSASession] DEACTIVATED - HW-Descrambling (passthrough)");
#ifdef DREAMNEXTGEN
		eAlsaOutput::setSoftDecoderActive(0);
#endif
		if (m_cw_handler_registered)
		{
			eDVBCWHandler::getInstance()->unregisterEngine(m_cw_service_id, m_engine);
			if (m_cw_alt_service_id)
			{
				eDVBCWHandler::getInstance()->unregisterEngine(m_cw_alt_service_id, m_engine);
				m_cw_alt_service_id = 0;
			}
			m_cw_handler_registered = false;
		}
		m_first_cw_signaled = false;
		m_pending_cw.valid = false;
		if (m_engine)
			m_engine->clearKeys();
		// Reset ECM analysis state
		m_ecm_mode_detected = false;
		m_ecm_mode = DEFAULT_ECM_MODE;
		m_ecm_analyzed = false;
		m_csa_alt = false;
	}

	// Signal to parent (e.g. eDVBServicePlay for decoder setup)
	activated(m_active);
}

void eDVBCSASession::onCwReceived(eServiceReferenceDVB ref, int parity, const char* cw, uint16_t caid, uint32_t serviceId)
{
	// Only for our service
	if (!matchesService(ref))
		return;

	if (!m_cw_handler_registered)
		eDebug("[eDVBCSASession] onCwReceived: parity=%d for service %s", parity, ref.toString().c_str());

	// Buffer CW if session not yet active (activation pending on ECM analysis)
	if (!m_active)
	{
		if (cw)
		{
			m_pending_cw.parity = parity;
			memcpy(m_pending_cw.cw, cw, 8);
			m_pending_cw.caid = caid;
			m_pending_cw.serviceId = serviceId;
			m_pending_cw.valid = true;
			eDebug("[eDVBCSASession] CW buffered (session not yet active): parity=%d", parity);
		}
		return;
	}

	if (!cw || !m_engine)
		return;

	// Get ecm_mode: prefer detected, then cached, then default
	uint8_t ecm_mode;
	const char *source = "default";
	uint64_t svc_key = makeServiceKey(m_service_ref);

	if (m_ecm_mode_detected)
	{
		ecm_mode = m_ecm_mode;
		source = "detected";
	}
	else
	{
		auto cache_it = s_csa_cache.find(svc_key);
		if (cache_it != s_csa_cache.end() && cache_it->second.valid)
		{
			ecm_mode = cache_it->second.ecm_mode;
			source = "cached";
		}
		else
		{
			ecm_mode = DEFAULT_ECM_MODE;
		}
	}

	// Register/update eDVBCWHandler - it handles setKey() directly from its thread
	if (!m_cw_handler_registered)
	{
		m_cw_service_id = serviceId;
		eDVBCWHandler::getInstance()->registerEngine(serviceId, m_engine, ecm_mode);
		m_cw_handler_registered = true;
		// The first CW packet was already intercepted by eDVBCWHandler BEFORE this
		// registration, so the engine missed it. Apply it now to avoid waiting
		// for the next CW cycle.
		m_engine->setKey(parity, ecm_mode, (const uint8_t*)cw);
		const uint8_t* cw_bytes = (const uint8_t*)cw;
		eDebug("[eDVBCSASession] CW set: caid=0x%04X, parity=%d, hasEven=%d, hasOdd=%d, CW=%02X",
			caid, parity, m_engine->hasEvenKey(), m_engine->hasOddKey(), cw_bytes[0]);

		// Cache serviceId for future sessions (enables pre-registration on PiP swap)
		auto& cached = s_csa_cache[svc_key];
		const bool service_id_changed = serviceId != 0
			&& (!cached.serviceId_valid || cached.serviceId != serviceId);
		if (serviceId != 0)
		{
			cached.serviceId = serviceId;
			cached.serviceId_valid = true;
		}
		if (cached.valid && cached.is_csa_alt && service_id_changed)
			s_persistent_csa_cache_dirty = true;
		flushPersistentCsaCache();
	}
	else if (serviceId != 0 && serviceId != m_cw_service_id &&
		serviceId != m_cw_alt_service_id &&
		ref.getDVBNamespace() == m_service_ref.getDVBNamespace())
	{
		// ServiceId mismatch: pre-registration used cached serviceId from a different
		// namespace variant of the same DVB triplet (e.g. C02ED8 vs C00000 for fallback
		// tuner streams). Register ADDITIONALLY for the actual serviceId so the engine
		// receives CWs from both connections - OScam alternates CW delivery between them.
		eDebug("[eDVBCSASession] Additional serviceId %u registered (primary=%u)", serviceId, m_cw_service_id);
		m_cw_alt_service_id = serviceId;
		eDVBCWHandler::getInstance()->registerEngine(serviceId, m_engine, ecm_mode);
		// Apply this CW directly - CWHandler already intercepted and missed it
		m_engine->setKey(parity, ecm_mode, (const uint8_t*)cw);
		const uint8_t* cw_bytes = (const uint8_t*)cw;
		eDebug("[eDVBCSASession] CW set: caid=0x%04X, parity=%d, hasEven=%d, hasOdd=%d, CW=%02X",
			caid, parity, m_engine->hasEvenKey(), m_engine->hasOddKey(), cw_bytes[0]);
	}
	else
	{
		eDVBCWHandler::getInstance()->updateEcmMode(m_cw_service_id, m_engine, ecm_mode);
		// Set key if engine missed it (e.g. replayed CW from m_pending_cw)
		if ((parity == 0 && !m_engine->hasEvenKey()) || (parity == 1 && !m_engine->hasOddKey()))
		{
			m_engine->setKey(parity, ecm_mode, (const uint8_t*)cw);
			eDebug("[eDVBCSASession] CW set (missed by CWHandler): parity=%d, hasEven=%d, hasOdd=%d",
				parity, m_engine->hasEvenKey(), m_engine->hasOddKey());
		}
	}

	if (m_ecm_mode != ecm_mode)
		eDebug("[eDVBCSASession] ECM Mode 0x%02X (%s, tail: %02X %02X %02X %02X)",
			ecm_mode, source, m_ecm_tail[0], m_ecm_tail[1], m_ecm_tail[2], m_ecm_tail[3]);

	// Signal firstCwReceived once (for SoftDecoder start)
	if (!m_first_cw_signaled && m_engine->hasAnyKey())
	{
		eDebug("[eDVBCSASession] First CW received - signaling");
		m_first_cw_signaled = true;
		firstCwReceived();
	}
}

bool eDVBCSASession::hasKeys() const
{
	return m_engine && m_engine->hasAnyKey();
}

void eDVBCSASession::descramble(unsigned char* packets, int len)
{
	// Not active = Passthrough (CI+, StreamRelay, FTA, or detection pending)
	if (!m_active)
		return;

	// No engine or no CW = Passthrough (may cause artifacts at channel start)
	if (!m_engine || !m_engine->hasAnyKey())
		return;

	// CW available - descramble via engine (in-place)
	m_engine->descramble(packets, len);

	// The engine turns packets without the matching parity key into null
	// packets.  Scanning after descrambling therefore counts only clear A/V
	// packets that are safe to queue for decoder startup.
	updateBufferReadiness(packets, len);
}
