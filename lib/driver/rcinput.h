#ifndef __rcdbox_h
#define __rcdbox_h

#include <lib/driver/rc.h>

class eRCDeviceInputDev: public eRCDevice
{
public:
	void handleCode(int code);
	eRCDeviceInputDev(eRCInputEventDriver *driver);
	const char *getDescription() const;

	const char *getKeyDescription(const eRCKey &key) const;
	int getKeyCompatibleCode(const eRCKey &key) const;
};

#endif
