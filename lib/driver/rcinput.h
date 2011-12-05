#ifndef __rcdbox_h
#define __rcdbox_h

#include <lib/driver/rc.h>

class eRCDeviceInputDev: public eRCDevice
{
	int iskeyboard, ismouse;
	int consoleFd;
	bool shiftState, capsState;
public:
	void handleCode(long code);
	eRCDeviceInputDev(eRCInputEventDriver *driver, int consolefd);
	const char *getDescription() const;
	void setExclusive(bool);
};

#endif
