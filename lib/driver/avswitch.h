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
	
	void setFastBlank(int val);
	void setColorFormat(int format);
	void setAspectRatio(int ratio);
	void setVideomode(int mode);
	void setInput(int val);

};

#endif
