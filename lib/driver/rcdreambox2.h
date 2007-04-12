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
	int getRepeatDelay();
	int getRepeatRate();
	int getKeyCode(int key);
public:
	void handleCode(int code);
	eRCDeviceDreambox2(eRCDriver *driver);
	const char *getDescription() const;
};

class eRCDeviceDreamboxButton: public eRCDevice
{
	int last;
	eTimer repeattimer;
private:
	void repeat();
	int getRepeatDelay();
	int getRepeatRate();
	int getKeyCode(int button);
public:
	void handleCode(int code);
	eRCDeviceDreamboxButton(eRCDriver *driver);
	const char *getDescription() const;
};

#endif

#endif // DISABLE_DREAMBOX_RC
