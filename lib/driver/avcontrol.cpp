#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>
#include <algorithm>

#include <lib/base/cfile.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/driver/avcontrol.h>

const char *__MODULE__ = "eAVControl";

const char *proc_hdmi_rx_monitor = "/proc/stb/hdmi-rx/0/hdmi_rx_monitor";
const char *proc_hdmi_rx_monitor_audio = "/proc/stb/audio/hdmi_rx_monitor";
#ifdef DREAMNEXTGEN
const char *proc_videomode = "/sys/class/display/mode";
#else
const char *proc_videomode = "/proc/stb/video/videomode";
#endif
const char *proc_videomode_50 = "/proc/stb/video/videomode_50hz";
const char *proc_videomode_60 = "/proc/stb/video/videomode_60hz";

bool eAVControl::getProgressive(int flags)
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
int eAVControl::getResolutionX(int defaultVal, int flags)
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
int eAVControl::getResolutionY(int defaultVal, int flags)
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
int eAVControl::getFrameRate(int defaultVal, int flags)
{

#ifdef DREAMNEXTGEN
	const char *fileName = "/proc/stb/vmpeg/0/frame_rate";
#else
	const char *fileName = "/proc/stb/vmpeg/0/frame_rate";
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
std::string eAVControl::getVideoMode(std::string defaultVal, int flags)
{

	FILE *fd;
	std::string result = CFile::read(proc_videomode, __MODULE__, flags);
	if (!result.empty() && result[result.length() - 1] == '\n')
	{
		result.erase(result.length() - 1);
	}
	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %d", __MODULE__, "getVideoMode", result.c_str());

	return result;
}


/// @brief Set VideoMode
/// @param newMode 
/// @param flags 
void eAVControl::setVideoMode(std::string newMode, int flags)
{
	CFile::writeStr(proc_videomode, newMode, __MODULE__, flags);

	if (flags & FLAGS_DEBUG)
		eDebug("[%s] %s: %s", __MODULE__, "setVideoMode", newMode.c_str());
}

/// @brief set HDMIInPip for 'dm7080', 'dm820', 'dm900', 'dm920'
/// @return false if one of the models
bool eAVControl::setHDMIInPiP(int flags)
{

#ifdef HAVE_HDMIIN_DM

	std::string check = CFile::read(hdmi_rx_monitor);

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
bool eAVControl::setHDMIInFull(int flags)
{

#ifdef HAVE_HDMIIN_DM

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
void eAVControl::disableHDMIIn(int flags)
{

	std::string check = CFile::read(proc_hdmi_rx_monitor);

	if (check.rfind("on", 0) == 0)
	{
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off");
		CFile::writeStr(proc_hdmi_rx_monitor, "off");
	}
}
