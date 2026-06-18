/*
Copyright (c) 2023-2025 OpenATV, jbleyel

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.
*/

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>
#include <algorithm>
#include <cstdlib>
#include <regex>

#include <lib/base/cfile.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/base/modelinformation.h>
#include <lib/driver/avcontrol.h>

const char *__MODULE__ = "eAVControl"; // NOSONAR

const char *proc_hdmi_rx_monitor = "/proc/stb/hdmi-rx/0/hdmi_rx_monitor";	// NOSONAR
const char *proc_hdmi_rx_monitor_audio = "/proc/stb/audio/hdmi_rx_monitor"; // NOSONAR
#ifdef DREAMNEXTGEN
const char *proc_policy169 = "/sys/class/video/screen_mode";	 // NOSONAR
const char *proc_policy43 = "/sys/class/video/screen_mode";		 // NOSONAR
const char *proc_videomode = "/sys/class/display/mode";			 // NOSONAR
const char *proc_videoaspect_r = "/sys/class/video/screen_mode"; // NOSONAR
const char *proc_videoaspect_w = "/sys/class/video/screen_mode"; // NOSONAR
const char *proc_osd_alpha = "/sys/class/graphics/fb0/osd_plane_alpha";	 // NOSONAR
#else
const char *proc_policy169 = "/proc/stb/video/policy2";		 // NOSONAR
const char *proc_policy43 = "/proc/stb/video/policy";		 // NOSONAR
const char *proc_videomode = "/proc/stb/video/videomode";	 // NOSONAR
const char *proc_videoaspect_r = "/proc/stb/vmpeg/0/aspect"; // NOSONAR
const char *proc_videoaspect_w = "/proc/stb/video/aspect";	 // NOSONAR
const char *proc_osd_alpha = "/proc/stb/video/alpha";	 // NOSONAR
#endif
const char *proc_videomode_50 = "/proc/stb/video/videomode_50hz"; // NOSONAR
const char *proc_videomode_60 = "/proc/stb/video/videomode_60hz"; // NOSONAR
const char *proc_videomode_24 = "/proc/stb/video/videomode_24hz"; // NOSONAR

const char *proc_wss = "/proc/stb/denc/0/wss"; // NOSONAR

eAVControl *eAVControl::m_instance = nullptr;

/// @brief Normalize a driver video mode to the Enigma2 config value
/// @param mode Driver or config video mode
/// @return normalized video mode
std::string eAVControl::normalizeVideoMode(const std::string &mode) const
{
	std::string result = mode;
	result.erase(std::remove(result.begin(), result.end(), '\n'), result.end());
	result.erase(std::remove(result.begin(), result.end(), '\r'), result.end());

#ifdef DREAMNEXTGEN
	if (result.length() > 2 && result.compare(result.length() - 2, 2, "hz") == 0)
		result.erase(result.length() - 2);

	if (result == "480i60")
		result = "480i";
	else if (result == "576i50")
		result = "576i";
	else if (result == "480p60")
		result = "480p";
	else if (result == "576p50")
		result = "576p";
	else if (result == "720p60")
		result = "720p";
	else if (result == "1080i60")
		result = "1080i";
	else if (result == "1080p60")
		result = "1080p";
	else if (result == "2160p60")
		result = "2160p";
#endif

	return result;
}

/// @brief Convert an Enigma2 config video mode to the driver video mode
/// @param mode normalized video mode
/// @return driver video mode
std::string eAVControl::getDriverVideoMode(const std::string &mode) const
{
#ifdef DREAMNEXTGEN
	if (mode.empty() || mode == "PAL" || mode == "NTSC" || mode == "pal" || mode == "pal60" || mode == "ntsc" || mode.find("hz") != std::string::npos)
		return mode;
	if (mode == "480i")
		return "480i60hz";
	if (mode == "576i")
		return "576i50hz";
	if (mode == "480p")
		return "480p60hz";
	if (mode == "576p")
		return "576p50hz";
	if (mode == "720p")
		return "720p60hz";
	if (mode == "1080i")
		return "1080i60hz";
	if (mode == "1080p")
		return "1080p60hz";
	if (mode == "2160p")
		return "2160p60hz";
	return mode + "hz";
#else
	return mode;
#endif
}

