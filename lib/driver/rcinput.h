#ifndef __rcdbox_h
#define __rcdbox_h

#include <lib/driver/rc.h>

class eRCDeviceInputDev: public eRCDevice
{
	int iskeyboard, ismouse;
	int consoleFd;
	bool shiftState, capsState;
	std::unordered_map<unsigned int, unsigned int> remaps;
public:
	void handleCode(long code);
	eRCDeviceInputDev(eRCInputEventDriver *driver, int consolefd);
	const char *getDescription() const;
	void setExclusive(bool);
	int setKeyMapping(const std::unordered_map<unsigned int, unsigned int>& remaps);
};

#endif
