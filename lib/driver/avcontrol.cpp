#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>
#include <algorithm>
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
const char *proc_videomode = "/sys/class/display/mode";		   // NOSONAR
const char *proc_videoaspect = "/sys/class/video/screen_mode"; // NOSONAR
#else
const char *proc_videomode = "/proc/stb/video/videomode";  // NOSONAR
const char *proc_videoaspect = "/proc/stb/vmpeg/0/aspect"; // NOSONAR
#endif
const char *proc_videomode_50 = "/proc/stb/video/videomode_50hz"; // NOSONAR
const char *proc_videomode_60 = "/proc/stb/video/videomode_60hz"; // NOSONAR
const char *proc_videomode_24 = "/proc/stb/video/videomode_24hz"; // NOSONAR

eAVControl *eAVControl::m_instance = 0;

eAVControl::eAVControl()
{
	struct stat buffer;
	m_b_has_proc_aspect = (stat(proc_videoaspect, &buffer) == 0);
	m_b_has_proc_hdmi_rx_monitor = (stat(proc_hdmi_rx_monitor, &buffer) == 0);
	m_b_has_proc_videomode_50 = (stat(proc_videomode_50, &buffer) == 0);
	m_b_has_proc_videomode_60 = (stat(proc_videomode_60, &buffer) == 0);
#ifdef DREAMNEXTGEN
	m_b_has_proc_videomode_24 = true;
#else
	m_b_has_proc_videomode_24 = (access(proc_videomode_24, W_OK) == 0);
#endif
	m_videomode_choices = readAvailableModes();
	m_video_output_active = false;

	eModelInformation &modelinformation = eModelInformation::getInstance();
	m_b_has_scartswitch = modelinformation.getValue("scart") == "True";
	if (m_b_has_scartswitch)
	{
		m_b_has_scartswitch = modelinformation.getValue("noscartswitch") != "True";
		if (m_b_has_scartswitch)
			m_b_has_scartswitch = checkScartSwitch();
	}

	eDebug("[%s] Init: ScartSwitch:%d / VideoMode 24:%d 50:%d 60:%d / HDMIRxMonitor:%d / VideoAspect:%d", __MODULE__, m_b_has_scartswitch, m_b_has_proc_videomode_24, m_b_has_proc_videomode_50, m_b_has_proc_videomode_60, m_b_has_proc_hdmi_rx_monitor, m_b_has_proc_aspect);
	eDebug("[%s] Init: VideoMode Choices:%s", __MODULE__, m_videomode_choices.c_str());
	m_instance = this;

}

eAVControl::~eAVControl()
{
	m_instance = 0;
}

/// @brief Get video aspect
/// @param defaultVal
/// @param flags
/// @return
int eAVControl::getAspect(int defaultVal, int flags) const
{
	if (m_b_has_proc_aspect)
	{
		int value = 0;
		CFile::parseIntHex(&value, proc_videoaspect, __MODULE__, flags);
		if (flags & FLAGS_DEBUG)
			eDebug("[%s] %s: %d", __MODULE__, "getAspect", value);
	}
	return defaultVal;
}

/// @brief Get progressive
/// @param flags
/// @return
bool eAVControl::getProgressive(int flags) const
{
	int value = 0;
	CFile::parseIntHex(&value, "/proc/stb/vmpeg/0/progressive", __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "getProgressive", value);
	return value == 1;
}

/// @brief Get screen resolution X
/// @param defaultVal = 0
/// @param flags bit ( 1 = DEBUG , 2 = SUPPRESS_NOT_EXISTS , 4 = SUPPRESS_READWRITE_ERROR)
/// @return resolution value
int eAVControl::getResolutionX(int defaultVal, int flags) const
{
	int value;
#ifdef DREAMNEXTGEN
	int ret = CFile::parseInt(&x, "/sys/class/video/frame_width", __MODULE__, flags);
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
	int ret = CFile::parseInt(&value, "/sys/class/video/frame_height", __MODULE__, flags);
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
/// @param flags
/// @return
int eAVControl::getFrameRate(int defaultVal, int flags) const
{

#ifdef DREAMNEXTGEN
	const char *fileName = "/proc/stb/vmpeg/0/frame_rate";
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
}

/// @brief Get VideoMode
/// @param defaultVal
/// @param flags
/// @return
std::string eAVControl::getVideoMode(const std::string &defaultVal, int flags) const
{
	std::string result = CFile::read(proc_videomode, __MODULE__, flags);
	if (!result.empty() && result[result.length() - 1] == '\n')
	{
		result.erase(result.length() - 1);
	}
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "getVideoMode", result.c_str());

	return result;
}

/// @brief Set VideoMode
/// @param newMode
/// @param flags
void eAVControl::setVideoMode(const std::string &newMode, int flags) const
{
	CFile::writeStr(proc_videomode, newMode, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setVideoMode", newMode.c_str());
}

/// @brief set HDMIInPip for 'dm7080', 'dm820', 'dm900', 'dm920'
/// @return false if one of the models
bool eAVControl::setHDMIInPiP(int flags) const
{

#ifdef HAVE_HDMIIN_DM

	if (!m_b_has_proc_hdmi_rx_monitor)
		return true;

	std::string check = CFile::read(proc_hdmi_rx_monitor, __MODULE__, flags);

	if (check.rfind("off", 0) == 0)
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "on", __MODULE__, flags);
		CFile::writeStr(proc_hdmi_rx_monitor, "on", __MODULE__, flags);
	}
	else
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off", __MODULE__, flags);
		CFile::writeStr(proc_hdmi_rx_monitor, "off", __MODULE__, flags);
	}

	return false;

