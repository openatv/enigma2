#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>

#include <lib/base/cfile.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/driver/avcontrol.h>


const char *proc_hdmi_rx_monitor = "/proc/stb/hdmi-rx/0/hdmi_rx_monitor";
const char *proc_hdmi_rx_monitor_audio = "/proc/stb/audio/hdmi_rx_monitor";
#ifdef DREAMNEXTGEN
const char *proc_videomode = "/sys/class/display/mode";
#else
const char *proc_videomode = "/proc/stb/video/videomode";
#endif
const char *proc_videomode_50 = "/proc/stb/video/videomode_50hz";
const char *proc_videomode_60 = "/proc/stb/video/videomode_60hz";

bool eAVControl::getProgressive(bool debug)
{
	const char *proc = "/proc/stb/vmpeg/0/progressive";

	int progressive = 0;
	CFile::parseIntHex(&progressive, proc);
	if (debug && progressive < 0)
		eDebug("[eAVControl] error read %s: %m", proc);
	return progressive == 1;
}

int eAVControl::getResolutionX(int defaultVal, bool debug)
{

	int x;
#ifdef DREAMNEXTGEN
	const char *proc = "/sys/class/video/frame_width";
	CFile::parseInt(&x, proc);
#else
	const char *proc = "/proc/stb/vmpeg/0/xres";
	CFile::parseIntHex(&x, proc);
#endif

	if (x < 0)
	{
		if (debug)
			eDebug("[eAVControl] error read %s: %m", proc);
		x = defaultVal;
	}
	return x;
}

int eAVControl::getResolutionY(int defaultVal, bool debug)
{

	int y;
#ifdef DREAMNEXTGEN
	const char *proc = "/sys/class/video/frame_height";
	CFile::parseInt(&y, proc);
#else
	const char *proc = "/proc/stb/vmpeg/0/yres";
	CFile::parseIntHex(&y, proc);
#endif

	if (y < 0)
	{
		if (debug)
			eDebug("[eAVControl] error read %s: %m", proc);
		y = defaultVal;
	}
	return y;
}

int eAVControl::getFrameRate(int defaultVal, bool debug)
{

#ifdef DREAMNEXTGEN
	const char *proc = "/proc/stb/vmpeg/0/frame_rate";
#else
	const char *proc = "/proc/stb/vmpeg/0/frame_rate";
#endif

	int framerate = 0;
	CFile::parseInt(&framerate, proc);
	if (framerate < 0)
	{
		if (debug)
			eDebug("[eAVControl] error read %s: %m", proc);
		framerate = defaultVal;
	}
	return framerate;
}

std::string eAVControl::getVideoMode(std::string defaultVal, bool debug)
{

	FILE *fd;
	std::string result = defaultVal;
	char buffer[50];
	if ((fd = fopen(proc_videomode, "r")) != NULL)
	{
		if (fgets(buffer, sizeof(buffer), fd))
		{
			int len = strlen(buffer);
			if (len)
			{
				if (buffer[len - 1] == '\n')
					buffer[len - 1] = '\0';
				result = std::string(buffer);
			}
		}
		else if(debug)
		{
			eDebug("[eAVControl] error read %s: %m", proc_videomode);
		}
		fclose(fd);
	}
	else if(debug)
	{
		eDebug("[eAVControl] error open %s: %m", proc_videomode);
	}

	return result;
}


void eAVControl::setVideoMode(std::string newMode, bool debug)
{
	if (debug)
		eDebug("[eAVControl] setVideoMode:%s", newMode.c_str());

	CFile::writeStr(proc_videomode, newMode);

}
/// @brief set HDMIInPip for 'dm7080', 'dm820', 'dm900', 'dm920'
/// @return false if one of the models
bool eAVControl::setHDMIInPiP()
{
	
#ifdef HAVE_HDMIIN_DM

	std::string check = CFile::read(hdmi_rx_monitor);

    if (check.rfind("off", 0) == 0) {
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "on");
		CFile::writeStr(proc_hdmi_rx_monitor, "on");
    } else {
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
bool eAVControl::setHDMIInFull()
{
	
#ifdef HAVE_HDMIIN_DM

	std::string check = CFile::read(proc_hdmi_rx_monitor);

    if (check.rfind("off", 0) == 0) {

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

    } else {
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
void eAVControl::disableHDMIIn()
{

	std::string check = CFile::read(proc_hdmi_rx_monitor);

    if (check.rfind("on", 0) == 0) {
		CFile::writeStr(proc_hdmi_rx_monitor_audio, "off");
		CFile::writeStr(proc_hdmi_rx_monitor, "off");
    }

}
