#ifndef __avswitch_h
#define __avswitch_h

#include <lib/base/object.h>
#include <lib/python/connections.h>

class eAVSwitch
{
	static eAVSwitch *instance;
	int m_video_mode;
	bool m_active;
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
	bool haveScartSwitch();
	void setColorFormat(int format);
	void setAspectRatio(int ratio);
	void setVideomode(int mode);
	void setInput(int val);
	void setWSS(int val);
	bool isActive();
};

#endif
