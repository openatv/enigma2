#ifndef __dvbcsaengine_h
#define __dvbcsaengine_h

#include <lib/base/object.h>
#include <vector>
#include <atomic>
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
 * Thread-safe wrapper around libdvbcsa using double-buffered keys.
 * setKey() from CWHandler thread and descramble() from recorder thread
 * can run concurrently without locks.
 *
 * Each parity (even/odd) has two key slots. setKey() writes into the
 * inactive slot, then atomically swaps the active index. descramble()
 * snapshots the active index once per call and uses it throughout.
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

	// Status
	bool hasEvenKey() const { return m_key_even_set; }
	bool hasOddKey() const { return m_key_odd_set; }
	bool hasAnyKey() const { return hasEvenKey() || hasOddKey(); }
	int getBatchSizeInstance() const { return m_batch_size; }

private:
	// Double-buffered keys: two slots per parity, atomic index selects active one.
	// setKey() writes to inactive slot, then swaps index.
	// descramble() reads active slot via snapshot of index.
	dvbcsa_bs_key_t* m_key_even[2];
	dvbcsa_bs_key_t* m_key_odd[2];
	std::atomic<int> m_key_even_idx{0};    // active index for even key (0 or 1)
	std::atomic<int> m_key_odd_idx{0};     // active index for odd key (0 or 1)
	std::atomic<bool> m_key_even_set{false};
	std::atomic<bool> m_key_odd_set{false};
	int m_batch_size;

	// Pre-allocated batch arrays
	std::vector<dvbcsa_bs_batch_s> m_batch_even;
	std::vector<dvbcsa_bs_batch_s> m_batch_odd;

	// TS Packet Helpers
	static bool isPacketValid(const unsigned char* pkt);
	static unsigned char getScrambledBits(const unsigned char* pkt);
	static unsigned char getPayloadOffset(const unsigned char* pkt);
	static void clearTSC(unsigned char* pkt);
};

#endif // __dvbcsaengine_h
