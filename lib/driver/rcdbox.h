#ifndef DISABLE_DBOX_RC

#ifndef __rcdbox_h
#define __rcdbox_h

#include <lib/driver/rc.h>

class eRCDeviceDBoxOld: public eRCDevice
{
	int last, ccode;
	eTimer timeout, repeattimer;
private:
	void timeOut();
	void repeat();
public:
	void handleCode(int code);
	eRCDeviceDBoxOld(eRCDriver *driver);
	const char *getDescription() const;
	const char *getKeyDescription(const eRCKey &key) const;
	int getKeyCompatibleCode(const eRCKey &key) const;
};

class eRCDeviceDBoxNew: public eRCDevice
{
	int last, ccode;
	eTimer timeout, repeattimer;
private:
	void timeOut();
	void repeat();
public:
	void handleCode(int code);
	eRCDeviceDBoxNew(eRCDriver *driver);
	const char *getDescription() const;
	const char *getKeyDescription(const eRCKey &key) const;
	int getKeyCompatibleCode(const eRCKey &key) const;
};

class eRCDeviceDBoxButton: public eRCDevice
{
	int last;
	eTimer repeattimer;
private:
	void repeat();
public:
	void handleCode(int code);
	eRCDeviceDBoxButton(eRCDriver *driver);
	const char *getDescription() const;

	const char *getKeyDescription(const eRCKey &key) const;
	int getKeyCompatibleCode(const eRCKey &key) const;
};

class eRCDBoxDriver: public eRCShortDriver
{
public:
	eRCDBoxDriver();
};

#endif

#endif // DISABLE_DBOX_RC