/// @brief Get video axis for the current video mode
/// @param mode normalized video mode
/// @return video axis
std::string eAVControl::getVideoAxis(const std::string &mode) const
{
#ifdef DREAMNEXTGEN
	std::string value = normalizeVideoMode(mode);
	if (value.find("480") == 0)
		return "0 0 719 479";
	if (value.find("576") == 0)
		return "0 0 719 575";
	if (value.find("720") == 0)
		return "0 0 1279 719";
	if (value.find("1080") == 0)
		return "0 0 1919 1079";
	if (value.find("2160") == 0)
		return "0 0 3839 2159";
	if (value.find("smpte") == 0)
		return "0 0 4095 2159";
#endif
	return "0 0 719 575";
}

/// @brief Check if video axis handling is available
/// @return true if video axis handling is available
bool eAVControl::hasVideoAxis() const
{
#ifdef DREAMNEXTGEN
	return true;
#else
	return false;
#endif
}

eAVControl::eAVControl()
{
	struct stat buffer = {};

#ifdef HAVE_HDMIIN_DM
	m_b_has_proc_hdmi_rx_monitor = (stat(proc_hdmi_rx_monitor, &buffer) == 0);
#else
	m_b_has_proc_hdmi_rx_monitor = false;
#endif

	m_b_has_proc_videomode_50 = (stat(proc_videomode_50, &buffer) == 0);
	m_b_has_proc_videomode_60 = (stat(proc_videomode_60, &buffer) == 0);

#ifdef DREAMNEXTGEN
	m_b_has_proc_videomode_24 = true;
	m_b_has_proc_osd_alpha = true;
#else
	m_b_has_proc_videomode_24 = (access(proc_videomode_24, W_OK) == 0);
	m_b_has_proc_osd_alpha = (access(proc_osd_alpha, W_OK) == 0);
#endif

	m_videomode_choices = readAvailableModes();
	m_encoder_active = false;

	eModelInformation &modelinformation = eModelInformation::getInstance();
	m_b_has_scartswitch = modelinformation.getValue("scart") == "True";
	if (m_b_has_scartswitch)
	{
		m_b_has_scartswitch = modelinformation.getValue("noscartswitch") != "True";
		if (m_b_has_scartswitch)
			m_b_has_scartswitch = checkScartSwitch();
	}

	m_b_hdmiin_fhd = modelinformation.getValue("hdmifhdin") == "True";

	eDebug("[%s] Init: ScartSwitch:%d / VideoMode 24:%d 50:%d 60:%d / HDMIRxMonitor:%d", __MODULE__, m_b_has_scartswitch, m_b_has_proc_videomode_24, m_b_has_proc_videomode_50, m_b_has_proc_videomode_60, m_b_has_proc_hdmi_rx_monitor);
	eDebug("[%s] Init: VideoMode Choices:%s", __MODULE__, m_videomode_choices.c_str());
	m_instance = this;
	m_fp_fd = -1;

	if (modelinformation.getValue("scart") == "True")
	{

		m_fp_fd = open("/dev/dbox/fp0", O_RDONLY | O_NONBLOCK);
		if (m_fp_fd == -1)
		{
			eDebug("[%s] failed to open /dev/dbox/fp0 to monitor vcr scart slow blanking changed: %m", __MODULE__);
			m_fp_notifier = nullptr;
		}
		else
		{
			m_fp_notifier = eSocketNotifier::create(eApp, m_fp_fd, eSocketNotifier::Read | POLLERR);
			CONNECT(m_fp_notifier->activated, eAVControl::fp_event);
		}
	}
}

#ifndef FP_IOCTL_GET_EVENT
#define FP_IOCTL_GET_EVENT 20
#endif

#ifndef FP_IOCTL_GET_VCR
#define FP_IOCTL_GET_VCR 7
#endif

#ifndef FP_EVENT_VCR_SB_CHANGED
#define FP_EVENT_VCR_SB_CHANGED 1
#endif

int eAVControl::getVCRSlowBlanking()
{
	int val = 0;
	if (m_fp_fd >= 0)
	{
		CFile f("/proc/stb/fp/vcr_fns", "r");
		if (f)
		{
			if (fscanf(f, "%d", &val) != 1)
				eDebug("[%s] read /proc/stb/fp/vcr_fns failed: %m", __MODULE__);
		}
		else if (ioctl(m_fp_fd, FP_IOCTL_GET_VCR, &val) < 0)
			eDebug("[%s] FP_GET_VCR failed: %m", __MODULE__);
	}
	return val;
}

