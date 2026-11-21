#ifndef __servicedvbfcc_h
#define __servicedvbfcc_h

#include <lib/service/servicedvb.h>
#include <list>

#include <lib/dvb/fcc.h>

class eDVBServiceFCCPlay: public eDVBServicePlay
{
	DECLARE_REF(eDVBServiceFCCPlay);
public:
	eDVBServiceFCCPlay(const eServiceReference &ref, eDVBService *service);
	virtual ~eDVBServiceFCCPlay();
	void serviceEvent(int event);
	RESULT start();
protected:
	void pushbackFCCEvents(int event);
	void popFCCEvents();
	void changeFCCMode();
	void processNewProgramInfo(bool toLive=false);
	void updateFCCDecoder(bool sendSeekableStateChanged=false);
	void FCCDecoderStop();
	void switchToLive();
	bool checkUsbTuner();
	bool getFCCStateDecoding();
	void setNormalDecoding();

	bool m_fcc_enable;

	enum {
		fcc_start		= 1,
		fcc_tune_failed	= 2,
		fcc_failed		= 4,
		fcc_ready		= 8,
		fcc_decoding		= 16,
		fcc_novideo		= 32,
	};
	int m_fcc_flag;

	enum {
		fcc_mode_preparing,
		fcc_mode_decoding
	};
	int m_fcc_mode;

	bool m_fcc_mustplay;
	std::list<int> m_fcc_events;
	int m_pmtVersion;
	bool m_normal_decoding;
};

#endif /* __servicedvbfcc_h */
