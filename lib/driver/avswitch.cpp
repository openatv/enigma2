#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <string.h>

#include <lib/base/cfile.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/ebase.h>
#include <lib/driver/avswitch.h>

eAVSwitch *eAVSwitch::instance = 0;

eAVSwitch::eAVSwitch()
{
	ASSERT(!instance);
	instance = this;
	m_video_mode = 0;
	m_active = false;
}


eAVSwitch::~eAVSwitch()
{
}

eAVSwitch *eAVSwitch::getInstance()
{
	return instance;
}

bool eAVSwitch::haveScartSwitch()
{
	char tmp[255];
	int fd = open("/proc/stb/avs/0/input_choices", O_RDONLY);
	if(fd < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/avs/0/input_choices: %m");
		return false;
	}
	if (read(fd, tmp, 255) < 1)
	{
		eDebug("[eAVSwitch] failed to read data from /proc/stb/avs/0/input_choices: %m");
	}
	close(fd);
	return !!strstr(tmp, "scart");
}

void eAVSwitch::setInput(int val)
{
	/*
	0-encoder
	1-scart
	2-aux
	*/

	const char *input[] = {"encoder", "scart", "aux"};

	int fd;

	m_active = val == 0;

	if((fd = open("/proc/stb/avs/0/input", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/avs/0/input: %m");
		return;
	}

	if (write(fd, input[val], strlen(input[val])) < 0)
	{
		eDebug("[eAVSwitch] setInput failed %m");
	}
	close(fd);
}

bool eAVSwitch::isActive()
{
	return m_active;
}

void eAVSwitch::setColorFormat(int format)
{
	/*
	0-CVBS
	1-RGB
	2-S-Video
	*/
	const char *fmt = "";
	int fd;

	if (access("/proc/stb/avs/0/colorformat", W_OK))
		return;  // no colorformat file...

	switch (format) {
		case 0: fmt = "cvbs";   break;
		case 1: fmt = "rgb";    break;
		case 2: fmt = "svideo"; break;
		case 3: fmt = "yuv";    break;
	}
	if (*fmt == '\0')
		return; // invalid format

	if ((fd = open("/proc/stb/avs/0/colorformat", O_WRONLY)) < 0) {  //NOSONAR
		eDebug("[eAVSwitch] cannot open /proc/stb/avs/0/colorformat: %m");
		return;
	}

	if (write(fd, fmt, strlen(fmt)) < 1)
	{
		eDebug("[eAVSwitch] setColorFormat failed %m");
	}
	close(fd);
}

void eAVSwitch::setAspectRatio(int ratio)
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
	const char *aspect[] = {"4:3", "4:3", "any", "16:9", "16:10", "16:10", "16:9", "16:9"};
	const char *policy[] = {"letterbox", "panscan", "bestfit", "panscan", "letterbox", "panscan", "letterbox"};

	int fd;
#ifdef DREAMNEXTGEN
	if((fd = open("/sys/class/video/screen_mode", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /sys/class/video/screen_mode: %m");
		return;
	}
#else
	if((fd = open("/proc/stb/video/aspect", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/video/aspect: %m");
		return;
	}
#endif

//	eDebug("set aspect to %s", aspect[ratio]);
	if (write(fd, aspect[ratio], strlen(aspect[ratio])) < 1)
	{
		eDebug("[eAVSwitch] setAspectRatio failed %m");
	}
	close(fd);

	if((fd = open("/proc/stb/video/policy", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/video/policy: %m");
		return;
	}
//	eDebug("set ratio to %s", policy[ratio]);
	if (write(fd, policy[ratio], strlen(policy[ratio])) < 1)
	{
		eDebug("[eAVSwitch] setAspectRatio policy failed %m");
	}
	close(fd);

//	if((fd = open("/proc/stb/video/policy2", O_WRONLY)) < 0) {
//		eDebug("cannot open /proc/stb/video/policy2");
//		return;
//	}
//	write(fd, policy[ratio], strlen(policy[ratio]));
//	close(fd);
}

void eAVSwitch::setVideomode(int mode)
{
	const char *pal="pal";
	const char *ntsc="ntsc";

	if (mode == m_video_mode)
		return;

	if (mode == 2)
	{
		int fd1 = open("/proc/stb/video/videomode_50hz", O_WRONLY);
		if(fd1 < 0) {
			eDebug("[eAVSwitch] cannot open /proc/stb/video/videomode_50hz: %m");
			return;
		}
		int fd2 = open("/proc/stb/video/videomode_60hz", O_WRONLY);
		if(fd2 < 0) {
			eDebug("[eAVSwitch] cannot open /proc/stb/video/videomode_60hz: %m");
			close(fd1);
			return;
		}
		if (write(fd1, pal, strlen(pal)) < 1)
		{
			eDebug("[eAVSwitch] setVideomode pal failed %m");
		}
		if (write(fd2, ntsc, strlen(ntsc)) < 1)
		{
			eDebug("[eAVSwitch] setVideomode ntsc failed %m");
		}
		close(fd1);
		close(fd2);
	}
	else
	{
#ifdef DREAMNEXTGEN
		int fd = open("/sys/class/display/mode", O_WRONLY);
		if(fd < 0) {
			eDebug("[eAVSwitch] cannot open /sys/class/display/mode: %m");
			return;
		}
#else
		int fd = open("/proc/stb/video/videomode", O_WRONLY);
		if(fd < 0) {
			eDebug("[eAVSwitch] cannot open /proc/stb/video/videomode: %m");
			return;
		}
#endif
		switch(mode) {
			case 0:
				if (write(fd, pal, strlen(pal)) < 1)
				{
					eDebug("[eAVSwitch] setVideomode pal failed %m");
				}
				break;
			case 1:
				if (write(fd, ntsc, strlen(ntsc)) < 1)
				{
					eDebug("[eAVSwitch] setVideomode ntsc failed %m");
				}
				break;
			default:
				eDebug("[eAVSwitch] unknown videomode %d", mode);
		}
		close(fd);
	}

	m_video_mode = mode;
}

void eAVSwitch::setWSS(int val) // 0 = auto, 1 = auto(4:3_off)
{
	int fd;
	if((fd = open("/proc/stb/denc/0/wss", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/denc/0/wss: %m");
		return;
	}
	const char *wss[] = {
		"off", "auto", "auto(4:3_off)", "4:3_full_format", "16:9_full_format",
		"14:9_letterbox_center", "14:9_letterbox_top", "16:9_letterbox_center",
		"16:9_letterbox_top", ">16:9_letterbox_center", "14:9_full_format"
	};
	if (write(fd, wss[val], strlen(wss[val])) < 1)
	{
		eDebug("[eAVSwitch] setWSS failed %m");
	}
//	eDebug("set wss to %s", wss[val]);
	close(fd);
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eAVSwitch> init_avswitch(eAutoInitNumbers::rc, "AVSwitch Driver");