void eAVControl::fp_event(int what)
{
	if (what & POLLERR) // driver not ready for fp polling
	{
		eDebug("[%s] fp driver not read for polling.. so disable polling", __MODULE__);
		m_fp_notifier->stop();
	}
	else
	{
		CFile f("/proc/stb/fp/events", "r");
		if (f)
		{
			int events;
			if (fscanf(f, "%d", &events) != 1)
				eDebug("[%s] read /proc/stb/fp/events failed: %m", __MODULE__);
			else if (events & FP_EVENT_VCR_SB_CHANGED)
				/* emit */ vcr_sb_notifier(getVCRSlowBlanking());
		}
		else
		{
			int val = FP_EVENT_VCR_SB_CHANGED; // ask only for this event
			if (ioctl(m_fp_fd, FP_IOCTL_GET_EVENT, &val) < 0)
				eDebug("[%s] FP_IOCTL_GET_EVENT failed: %m", __MODULE__);
			else if (val & FP_EVENT_VCR_SB_CHANGED)
				/* emit */ vcr_sb_notifier(getVCRSlowBlanking());
		}
	}
}

eAVControl::~eAVControl()
{
	m_instance = nullptr;
	if (m_fp_fd >= 0)
		close(m_fp_fd);
}

/// @brief Get video aspect
/// @param defaultVal
/// @param flags
/// @return
int eAVControl::getAspect(int defaultVal, int flags) const
{
	int value = 0;
	int ret = CFile::parseIntHex(&value, proc_videoaspect_r, __MODULE__, flags);
	if (ret != 0)
	{
		value = defaultVal;
	}
	else if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "getAspect", value);
	return value;
}

/// @brief Get progressive
/// @param flags
/// @return
bool eAVControl::getProgressive(int flags) const
{
#ifdef DREAMNEXTGEN
	std::string value = CFile::read("/sys/devices/platform/deinterlace/deinterlace/di0/frame_format", __MODULE__, flags);
	value.erase(std::remove(value.begin(), value.end(), '\n'), value.end());
	value.erase(std::remove(value.begin(), value.end(), '\r'), value.end());
	bool progressive = value != "interlace" && value != "interlaced";
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d (%s)", __MODULE__, "getProgressive", progressive, value.c_str());
	return progressive;
#else
	int value = 0;
	CFile::parseIntHex(&value, "/proc/stb/vmpeg/0/progressive", __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "getProgressive", value);
	return value == 1;
#endif
}

/// @brief Get screen resolution X
/// @param defaultVal = 0
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return resolution value
int eAVControl::getResolutionX(int defaultVal, int flags) const
{
	int value;
#ifdef DREAMNEXTGEN
	int ret = CFile::parseInt(&value, "/sys/class/video/frame_width",
				  __MODULE__, flags | FLAGS_SUPPRESS_READWRITE_ERROR);
#else
	int ret = CFile::parseIntHex(&value, "/proc/stb/vmpeg/0/xres", __MODULE__, flags);
#endif

	if (ret != 0)
	{
		value = defaultVal;
	}
	else if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "getResolutionX", value);

	return value;
}

/// @brief Get screen resolution Y
/// @param defaultVal = 0
/// @param flags bit (1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return resolution value
int eAVControl::getResolutionY(int defaultVal, int flags) const
{

	int value;
#ifdef DREAMNEXTGEN
	int ret = CFile::parseInt(&value, "/sys/class/video/frame_height",
				  __MODULE__, flags | FLAGS_SUPPRESS_READWRITE_ERROR);
#else
	int ret = CFile::parseIntHex(&value, "/proc/stb/vmpeg/0/yres", __MODULE__, flags);
#endif

	if (ret != 0)
	{
		value = defaultVal;
	}
	else if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "getResolutionY", value);
	return value;
}

