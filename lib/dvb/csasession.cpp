#include <lib/dvb/csasession.h>
#include <lib/dvb/csaengine.h>
#include <lib/dvb/cahandler.h>
#include <lib/base/eerror.h>

#ifdef DREAMNEXTGEN
#include <lib/dvb/alsa.h>
#endif

DEFINE_REF(eDVBCSASession);

static const uint8_t DEFAULT_ECM_MODE = 0x04;

// Static cache: Service -> CSA-ALT + ecm_mode; survives session changes for faster channel switching
// Key: (namespace << 48) | (onid << 32) | (tsid << 16) | sid
struct ServiceCsaInfo {
	bool is_csa_alt;      // true if CSA-ALT detected
	uint8_t ecm_mode;     // Lower nibble of ECM[len-1]
	bool valid;           // true if info has been detected
};
static std::map<uint64_t, ServiceCsaInfo> s_csa_cache;

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
{
	eDebug("[CSASession] Created for service %s", ref.toString().c_str());
}

eDVBCSASession::~eDVBCSASession()
{
	eDebug("[CSASession] Destroyed for service %s", m_service_ref.toString().c_str());

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
		eWarning("[CSASession] Failed to initialize CSA engine");
		m_engine = nullptr;
		return false;
	}

	// Connect to eDVBCAHandler for CW reception
	eDVBCAHandler* ca = eDVBCAHandler::getInstance();
	if (!ca)
	{
		eWarning("[CSASession] eDVBCAHandler not available");
		return false;
	}

	CONNECT(ca->receivedCw, eDVBCSASession::onCwReceived);

	eDebug("[CSASession] Initialized - CSA-ALT detection via ECM analysis");
	return true;
}

// ==================== ECM Monitor ====================

void eDVBCSASession::startECMMonitor(iDVBDemux *demux, uint16_t ecm_pid, uint16_t caid)
{
	if (!demux || ecm_pid == 0 || ecm_pid == 0xFFFF)
		return;

	stopECMMonitor();

	m_ecm_pid = ecm_pid;
	m_caid = caid;

	// Check cache first for faster channel switching
	uint64_t svc_key = makeServiceKey(m_service_ref);
	auto cache_it = s_csa_cache.find(svc_key);
	if (cache_it != s_csa_cache.end() && cache_it->second.valid)
	{
		const ServiceCsaInfo& info = cache_it->second;
		eDebug("[CSASession] ECM Monitor: Found cached info - CSA-ALT=%d, ecm_mode=0x%02X",
			info.is_csa_alt, info.ecm_mode);

		// Pre-load ecm_mode from cache
		m_ecm_mode = info.ecm_mode;
		m_ecm_mode_detected = true;

		if (info.is_csa_alt && !m_active)
		{
			eDebug("[CSASession] ECM Monitor: Activating from cache (CSA-ALT)");
			m_ecm_analyzed = true;
			m_csa_alt = true;
			setActive(true);
		}
	}

	// Create section reader
	ePtr<iDVBSectionReader> reader;
	if (demux->createSectionReader(eApp, reader) != 0 || !reader)
	{
		eWarning("[CSASession] ECM Monitor: Failed to create section reader");
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
		eWarning("[CSASession] ECM Monitor: Failed to start filter on PID %d", ecm_pid);
		m_ecm_reader = nullptr;
		return;
	}

	eDebug("[CSASession] ECM Monitor started on PID %d", ecm_pid);
}

void eDVBCSASession::stopECMMonitor()
{
	if (m_ecm_reader)
	{
		m_ecm_reader->stop();
		m_ecm_reader = nullptr;
		eDebug("[CSASession] ECM Monitor stopped");
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

		eDebug("[CSASession] ECM received (PMT): caid=0x%04X, ecm[2]=0x%02X, ecm[4]=0x%02X, ecm_mode=0x%02X, CSA-ALT=%d",
			m_caid, data[2], data[4], new_ecm_mode, is_csa_alt);

		// Update unified cache
		uint64_t svc_key = makeServiceKey(m_service_ref);
		s_csa_cache[svc_key] = {is_csa_alt, new_ecm_mode, true};

		m_ecm_analyzed = true;
		m_csa_alt = is_csa_alt;

		if (is_csa_alt)
		{
			eDebug("[CSASession] CSA-ALT detected from ECM! Activating software descrambling");
			if (!m_active)
			{
				setActive(true);
			}
		}
		else
		{
			eDebug("[CSASession] ECM analyzed: Not CSA-ALT, hardware descrambling will be used");
		}
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
		eDebug("[CSASession] ACTIVATED - CSA-ALT detected, SW-Descrambling active");
#ifdef DREAMNEXTGEN
		eAlsaOutput::setSoftDecoderActive(1);
#endif
	}
	else
	{
		eDebug("[CSASession] DEACTIVATED - HW-Descrambling (passthrough)");
#ifdef DREAMNEXTGEN
		eAlsaOutput::setSoftDecoderActive(0);
#endif
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

void eDVBCSASession::onCwReceived(eServiceReferenceDVB ref, int parity, const char* cw, uint16_t caid)
{
	// Only for our service
	if (!matchesService(ref))
		return;

	eDebug("[CSASession] onCwReceived: parity=%d for service %s", parity, ref.toString().c_str());

	// Only process CWs when active
	if (!m_active)
		return;

	if (!cw || !m_engine)
		return;

	// Check if this is the first CW (for signaling)
	bool had_any_key = m_engine->hasAnyKey();

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
	eDebug("[CSASession] ECM Mode 0x%02X (%s, tail: %02X %02X %02X %02X)",
		ecm_mode, source, m_ecm_tail[0], m_ecm_tail[1], m_ecm_tail[2], m_ecm_tail[3]);
	const uint8_t* cw_bytes = (const uint8_t*)cw;
	m_engine->setKey(parity, ecm_mode, cw_bytes);
	char caid_str[20] = "";
	if (caid != 0)
		snprintf(caid_str, sizeof(caid_str), "caid=0x%04X, ", caid);
	eDebug("[CSASession] CW set: %sparity=%d, hasEven=%d, hasOdd=%d, CW=%02X",
		caid_str, parity, m_engine->hasEvenKey(), m_engine->hasOddKey(), cw_bytes[0]);

	// If this is the first CW, signal to listeners
	if (!had_any_key && m_engine->hasAnyKey())
	{
		eDebug("[CSASession] First CW received - signaling");
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
}
