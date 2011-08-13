#ifndef __avswitch_h
#define __avswitch_h

#include <lib/base/object.h>
#include <lib/python/connections.h>

class eSocketNotifier;

class eAVSwitch: public Object
{
	static eAVSwitch *instance;
	int m_video_mode;
	bool m_active;
	ePtr<eSocketNotifier> m_fp_notifier;
	void fp_event(int what);
	int m_fp_fd;
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
	int getVCRSlowBlanking();
	void setColorFormat(int format);
	void setAspectRatio(int ratio);
	void setVideomode(int mode);
	void setInput(int val);
	void setWSS(int val);
	bool isActive();
	PSignal1<void, int> vcr_sb_notifier;
};

#endif