/// @brief Get FrameRate
/// @param defaultVal
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return
int eAVControl::getFrameRate(int defaultVal, int flags) const
{

#ifdef DREAMNEXTGEN
	std::string fpsInfo = CFile::read("/sys/class/video/fps_info", __MODULE__, flags);
	std::smatch match;
	int value = defaultVal;
	if (std::regex_search(fpsInfo, match, std::regex("input_fps:0x([0-9a-fA-F]+)")))
	{
		int fps = std::stoi(match[1].str(), nullptr, 16);
		if (fps > 0)
			value = fps * 1000;
	}
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d (%s)", __MODULE__, "getFrameRate", value, fpsInfo.c_str());
	return value;
#else
#ifdef DREAMBOX
	const char *fileName = "/proc/stb/vmpeg/0/fallback_framerate";
#else
	const char *fileName = "/proc/stb/vmpeg/0/framerate";
#endif

	int value = 0;
	int ret = CFile::parseInt(&value, fileName, __MODULE__, flags);
	if (ret != 0)
	{
		value = defaultVal;
	}
	else if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "getFrameRate", value);

	return value;
#endif
}

/// @brief Get VideoMode
/// @param defaultVal
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return
std::string eAVControl::getVideoMode(const std::string &defaultVal, int flags) const
{
#ifdef VIDEO_MODE_50
	std::string result = CFile::read(proc_videomode_50, __MODULE__, flags);
#else
	std::string result = CFile::read(proc_videomode, __MODULE__, flags);
#endif
	result = normalizeVideoMode(result);
	if (result.empty())
		result = defaultVal;
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "getVideoMode", result.c_str());

	return result;
}

/// @brief Set VideoMode
/// @param newMode
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setVideoMode(const std::string &newMode, int flags) const
{
	std::string driverMode = getDriverVideoMode(newMode);
#ifdef VIDEO_MODE_50
	// gigablue driver bug
	CFile::writeStr(proc_videomode_50, driverMode, __MODULE__, flags);
	CFile::writeStr(proc_videomode_60, driverMode, __MODULE__, flags);
#else
	CFile::writeStr(proc_videomode, driverMode, __MODULE__, flags);
#endif
#ifdef DREAMNEXTGEN
	CFile::writeStr("/etc/u-boot.scr.d/000_hdmimode.scr", "setenv hdmimode " + driverMode, __MODULE__, flags | FLAGS_SUPPRESS_NOT_EXISTS);
	CFile::writeStr("/etc/u-boot.scr.d/000_outputmode.scr", "setenv outputmode " + driverMode, __MODULE__, flags | FLAGS_SUPPRESS_NOT_EXISTS);
	(void)std::system("update-autoexec");
	CFile::writeStr("/sys/class/ppmgr/ppscaler", "1", __MODULE__, flags | FLAGS_SUPPRESS_NOT_EXISTS);
	CFile::writeStr("/sys/class/ppmgr/ppscaler", "0", __MODULE__, flags | FLAGS_SUPPRESS_NOT_EXISTS);
	CFile::writeStr("/sys/class/video/axis", getVideoAxis(newMode), __MODULE__, flags);
#endif

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s (%s)", __MODULE__, "setVideoMode", newMode.c_str(), driverMode.c_str());
}

