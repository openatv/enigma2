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

	/** How far into its period a word turned up, in ms; reading clears it */
	virtual int takeLateMs() { return 0; }

	/** A word arrived that does not open this service; reading clears it */
	virtual bool takeBadKey() { return false; }

	/** A raise pushes the periods in flight that much further out */
	virtual void creditPeriods(int /*ms*/) { /* Default for services without software descrambling. */ }

	/** Hand out a period nothing opens unchanged, marked scrambled */
	virtual void setKeepUnopened(bool /*on*/) { /* Default for services without software descrambling. */ }

	virtual bool hasKeys() const { return true; }
};

#endif // __iservicescrambled_h
