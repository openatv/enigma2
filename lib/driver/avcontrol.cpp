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
#include <lib/driver/avcontrol.h>

const char *__MODULE__ = "eAVControl"; // NOSONAR

const char *proc_hdmi_rx_monitor = "/proc/stb/hdmi-rx/0/hdmi_rx_monitor"; // NOSONAR
const char *proc_hdmi_rx_monitor_audio = "/proc/stb/audio/hdmi_rx_monitor"; // NOSONAR
#ifdef DREAMNEXTGEN
const char *proc_videomode = "/sys/class/display/mode"; // NOSONAR
const char *proc_videoaspect = "/sys/class/video/screen_mode"; // NOSONAR
#else
const char *proc_videomode = "/proc/stb/video/videomode"; // NOSONAR
const char *proc_videoaspect = "/proc/stb/vmpeg/0/aspect"; // NOSONAR
#endif
const char *proc_videomode_50 = "/proc/stb/video/videomode_50hz"; // NOSONAR
const char *proc_videomode_60 = "/proc/stb/video/videomode_60hz"; // NOSONAR

eAVControl::eAVControl()
{
	struct stat buffer;
	m_b_has_proc_aspect = (stat(proc_videoaspect, &buffer) == 0);
	m_b_has_proc_hdmi_rx_monitor = (stat(proc_hdmi_rx_monitor, &buffer) == 0);
	m_b_has_proc_videomode_50 = (stat(proc_videomode_50, &buffer) == 0);
	m_b_has_proc_videomode_60 = (stat(proc_videomode_60, &buffer) == 0);
	m_videomode_choices = readAvailableModes();
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

	std::string check = CFile::read(proc_hdmi_rx_monitor);

	if (check.rfind("off", 0) == 0)
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "on");
		CFile::writeStr(proc_hdmi_rx_monitor, "on");
	}
	else
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off");
		CFile::writeStr(proc_hdmi_rx_monitor, "off");
	}

	return false;

#else
	return true;
#endif
}
/// @brief set HDMIInFull for 'dm7080', 'dm820', 'dm900', 'dm920'
/// @return false if one of the models
bool eAVControl::setHDMIInFull(int flags) const
{

#ifdef HAVE_HDMIIN_DM

	if (!m_b_has_proc_hdmi_rx_monitor)
		return true;

	std::string check = CFile::read(proc_hdmi_rx_monitor);

	if (check.rfind("off", 0) == 0)
	{

		m_video_mode = CFile::read(proc_videomode);
		m_video_mode_50 = CFile::read(proc_videomode_50);
		m_video_mode_60 = CFile::read(proc_videomode_60);

#ifdef HAVE_HDMIIN_FHD
		CFile::writeStr(proc_videomode, "1080p");
#else
		CFile::writeStr(proc_videomode, "720p");
#endif

		CFile::writeStr(proc_hdmi_rx_monitor_audio, "on");
		CFile::writeStr(proc_hdmi_rx_monitor, "on");
	}
	else
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off");
		CFile::writeStr(proc_hdmi_rx_monitor, "off");
		CFile::writeStr(proc_videomode, m_video_mode);
		CFile::writeStr(proc_videomode_50, m_video_mode_50);
		CFile::writeStr(proc_videomode_60, m_video_mode_60);
	}

	return false;

#else
	return true;
#endif
}

/// @brief disable HDMIIn / used in StartEnigma.py
void eAVControl::disableHDMIIn(int flags) const
{
	if (!m_b_has_proc_hdmi_rx_monitor)
		return;

	std::string check = CFile::read(proc_hdmi_rx_monitor);

	if (check.rfind("on", 0) == 0)
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off");
		CFile::writeStr(proc_hdmi_rx_monitor, "off");
	}
}

/// @brief read the preferred video modes
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
	}

	if (!result.empty() && result[result.length() - 1] == '\n')
	{
		result.erase(result.length() - 1);
	}

#ifdef DREAMNEXTGEN
	result = std::regex_replace(result, std::regex("\\*"), "");
	result = std::regex_replace(result, std::regex("\n+"), " ");
#else

	if(result.empty())
	{
		if (access(fileName2, R_OK) == 0)
		{
			result = CFile::read(fileName2, __MODULE__, flags);
			if (!result.empty() && result[result.length() - 1] == '\n')
			{
				result.erase(result.length() - 1);
			}
		}
	}

#endif

	return result;
}

/// @brief read the available video modes
/// It's for internal use only because it will be static.
std::string eAVControl::readAvailableModes(int flags) const
{

#ifdef DREAMNEXTGEN
	return std::string("480i60hz 576i50hz 480p60hz 576p50hz 720p60hz 1080i60hz 1080p60hz 720p50hz 1080i50hz 1080p30hz 1080p50hz 1080p25hz 1080p24hz 2160p30hz 2160p25hz 2160p24hz smpte24hz smpte25hz smpte30hz smpte50hz smpte60hz 2160p50hz 2160p60hz");
#else
	const char *fileName ="/proc/stb/video/videomode_choices";
	std::string result = "";
	if (access(fileName, R_OK) == 0)
	{
		result = CFile::read(fileName, __MODULE__, flags);
	}

	if (!result.empty() && result[result.length() - 1] == '\n')
	{
		result.erase(result.length() - 1);
	}
	return result;
#endif

}

/// @brief get the available video modes
std::string eAVControl::getAvailableModes(int flags) const
{
	return m_videomode_choices;
}