/// @brief Set video modes for 50Hz, 60Hz and 24Hz
/// @param mode50
/// @param mode60
/// @param mode24
/// @param flags
void eAVControl::setVideoModeMulti(const std::string &mode50, const std::string &mode60, const std::string &mode24, int flags) const
{
#ifdef DREAMNEXTGEN
	setVideoMode(!mode50.empty() ? mode50 : (!mode60.empty() ? mode60 : mode24), flags);
#else
	std::string effectiveMode50 = !mode50.empty() ? mode50 : (!mode60.empty() ? mode60 : mode24);
	std::string driverMode50 = getDriverVideoMode(effectiveMode50);
	std::string driverMode60 = getDriverVideoMode(mode60.empty() ? effectiveMode50 : mode60);
	std::string driverMode24 = getDriverVideoMode(mode24.empty() ? (mode60.empty() ? effectiveMode50 : mode60) : mode24);
	if (m_b_has_proc_videomode_50)
		CFile::writeStr(proc_videomode_50, driverMode50, __MODULE__, flags);
	if (m_b_has_proc_videomode_60)
		CFile::writeStr(proc_videomode_60, driverMode60, __MODULE__, flags);
	if (m_b_has_proc_videomode_24)
		CFile::writeStr(proc_videomode_24, driverMode24, __MODULE__, flags);
	// Fallback if no possibility to setup 50/60 hz mode.
	CFile::writeStr(proc_videomode, driverMode50, __MODULE__, flags);
	if (eModelInformation::getInstance().getValue("brand") == "gigablue") // Use 50Hz mode (if available) for booting.
		CFile::writeStr("/etc/videomode", driverMode50, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: 50:%s 60:%s 24:%s", __MODULE__, "setVideoModeMulti", driverMode50.c_str(), driverMode60.c_str(), driverMode24.c_str());
#endif
}

/// @brief startStopHDMIIn
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @param audio
/// @param on
void eAVControl::startStopHDMIIn(bool on, bool audio, int flags)
{

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: audio:%d on:%d", __MODULE__, "startStopHDMIIn", audio, on);

	std::string state = on ? "on" : "off";

	if (on)
	{
		m_video_mode = CFile::read(proc_videomode, __MODULE__, flags);
		if (m_b_has_proc_videomode_50)
			m_video_mode_50 = CFile::read(proc_videomode_50, __MODULE__, flags);
		if (m_b_has_proc_videomode_60)
			m_video_mode_60 = CFile::read(proc_videomode_60, __MODULE__, flags);

		std::string mode = m_b_hdmiin_fhd ? "1080p" : "720p";

		CFile::writeStr(proc_videomode, getDriverVideoMode(mode), __MODULE__, flags);
		if (m_b_has_proc_videomode_50)
			CFile::writeStr(proc_videomode_50, getDriverVideoMode(mode), __MODULE__, flags);
		if (m_b_has_proc_videomode_60)
			CFile::writeStr(proc_videomode_60, getDriverVideoMode(mode), __MODULE__, flags);

		if (m_b_has_proc_hdmi_rx_monitor)
		{
			if (audio)
				CFile::writeStr(proc_hdmi_rx_monitor_audio, state, __MODULE__, flags);
			CFile::writeStr(proc_hdmi_rx_monitor, state, __MODULE__, flags);
		}
	}
	else
	{
		if (m_b_has_proc_hdmi_rx_monitor)
		{
			CFile::writeStr(proc_hdmi_rx_monitor_audio, state, __MODULE__, flags);
			CFile::writeStr(proc_hdmi_rx_monitor, state, __MODULE__, flags);
		}
		CFile::writeStr(proc_videomode, m_video_mode, __MODULE__, flags);
		if (m_b_has_proc_videomode_50)
			CFile::writeStr(proc_videomode_50, m_video_mode_50, __MODULE__, flags);
		if (m_b_has_proc_videomode_60)
			CFile::writeStr(proc_videomode_60, m_video_mode_60, __MODULE__, flags);
	}
}

/// @brief disable HDMIIn / used in StartEnigma.py
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::disableHDMIIn(int flags) const
{
	if (!m_b_has_proc_hdmi_rx_monitor)
		return;

	CFile::writeStr(proc_hdmi_rx_monitor_audio, "off", __MODULE__, flags);
	CFile::writeStr(proc_hdmi_rx_monitor, "off", __MODULE__, flags);
}

/// @brief read the preferred video modes
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return
std::string eAVControl::getPreferredModes(int flags) const
{

#ifdef DREAMNEXTGEN
	const char *fileName = "/sys/class/amhdmitx/amhdmitx0/disp_cap";
#else
	const char *fileName = "/proc/stb/video/videomode_edid";
	const char *fileName2 = "/proc/stb/video/videomode_preferred";
#endif

	std::string result = "";

	if (access(fileName, R_OK) == 0)
	{
		result = CFile::read(fileName, __MODULE__, flags);
		if (!result.empty() && result[result.length() - 1] == '\n')
		{
			result.erase(result.length() - 1);
		}
	}

#ifdef DREAMNEXTGEN
	result = std::regex_replace(result, std::regex("\\*"), "");
	result = std::regex_replace(result, std::regex("\n+"), " ");
	result = std::regex_replace(result, std::regex("hz"), "");
	result = std::regex_replace(result, std::regex("480i60"), "480i");
	result = std::regex_replace(result, std::regex("576i50"), "576i");
	result = std::regex_replace(result, std::regex("480p60"), "480p");
	result = std::regex_replace(result, std::regex("576p50"), "576p");
	result = std::regex_replace(result, std::regex("720p60"), "720p");
	result = std::regex_replace(result, std::regex("1080i60"), "1080i");
	result = std::regex_replace(result, std::regex("1080p60"), "1080p");
	result = std::regex_replace(result, std::regex("2160p60"), "2160p");
#else

	if (result.empty() && access(fileName2, R_OK) == 0)
	{
		result = CFile::read(fileName2, __MODULE__, flags);
		if (!result.empty() && result[result.length() - 1] == '\n')
		{
			result.erase(result.length() - 1);
		}
	}

#endif

	return result;
}

/// @brief read the available video modes It's for internal use only because it will be static.
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return
std::string eAVControl::readAvailableModes(int flags) const
{

#ifdef DREAMNEXTGEN
	return std::string("480i 576i 480p 576p 720p 720p50 1080i 1080i50 1080p 1080p24 1080p25 1080p30 1080p50 2160p24 2160p25 2160p30 2160p50 2160p smpte24 smpte25 smpte30 smpte50 smpte60");
#elif USE_VIDEO_MODE_HD
	return std::string("pal ntsc 720p 720p25 720p30 720p50 1080i 1080i50 1080p25 1080p30 1080p50 1080p 576i 576p 480i 480p");
#else
	const char *fileName = "/proc/stb/video/videomode_choices";
	std::string result = "";
	if (access(fileName, R_OK) == 0)
	{
		result = CFile::read(fileName, __MODULE__, flags);
	}

	if (!result.empty() && result[result.length() - 1] == '\n')
	{
		result.erase(result.length() - 1);
	}
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "readAvailableModes", result.c_str());
	return result;
#endif
}

