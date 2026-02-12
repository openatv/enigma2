#ifndef __dvbcsasession_h
#define __dvbcsasession_h

#include <lib/service/iservicescrambled.h>
#include <lib/dvb/idvb.h>
#include <lib/base/ebase.h>
#include <sigc++/sigc++.h>
#include <functional>

class eDVBCSAEngine;
class eDVBCAHandler;

/**
 * eDVBCSASession - CW-Management per Service with ECM-based CSA-ALT Detection
 *
 * - Receives CWs from softcam via eDVBCAHandler signals
 * - Filters by service reference
 * - Monitors ECM to detect CSA-ALT and ecm_mode
 * - ACTIVATES ITSELF when CSA-ALT is detected from ECM
 * - Delegates descrambling to eDVBCSAEngine
 *
 * The session is created "speculatively" and remains inactive.
 * ECM Monitor analyzes incoming ECMs and activates if CSA-ALT is detected.
 * Detection is fully autonomous - no dependency on external signals.
 *
 * When inactive: descramble() is a passthrough (no changes to data)
 * When active: descramble() delegates to eDVBCSAEngine
 */
class eDVBCSASession : public iServiceScrambled, public sigc::trackable
{
	DECLARE_REF(eDVBCSASession);

public:
	/**
	 * Constructor
	 * @param ref Service reference for CW filtering
	 *
	 * Session starts INACTIVE and activates when CSA-ALT is detected from ECM
	 */
	eDVBCSASession(const eServiceReferenceDVB& ref);
	~eDVBCSASession();

	// Initialization - connects to eDVBCAHandler for CW reception
	bool init();

	// iServiceScrambled Interface
	// Descrambles in-place when active and CW available, otherwise passthrough
	void descramble(unsigned char* packets, int len) override;

	// Status
	bool isActive() const { return m_active; }
	bool hasKeys() const override;
	const eServiceReferenceDVB& getServiceRef() const { return m_service_ref; }

	/**
	 * Start ECM monitoring to detect ecm_mode and CSA-ALT
	 * @param demux Demux to use for filtering
	 * @param ecm_pid ECM PID from PMT
	 * @param caid CA System ID for CSA-ALT detection
	 *
	 * Reads ecm[len-1] and extracts lower nibble for ecm_mode.
	 * Also detects CSA-ALT from ECM using softcam's select_csa_alt() logic:
	 * - CAID is VideoGuard (0x09xx)
	 * - ecm[4] != 0
	 * - (ecm[2] - ecm[4]) == 4
	 */
	void startECMMonitor(iDVBDemux *demux, uint16_t ecm_pid, uint16_t caid);
	void stopECMMonitor();

	uint8_t getEcmMode() const { return m_ecm_mode; }
	bool isEcmModeDetected() const { return m_ecm_mode_detected; }
	bool isEcmAnalyzed() const { return m_ecm_analyzed; }  // true once ECM was analyzed
	bool isCsaAlt() const { return m_csa_alt; }            // true if CSA-ALT was detected

	/**
	 * Force activation for recording sessions
	 * Recording sessions don't do ECM analysis - they trust that
	 * Live-TV has already detected CSA-ALT for this channel
	 */
	void forceActivate() { setActive(true); }

	/**
	 * Force deactivation for FCC mode switching
	 * When FCC goes back to prepare mode, we need to deactivate
	 * the session but keep it around for the next switch
	 */
	void forceDeactivate() { setActive(false); }

	// Signal when session is activated (for Live-TV decoder setup)
	sigc::signal<void(bool)> activated;  // true=activated, false=deactivated

	// Signal when first CW is received (for decoder start timing)
	sigc::signal<void()> firstCwReceived;

	// Optional callback to check if activation should be suppressed
	// (e.g. CI module handles decryption). Return true to suppress.
	std::function<bool()> shouldSuppressActivation;

private:
	eServiceReferenceDVB m_service_ref;
	ePtr<eDVBCSAEngine> m_engine;

	// Activation status
	bool m_active;      // true when CSA-ALT detected from ECM

	// ECM monitoring for ecm_mode and CSA-ALT detection
	ePtr<iDVBSectionReader> m_ecm_reader;
	ePtr<eConnection> m_ecm_conn;
	uint16_t m_ecm_pid;
	uint16_t m_caid;              // CA System ID for CSA-ALT detection
	uint8_t m_ecm_mode;           // Detected ecm_mode
	uint8_t m_ecm_tail[4];        // Last 4 bytes of ECM for debugging
	bool m_ecm_mode_detected;     // true once first ECM was received
	bool m_ecm_analyzed;          // true once CSA-ALT check was performed
	bool m_csa_alt;               // true if CSA-ALT was detected
	void ecmDataReceived(const uint8_t *data);

	// Signal Connections
	ePtr<eConnection> m_cw_connection;

	// CW Handler (called from eDVBCAHandler signal)
	void onCwReceived(eServiceReferenceDVB ref, int parity, const char* cw, uint16_t caid, uint32_t serviceId);

	// Helper
	bool matchesService(const eServiceReferenceDVB& ref) const;
	void setActive(bool active);

	// eDVBCWHandler registration
	uint32_t m_cw_service_id;       // Softcam's serviceId (set on first CW)
	bool m_cw_handler_registered;   // true once registered with eDVBCWHandler
	bool m_first_cw_signaled;       // true once firstCwReceived signal was emitted

	// CW buffer for CWs arriving before activation
	// When a CW arrives while m_active is false, we store it here.
	// On setActive(true), the buffered CW is replayed immediately,
	// avoiding a multi-second wait for the next CW cycle.
	struct PendingCw {
		int parity;
		char cw[8];
		uint16_t caid;
		uint32_t serviceId;
		bool valid;
	};
	PendingCw m_pending_cw;
};

#endif // __dvbcsasession_h
