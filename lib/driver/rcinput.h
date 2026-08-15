#ifndef __rcdbox_h
#define __rcdbox_h

#include <lib/driver/rc.h>

class eRCDeviceInputDev: public eRCDevice
{
	int iskeyboard, isgamepad, ismouse;
	int consoleFd;
	bool shiftState, capsState;
	std::unordered_map<unsigned int, unsigned int> remaps;
	std::unordered_map<unsigned int, int> gamepadAxisStates;
	int getGamepadButtonKey(unsigned int code) const;
	void handleGamepadAxis(const struct input_event &event);
public:
	void handleCode(long code);
	eRCDeviceInputDev(eRCInputEventDriver *driver, int consolefd);
	const char *getDescription() const;
	void setExclusive(bool);
	int setKeyMapping(const std::unordered_map<unsigned int, unsigned int>& remaps);
};

#endif
