#ifndef __avswitch_h
#define __avswitch_h

class eAVSwitch
{
	static eAVSwitch *instance;
	
	int avsfd;
protected:	
public:
	eAVSwitch();
	~eAVSwitch();

	static eAVSwitch *getInstance();

	void setColorFormat(int format);
};

#endif
