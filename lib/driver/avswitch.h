#ifndef __avswitch_h
#define __avswitch_h

class eAVSwitch
{
	static eAVSwitch *instance;
	int m_video_mode;
#ifdef SWIG
	eAVSwitch();
	~eAVSwitch();
#endif
protected:
public:
#ifndef SWIG
	eAVSwitch();
	~eAVSwitch();
#endif
	static eAVSwitch *getInstance();
	
	void setFastBlank(int val);
	void setColorFormat(int format);
	void setAspectRatio(int ratio);
	void setVideomode(int mode);
	void setInput(int val);
	void setSlowblank(int val);
	void setWSS(int val);
};

#endif