#else
	return true;
#endif
}
/// @brief set HDMIInFull for 'dm7080', 'dm820', 'dm900', 'dm920'
/// @return false if one of the models
bool eAVControl::setHDMIInFull(int flags)
{

#ifdef HAVE_HDMIIN_DM

	if (!m_b_has_proc_hdmi_rx_monitor)
		return true;

	std::string check = CFile::read(proc_hdmi_rx_monitor, __MODULE__, flags);

	if (check.rfind("off", 0) == 0)
	{

		m_video_mode = CFile::read(proc_videomode, __MODULE__, flags);
		m_video_mode_50 = CFile::read(proc_videomode_50, __MODULE__, flags);
		m_video_mode_60 = CFile::read(proc_videomode_60, __MODULE__, flags);

#ifdef HAVE_HDMIIN_FHD
		CFile::writeStr(proc_videomode, "1080p", __MODULE__, flags);
#else
		CFile::writeStr(proc_videomode, "720p", __MODULE__, flags);
#endif

		CFile::writeStr(proc_hdmi_rx_monitor_audio, "on", __MODULE__, flags);
		CFile::writeStr(proc_hdmi_rx_monitor, "on", __MODULE__, flags);
	}
	else
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off", __MODULE__, flags);
		CFile::writeStr(proc_hdmi_rx_monitor, "off", __MODULE__, flags);
		CFile::writeStr(proc_videomode, m_video_mode, __MODULE__, flags);
		CFile::writeStr(proc_videomode_50, m_video_mode_50, __MODULE__, flags);
		CFile::writeStr(proc_videomode_60, m_video_mode_60, __MODULE__, flags);
	}

	return false;

#else
	return true;
#endif
}

/// @brief disable HDMIIn / used in StartEnigma.py
/// @param flags
void eAVControl::disableHDMIIn(int flags) const
{
	if (!m_b_has_proc_hdmi_rx_monitor)
		return;

	std::string check = CFile::read(proc_hdmi_rx_monitor, __MODULE__, flags);

	if (check.rfind("on", 0) == 0)
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off", __MODULE__, flags);
		CFile::writeStr(proc_hdmi_rx_monitor, "off", __MODULE__, flags);
	}
}

/// @brief read the preferred video modes
/// @param flags
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
/// @param flags
/// @return
std::string eAVControl::readAvailableModes(int flags) const
{

#ifdef DREAMNEXTGEN
	return std::string("480i60hz 576i50hz 480p60hz 576p50hz 720p60hz 1080i60hz 1080p60hz 720p50hz 1080i50hz 1080p30hz 1080p50hz 1080p25hz 1080p24hz 2160p30hz 2160p25hz 2160p24hz smpte24hz smpte25hz smpte30hz smpte50hz smpte60hz 2160p50hz 2160p60hz");
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
/// @param flags
void eAVControl::setAspectRatio(int ratio, bool setPolicy, int flags) const
{
	/*
	0-4:3 Letterbox
	1-4:3 PanScan
	2-16:9
	3-16:9 forced ("panscan")
	4-16:10 Letterbox
	5-16:10 PanScan
	6-16:9 forced ("letterbox")
	*/
	const char *aspect[] = {"4:3", "4:3", "any", "16:9", "16:10", "16:10", "16:9"};
	const char *policy[] = {"letterbox", "panscan", "bestfit", "panscan", "letterbox", "panscan", "letterbox"};

	if (ratio < 0 || ratio > 7)
	{
		eDebug("[%s] %s: invalid value %d", __MODULE__, "setAspectRatio", ratio);
		return;
	}

	std::string newAspect = aspect[ratio];
	std::string newPolicy = policy[ratio];

#ifdef DREAMNEXTGEN
	CFile::writeInt("/sys/class/video/screen_mode", newAspect, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setAspectRatio/aspect", newAspect);
#else
	CFile::writeInt("/proc/stb/video/aspect", ratio, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setAspectRatio/aspect", newAspect.c_str());

	if (!setPolicy)
		return;

	CFile::writeStr("/proc/stb/video/policy", newPolicy, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setAspectRatio/policy", newAspect.c_str());

#endif
}

/// @brief set video output
/// @param newMode (scart, aux, encoder, off)
/// @param flags
void eAVControl::setVideoOutput(std::string newMode, int flags)
{

	if (newMode == "off") // off = aux or scart based on scartswitch used for standby
	{
		newMode = m_b_has_scartswitch ? "scart" : "aux";
	}
	else if (newMode != "scart" && newMode != "aux" && newMode != "encoder")
	{
		newMode = "encoder"; // set to encoder if not valid
	}

	m_video_output_active = newMode == "encoder";

	CFile::writeStr("/proc/stb/avs/0/input", newMode, __MODULE__, flags);
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "enableVideoOut", newMode.c_str());
}

/// @brief get video output active state
/// @return true/false
bool eAVControl::isVideoOutputActive() const
{
	return m_video_output_active;
}

/// @brief read input choices and check for scart / it's for internal use only
/// @param flags
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
/// @param flags
void eAVControl::setColorFormat(const std::string &newFormat, int flags) const
{

	if (access("/proc/stb/avs/0/colorformat", W_OK))
		return;

	CFile::writeStr("/proc/stb/avs/0/colorformat", newFormat, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setColorFormat/policy", newFormat.c_str());
}

eAutoInitP0<eAVControl> init_avcontrol(eAutoInitNumbers::rc, "AVControl Driver");
