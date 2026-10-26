/*
Copyright (c) 2023-2025 OpenATV, jbleyel

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.
*/

#ifndef __avcontrol_h
#define __avcontrol_h

#include <lib/base/object.h>
#include <lib/python/connections.h>
#include <set>
#include <map>
#include <utility>

class eSocketNotifier;
class eTimer;

class eAVControl : public sigc::trackable
{
	void fp_event(int what);

#ifdef SWIG
	eAVControl();
	~eAVControl();
#endif

public:
#ifndef SWIG
	eAVControl();
	~eAVControl();
#endif

	static eAVControl *getInstance()
	{
		return m_instance;
	}
	int getAspect(int defaultVal = 0, int flags = 0) const;
	int getFrameRate(int defaultVal = 50000, int flags = 0) const;
	bool getProgressive(int flags = 0) const;
	int getResolutionX(int defaultVal = 0, int flags = 0) const;
	int getResolutionY(int defaultVal = 0, int flags = 0) const;
	std::string getVideoMode(const std::string &defaultVal = "", int flags = 0) const;
	std::string getPreferredModes(int flags = 0) const;
	std::string getAvailableModes() const;
	std::string normalizeVideoMode(const std::string &mode) const;
	std::string getDriverVideoMode(const std::string &mode) const;
	std::string getVideoAxis(const std::string &mode) const;
	bool hasVideoAxis() const;
	bool isEncoderActive() const;

	void setAspectRatio(int ratio, int flags = 0) const;
	void setAspect(const std::string &newFormat, int flags = 0) const;
	void setColorFormat(const std::string &newFormat, int flags = 0) const;
	void setHDMIColordepth(const std::string &colordepth, int flags = 0);

	void setVideoMode(const std::string &newMode, int flags = 0) const;
	void setVideoModeMulti(const std::string &mode50, const std::string &mode60, const std::string &mode24, int flags = 0) const;
	void setInput(const std::string &newMode, int flags = 0);
	void startStopHDMIIn(bool on, bool audio, int flags = 0);
	void disableHDMIIn(int flags = 0) const;
	void setOSDAlpha(int alpha, int flags = 0) const;
	void setOSDAutoHideTimeout(int seconds);
	bool isOSDAutoHidden() const { return m_osdHidden; }
	bool isOSDAutoHidePaused() const { return m_osdHidePaused; }
	PSignal1<void, int> osdAutoHidePauseChanged;
#ifndef SWIG
	void setOSDWindowVisible(const void *window, bool visible);
	bool handleOSDKey(const std::string &device, int key, int flags);
#endif

	bool hasProcHDMIRXMonitor() const { return m_b_has_proc_hdmi_rx_monitor; }
	bool hasProcVideoMode50() const { return m_b_has_proc_videomode_50; }
	bool hasProcVideoMode60() const { return m_b_has_proc_videomode_60; }
	bool hasScartSwitch() const;
	bool has24hz() const { return m_b_has_proc_videomode_24; }
	bool hasOSDAlpha() const { return m_b_has_proc_osd_alpha; }

	void setWSS(int val, int flags = 0) const;
	void setPolicy43(const std::string &newPolicy, int flags = 0) const;
	void setPolicy169(const std::string &newPolicy, int flags = 0) const;

	void setVideoSize(int top, int left, int width, int height, int flags = 0) const;

	std::string getEDIDPath() const;

	enum
	{
		FLAGS_DEBUG = 1,
		FLAGS_SUPPRESS_NOT_EXISTS = 2,
		FLAGS_SUPPRESS_READWRITE_ERROR = 4
	};
	PSignal1<void, int> vcr_sb_notifier;
	int getVCRSlowBlanking();

private:
	ePtr<eTimer> m_osdHideTimer;
	ePtr<eTimer> m_osdFadeTimer;
	int m_osdFadeStep = 0;
	bool m_osdHidePaused = false;
	bool m_osdReplayZero = false;
	std::map<std::pair<std::string, int>, int> m_osdZeroKeys;
	int m_osdHideTimeout = 0;
	mutable int m_osdAlpha = 255;
	mutable bool m_osdHidden = false;
	std::set<const void *> m_osdWindows;
	std::set<std::pair<std::string, int> > m_osdWakeKeys;
	int writeOSDAlpha(int alpha, int flags = 0) const;
	void hideOSD();
	void fadeOSD();
	void restoreOSD();
	void restartOSDTimer();
	static eAVControl *m_instance;
	std::string m_video_mode;
	std::string m_video_mode_50;
	std::string m_video_mode_60;
	std::string m_videomode_choices;
	std::string m_standby_video_mode;
	std::string m_hdmi_colordepth = "auto";

	bool m_b_has_proc_osd_alpha;
	bool m_b_has_proc_hdmi_rx_monitor;
	bool m_b_has_proc_videomode_50;
	bool m_b_has_proc_videomode_60;
	bool m_b_has_proc_videomode_24;
	bool m_encoder_active;
	bool m_b_has_scartswitch;
	bool m_b_hdmiin_fhd;
	int m_fp_fd;

	ePtr<eSocketNotifier> m_fp_notifier;

	std::string readAvailableModes(int flags = 0) const;
	void writeHDMIColorFormat(const std::string &driverMode, int flags = 0) const;
	void applyHDMIColorFormat(int flags = 0) const;
	bool checkScartSwitch(int flags = 0) const;
};

#endif
