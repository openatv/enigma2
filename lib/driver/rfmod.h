#ifdef ENABLE_RFMOD

#ifndef __erfmod_h
#define __erfmod_h

#include <lib/base/ebase.h>

class eRFmod: public Object
{
	static eRFmod *instance;

	int rfmodfd;
	int channel,soundsubcarrier,soundenable,finetune;

public:
	eRFmod();
	~eRFmod();

	void init();

	static eRFmod *getInstance();

	int save();

	int setChannel(int channel);
	int setSoundSubCarrier(int val);
	int setSoundEnable(int val);
	int setFinetune(int val);
	int setTestPattern(int val);
};
#endif

#endif // ENABLE_RFMOD
