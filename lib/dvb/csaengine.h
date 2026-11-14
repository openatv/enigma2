#ifndef __dvbcsaengine_h
#define __dvbcsaengine_h

#include <lib/base/object.h>
#include <vector>
#include <atomic>
#include <mutex>
#include <stdint.h>

// Forward declarations for libdvbcsa
struct dvbcsa_bs_key_s;
typedef struct dvbcsa_bs_key_s dvbcsa_bs_key_t;

struct dvbcsa_bs_batch_s {
	unsigned char *data;
	unsigned int len;
};
typedef struct dvbcsa_bs_batch_s dvbcsa_bs_batch_s;

// Function pointer types for dlopen API
typedef dvbcsa_bs_key_t *(*dvbcsa_bs_key_alloc_f)(void);
typedef void (*dvbcsa_bs_key_free_f)(dvbcsa_bs_key_t *);
typedef void (*dvbcsa_bs_key_set_ecm_f)(uint8_t ecm_mode, const uint8_t *cw, dvbcsa_bs_key_t *);
typedef unsigned char (*dvbcsa_get_ecm_table_f)(void);
typedef size_t (*dvbcsa_bs_batch_size_f)(void);
typedef void (*dvbcsa_bs_decrypt_f)(const dvbcsa_bs_key_t *key, dvbcsa_bs_batch_s *pcks, int maxlen);

// Global dlopen API structure
struct csa_dlopen_api
{
	void *handle;
	bool tried;
	bool available;
	dvbcsa_bs_key_alloc_f    key_alloc;
	dvbcsa_bs_key_free_f     key_free;
	dvbcsa_bs_key_set_ecm_f  key_set_ecm;
	dvbcsa_get_ecm_table_f   get_ecm_table;
	dvbcsa_bs_batch_size_f   batch_size;
	dvbcsa_bs_decrypt_f      decrypt;
};

// Global API instance (defined in csaengine.cpp)
extern csa_dlopen_api g_csa_api;

// Load libdvbcsa dynamically (call once at startup)
bool csa_load_library();

/**
 * eDVBCSAEngine - Low-Level CSA Descrambler
 *
 * Thread-safe wrapper around libdvbcsa. Two key registers per parity: the one
 * in force, and one a word that came too early waits in. setKey() (CWHandler
 * thread) writes the one in force unless the output is inside a period it
 * still opens; descramble() (recorder thread) takes the waiting word once a
 * probe on a PES start shows the register is past that period.
 */
class eDVBCSAEngine
{
	DECLARE_REF(eDVBCSAEngine);

public:
	eDVBCSAEngine();
	~eDVBCSAEngine();

	// Initialization
	bool init();

	// Static helpers
	static bool isAvailable() { csa_load_library(); return g_csa_api.available; }
	static int getBatchSize();
	static std::string getLibraryName();
	static std::string getLibraryPath();
	static std::string getLibraryVersion();

	// Key Management (thread-safe, called from CWHandler thread)
	void setKey(int parity, uint8_t ecm_mode, const uint8_t* cw);
	void clearKeys();

	// Descrambling (called from recorder thread)
	void descramble(unsigned char* packets, int len);

	/* Nothing opens the period coming out: hold until a word arrives. */
	bool holdPlayback() const;


	// Status
	bool hasEvenKey() const { return m_cw_seen[0].load(); }
	bool hasOddKey() const { return m_cw_seen[1].load(); }
	bool hasAnyKey() const { return hasEvenKey() || hasOddKey(); }
	int getBatchSizeInstance() const { return m_batch_size; }

private:
	struct ParityState
	{
		dvbcsa_bs_key_t* key{nullptr};      // in force
		dvbcsa_bs_key_t* waiting{nullptr};  // a word that came too early
		uint8_t cw[8]{};                    // word in the register in force
		uint8_t cw_waiting[8]{};
		uint8_t cw_judged[8]{};             // last word a probe accepted
		uint8_t mode{0};
		uint8_t mode_waiting{0};
		uint64_t period_start_us{0};        // when this period began coming out
		bool live{false};                   // the register in force holds a word
		bool has_waiting{false};
		bool probe_armed{false};            // the register has still to prove itself
		bool probe_retry{false};            // one probe has missed
		bool run_dead{false};               // no word here opens this period
		bool reported{false};               // verdict logged
		bool miss_pending{false};           // the period got no word of its own
		unsigned int probe_tries{0};
	};

	ParityState m_parity[2];  // [0] = even
	// Covers the registers and the state above, a decrypt included
	std::mutex m_lock;
	std::atomic<bool> m_cw_seen[2]{};  // A word was accepted, read lock-free
	int m_cur_parity{-1};  // Parity of the period the output is in
	int m_turning{-1};     // Parity the packets may be turning to
	unsigned m_turn_count{0};  // How many of them in a row have said so
	static const unsigned int PROBE_TRIES = 2;
	// A service whose scrambled PIDs carry no PES must not probe every payload
	static const unsigned int PROBE_LIMIT = 8;
	/* Packets of the new parity in a row before the period counts as changed. */
	static const unsigned int PERIOD_MIN_PACKETS = 8;
	/* PIDs that have opened with a PES start. Only those can condemn a word:
	 * a section payload holds no start code to find. Recorder thread only. */
	static const int PES_PIDS = 8;
	uint16_t m_pes_pid[PES_PIDS]{};
	int m_pes_pid_count{0};
	int m_batch_size;
	unsigned int m_bad_packets{0};  // Log rate limit only, races are harmless
	unsigned int m_periods{0};  // Crypto periods seen, to put the others in scale

	// Pre-allocated batch arrays
	std::vector<dvbcsa_bs_batch_s> m_batch_even;
	std::vector<dvbcsa_bs_batch_s> m_batch_odd;

	// TS Packet Helpers
	static bool isPacketValid(const unsigned char* pkt);
	static unsigned char getScrambledBits(const unsigned char* pkt);
	static int getPayloadOffset(const unsigned char* pkt);
	static void clearTSC(unsigned char* pkt);
	static void setNullPacket(unsigned char* pkt);
	// Drop the payload, keep the adaptation field: it is never scrambled
	static void discardPayload(unsigned char* pkt);
	void logBadPacket(const char* reason, const unsigned char* pkt, int offset, int len);
	bool probeKey(const dvbcsa_bs_key_t* key, const unsigned char* pkt, int offset) const;
	static uint16_t getPid(const unsigned char* pkt);
	bool knownPesPid(uint16_t pid) const;
	void notePesPid(uint16_t pid);
	// Caller holds the lock.
	void takeWaiting(int parity);
	void enterPeriod(int parity);
	void probePeriodKey(int parity, const unsigned char* pkt, int offset,
		dvbcsa_bs_batch_s* batch, int& cnt);
};

#endif // __dvbcsaengine_h
