#ifndef __rcdbox_h
#define __rcdbox_h

#include <lib/driver/rc.h>

class eRCDeviceInputDev: public eRCDevice
{
	int iskeyboard;
public:
	void handleCode(int code);
	eRCDeviceInputDev(eRCInputEventDriver *driver);
	const char *getDescription() const;
};

#endif
