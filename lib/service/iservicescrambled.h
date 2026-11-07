#ifndef __iservicescrambled_h
#define __iservicescrambled_h

#include <lib/base/object.h>

/**
 * iServiceScrambled - Interface for software descrambling
 *
 * Implemented by eDVBCSASession to provide descrambling
 * callback for eDVBTSRecorder.
 */
class iServiceScrambled: public iObject
{
public:
	/**
	 * Descramble packets in-place
	 * @param packets TS packet buffer
	 * @param len Buffer length in bytes
	 *
	 * When active and CW available: descrambles in-place
	 * Otherwise: passthrough (no changes to data)
	 */
	virtual void descramble(unsigned char*, int) = 0;

	/**
	 * Milliseconds the last control word came too late by, cleared on read
	 *
	 * Reports how far into its own crypto period a key arrived, so a
	 * playback delay can grow by what it was short of. Zero when nothing
	 * is pending, and for implementations that do not track it.
	 */
	virtual int takeLateDeficitMs() { return 0; }

	virtual bool hasKeys() const { return true; }
};

#endif // __iservicescrambled_h
