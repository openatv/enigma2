#ifndef __avcontrol_h
#define __avcontrol_h

#include <lib/base/object.h>
#include <lib/python/connections.h>

class eSocketNotifier;

class eAVControl: public sigc::trackable
{
	ePtr<eSocketNotifier> m_fp_notifier;
	void fp_event(int what);
	int m_fp_fd;

#ifdef SWIG
	eAVControl();
	~eAVControl();
#endif

public:
#ifndef SWIG
	eAVControl();
	~eAVControl();
#endif

	static eAVControl *getInstance() { return m_instance; }
	int getAspect(int defaultVal = 0, int flags = 0) const;
	int getFrameRate(int defaultVal = 50, int flags = 0) const;
	bool getProgressive(int flags = 0) const;
	int getResolutionX(int defaultVal = 0, int flags = 0) const;
	int getResolutionY(int defaultVal = 0, int flags = 0) const;
	std::string getVideoMode(const std::string &defaultVal = "", int flags = 0) const;
	std::string getPreferredModes(int flags = 0) const;
	std::string getAvailableModes() const;
	bool isVideoOutputActive() const;

	void setAspectRatio(int ratio, bool setPolicy = true, int flags = 0) const;
	void setColorFormat(const std::string &newFormat, int flags) const;

	void setVideoMode(const std::string &newMode, int flags = 0) const;
	void setVideoOutput(std::string newMode, int flags = 0);
	void startStopHDMIIn(bool on, bool audio, int flags = 0);
	void disableHDMIIn(int flags = 0) const;

	bool hasProcAspect() const { return m_b_has_proc_aspect; }
	bool hasProcHDMIRXMonitor() const { return m_b_has_proc_hdmi_rx_monitor; }
	bool hasProcVideoMode50() const { return m_b_has_proc_videomode_50; }
	bool hasProcVideoMode60() const { return m_b_has_proc_videomode_60; }
	bool hasScartSwitch() const;
	bool has24hz() const { return m_b_has_proc_videomode_24; }

	enum
	{
		FLAGS_DEBUG = 1,
		FLAGS_SUPPRESS_NOT_EXISTS = 2,
		FLAGS_SUPPRESS_READWRITE_ERROR = 4
	};
	PSignal1<void, int> vcr_sb_notifier;
	int getVCRSlowBlanking();

private:
	static eAVControl *m_instance;
	std::string m_video_mode;
	std::string m_video_mode_50;
	std::string m_video_mode_60;
	std::string m_videomode_choices;

	bool m_b_has_proc_aspect;
	bool m_b_has_proc_hdmi_rx_monitor;
	bool m_b_has_proc_videomode_50;
	bool m_b_has_proc_videomode_60;
	bool m_b_has_proc_videomode_24;
	bool m_video_output_active;
	bool m_b_has_scartswitch;
	bool m_b_hdmiin_fhd;

	std::string readAvailableModes(int flags = 0) const;
	bool checkScartSwitch(int flags = 0) const;
};

#endif
