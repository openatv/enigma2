#ifndef __avswitch_h
#define __avswitch_h

class eAVSwitch
{
	static eAVSwitch *instance;
	
protected:	
public:
	eAVSwitch();
	~eAVSwitch();

	static eAVSwitch *getInstance();

	void setColorFormat(int format);
	void setAspectRatio(int ratio);
	void setVideomode(int mode);
};

#endif
