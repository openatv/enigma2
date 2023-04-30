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

eAVControl *eAVControl::instance = 0;

eAVControl::eAVControl()
{
	ASSERT(!instance);
	instance = this;
}

eAVControl *eAVControl::getInstance()
{
	return instance;
}

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
	const char *yres = "/proc/stb/vmpeg/0/yres";
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

#ifdef DREAMNEXTGEN
	const char *proc = "/sys/class/display/mode";
#else
	const char *proc = "/proc/stb/video/videomode";
#endif

	FILE *fd;
	str::string result = defaultVal;
	char buffer[50];
	if ((fd = fopen(proc, "r")) != NULL)
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
		else
		{
			if (debug)
				eDebug("[eAVControl] error read %s: %m", proc);
		}
		fclose(fd);
	}
	else
	{
		if (debug)
			eDebug("[eAVControl] error open %s: %m", proc);
	}

	return result;
}
