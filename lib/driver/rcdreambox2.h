#ifndef DISABLE_DREAMBOX_RC

#ifndef __rcdreambox2_h
#define __rcdreambox2_h

#include <lib/driver/rc.h>

class eRCDeviceDreambox2: public eRCDevice
{
	int last, ccode;
	eTimer timeout, repeattimer;
private:
	void timeOut();
	void repeat();
public:
	void handleCode(int code);
	eRCDeviceDreambox2(eRCDriver *driver);
	const char *getDescription() const;
	const char *getKeyDescription(const eRCKey &key) const;
	int getKeyCompatibleCode(const eRCKey &key) const;
};

class eRCDreamboxDriver2: public eRCShortDriver
{
public:
	eRCDreamboxDriver2();
};

class eRCDeviceDreamboxButton: public eRCDevice
{
	int last;
	eTimer repeattimer;
private:
	void repeat();
public:
	void handleCode(int code);
	eRCDeviceDreamboxButton(eRCDriver *driver);
	const char *getDescription() const;

	const char *getKeyDescription(const eRCKey &key) const;
	int getKeyCompatibleCode(const eRCKey &key) const;
};

class eRCDreamboxButtonDriver: public eRCShortDriver
{
public:
	eRCDreamboxButtonDriver();
};
#endif

#endif // DISABLE_DREAMBOX_RC
