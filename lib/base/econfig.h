#ifndef __econfig_h
#define __econfig_h

#include <lib/base/nconfig.h>

class eConfig: public NConfig
{
	static eConfig *instance;
	int ppin;
public:
	int locked;
	static eConfig *getInstance() { return instance; }
	void setParentalPin( int pin )
	{
		 ppin = pin;
		 setKey("/elitedvb/pins/parentallock", ppin );
	}
	int getParentalPin() { return ppin; }
	bool pLockActive()
	{
		return ppin && locked;
	}
	eConfig();
	~eConfig();
};

#endif
