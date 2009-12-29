#ifndef __rcdbox_h
#define __rcdbox_h

#include <lib/driver/rc.h>

class eRCDeviceInputDev: public eRCDevice
{
	int iskeyboard;
public:
	void handleCode(long code);
	eRCDeviceInputDev(eRCInputEventDriver *driver);
	const char *getDescription() const;
	void setExclusive(bool);
};

#endif
