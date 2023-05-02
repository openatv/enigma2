#ifndef __avcontrol_h
#define __avcontrol_h

#include <lib/base/object.h>

class eAVControl
{

#ifdef SWIG
	eAVControl();
#endif

public:
#ifndef SWIG
	eAVControl();
#endif
	static eAVControl &getInstance()
	{
		static eAVControl m_instance;
		return m_instance;
	}

	int getAspect(int defaultVal = 0, int flags = 0) const;
	int getFrameRate(int defaultVal = 50, int flags = 0) const;
	bool getProgressive(int flags = 0) const;
	int getResolutionX(int defaultVal = 0, int flags = 0) const;
	int getResolutionY(int defaultVal = 0, int flags = 0) const;
	std::string getVideoMode(const std::string &defaultVal = "", int flags = 0) const;

	void setVideoMode(const std::string &newMode, int flags = 0) const;
	bool setHDMIInFull(int flags = 0) const;
	bool setHDMIInPiP(int flags = 0) const;
	void disableHDMIIn(int flags = 0) const;

	bool hasProcAspect() { return m_b_has_proc_aspect; }
	bool hasProcHDMIRXMonitor() { return m_b_has_proc_hdmi_rx_monitor; }
	bool hasProcVideoMode50() { return m_b_has_proc_videomode_50; }
	bool hasProcVideoMode60() { return m_b_has_proc_videomode_60; }

	enum
	{
		FLAGS_DEBUG = 1,
		FLAGS_SUPPRESS_NOT_EXISTS = 2,
		FLAGS_SUPPRESS_READWRITE_ERROR = 4
	};

private:
	std::string m_video_mode;
	std::string m_video_mode_50;
	std::string m_video_mode_60;

	bool m_b_has_proc_aspect;
	bool m_b_has_proc_hdmi_rx_monitor;
	bool m_b_has_proc_videomode_50;
	bool m_b_has_proc_videomode_60;
};

#endif
