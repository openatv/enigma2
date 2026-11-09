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

	/** The stream cannot be descrambled right now and should be held back */
	virtual bool holdPlayback() { return false; }

	/** The playback delay has grown, so the periods in flight come out later */

	virtual bool hasKeys() const { return true; }
};

#endif // __iservicescrambled_h