/// @brief get the available video modes
/// @return
std::string eAVControl::getAvailableModes() const
{
	return m_videomode_choices;
}

/// @brief set the aspect ratio
/// @param ratio
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setAspectRatio(int ratio, int flags) const
{

#ifdef DREAMNEXTGEN

	if (ratio < 0 || ratio > 13)
	{
		eDebug("[%s] %s: invalid value %d", __MODULE__, "setAspectRatio", ratio);
		return;
	}

	CFile::writeInt(proc_videoaspect_w, ratio, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "setAspectRatio", ratio);

		/*

		0 normal
		1 full stretch
		2 4-3
		3 16-9
		4 non-linear
		5 normal-noscaleup
		6 4-3 ignore
		7 4-3 letter box
		8 4-3 pan scan
		9 4-3 combined
		10 16-9 ignore
		11 16-9 letter box
		12 16-9 pan scan
		13 16-9 combined

		*/

#else

	if (ratio < 0 || ratio > 7)
	{
		eDebug("[%s] %s: invalid value %d", __MODULE__, "setAspectRatio", ratio);
		return;
	}

	/*
	0 - 4:3 Letterbox
	1 - 4:3 PanScan
	2 - 16:9
	3 - 16:9 forced ("panscan")
	4 - 16:10 Letterbox
	5 - 16:10 PanScan
	6 - 16:9 forced ("letterbox")
	*/
	const char *aspect[] = {"4:3", "4:3", "any", "16:9", "16:10", "16:10", "16:9"};
	const char *policy[] = {"letterbox", "panscan", "bestfit", "panscan", "letterbox", "panscan", "letterbox"};

	std::string newAspect = aspect[ratio];
	std::string newPolicy = policy[ratio];

	CFile::writeStr(proc_videoaspect_w, newAspect, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setAspectRatio/aspect", newAspect.c_str());

	CFile::writeStr("/proc/stb/video/policy", newPolicy, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setAspectRatio/policy", newPolicy.c_str());
#endif
}

/// @brief setAspect
/// @param newFormat (auto, 4:3, 16:9, 16:10)
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setAspect(const std::string &newFormat, int flags) const
{

#ifdef DREAMNEXTGEN

	std::string newMode = "0";

	if (newFormat == "16:9")
		newMode = "7";
	else if (newFormat == "4:3")
		newMode = "2";
	else if (newFormat == "16:10")
		newMode = "9";

	CFile::writeStr(proc_videoaspect_w, newMode, __MODULE__, flags);
#else
	CFile::writeStr(proc_videoaspect_w, newFormat, __MODULE__, flags);
#endif

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setAspect", newFormat.c_str());
}

/// @brief set video input
/// @param newMode (scart, aux, encoder, off)
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setInput(const std::string &newMode, int flags)
{

#ifdef DREAMNEXTGEN
	m_encoder_active = newMode == "encoder";
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setInput", newMode.c_str());
#else
	std::string newval = newMode;
	if (newMode == "off") // off = aux or scart based on scartswitch used for standby
	{
		newval = m_b_has_scartswitch ? "scart" : "aux";
	}
	else if (newMode != "scart" && newMode != "aux" && newMode != "encoder")
	{
		newval = "encoder"; // set to encoder if not valid
	}

	m_encoder_active = newval == "encoder";

	CFile::writeStr("/proc/stb/avs/0/input", newval, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setInput", newval.c_str());
#endif
}

/// @brief get video output active state
/// @return true/false
bool eAVControl::isEncoderActive() const
{
	return m_encoder_active;
}

/// @brief read input choices and check for scart / it's for internal use only
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return
bool eAVControl::checkScartSwitch(int flags) const
{
	if (m_b_has_scartswitch)
	{
		std::string check = CFile::read("/proc/stb/avs/0/input_choices", __MODULE__, flags);
		return !!strstr(check.c_str(), "scart");
	}
	else
		return false;
}

/// @brief get the scart switch info
/// @return
bool eAVControl::hasScartSwitch() const
{
	return m_b_has_scartswitch;
}

/// @brief sets the color format
/// @param newFormat (cvbs, rgb, svideo, yuv)
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setColorFormat(const std::string &newFormat, int flags) const
{

	if (access("/proc/stb/avs/0/colorformat", W_OK))
		return;

	CFile::writeStr("/proc/stb/avs/0/colorformat", newFormat, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setColorFormat", newFormat.c_str());
}

/// @brief setWSS
/// @param val
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setWSS(int val, int flags) const
{
	if (access(proc_wss, W_OK))
		return;

	std::string newval = (val == 1) ? "auto" : "auto(4:3_off)";

	CFile::writeStr(proc_wss, newval, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setWSS", newval.c_str());
}

/// @brief setPolicy43
/// @param newPolicy
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setPolicy43(const std::string &newPolicy, int flags) const
{

	CFile::writeStr(proc_policy43, newPolicy, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setPolicy43", newPolicy.c_str());
}

/// @brief setPolicy169
/// @param newPolicy
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setPolicy169(const std::string &newPolicy, int flags) const
{

	CFile::writeStr(proc_policy169, newPolicy, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setPolicy169", newPolicy.c_str());
}

/// @brief setVideoSize
/// @param top 
/// @param left 
/// @param width 
/// @param height 
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
void eAVControl::setVideoSize(int top, int left, int width, int height, int flags) const
{

	CFile::writeIntHex("/proc/stb/vmpeg/0/dst_top", top, __MODULE__, flags);
	CFile::writeIntHex("/proc/stb/vmpeg/0/dst_left", left, __MODULE__, flags);
	CFile::writeIntHex("/proc/stb/vmpeg/0/dst_width", width, __MODULE__, flags);
	CFile::writeIntHex("/proc/stb/vmpeg/0/dst_height", height, __MODULE__, flags);
	CFile::writeInt("/proc/stb/vmpeg/0/dst_apply", 1, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: T:%d L:%d W:%d H:%d", __MODULE__, "setVideoSize", top, left, width, height);
}

void eAVControl::setOSDAlpha(int alpha, int flags) const
{
#ifdef DREAMNEXTGEN
	CFile::writeIntHex(proc_osd_alpha, alpha, __MODULE__, flags);
#else
	CFile::writeInt(proc_osd_alpha, alpha, __MODULE__, flags);
#endif
}

/// @brief getEDIDPath
/// @return 
std::string eAVControl::getEDIDPath() const
{
	struct stat buffer = {};

#ifdef DREAMNEXTGEN
	const std::string proc = "/sys/class/amhdmitx/amhdmitx0/rawedid";
#else
	const std::string proc = "/proc/stb/hdmi/raw_edid";
#endif

	if (stat(proc.c_str(), &buffer) == 0 && stat("/usr/bin/edid-decode", &buffer) == 0)
	{
		return proc;
	}
	return "";
}


eAutoInitP0<eAVControl> init_avcontrol(eAutoInitNumbers::rc, "AVControl Driver");
