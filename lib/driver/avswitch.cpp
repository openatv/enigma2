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
	m_fp_fd = open("/dev/dbox/fp0", O_RDONLY|O_NONBLOCK);
	if (m_fp_fd == -1)
	{
		eDebug("[eAVSwitch] failed to open /dev/dbox/fp0 to monitor vcr scart slow blanking changed: %m");
		m_fp_notifier=0;
	}
	else
	{
		m_fp_notifier = eSocketNotifier::create(eApp, m_fp_fd, eSocketNotifier::Read|POLLERR);
		CONNECT(m_fp_notifier->activated, eAVSwitch::fp_event);
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

int eAVSwitch::getVCRSlowBlanking()
{
	int val=0;
	if (m_fp_fd >= 0)
	{
		CFile f("/proc/stb/fp/vcr_fns", "r");
		if (f)
		{
			if (fscanf(f, "%d", &val) != 1)
				eDebug("[eAVSwitch] read /proc/stb/fp/vcr_fns failed: %m");
		}
		else if (ioctl(m_fp_fd, FP_IOCTL_GET_VCR, &val) < 0)
			eDebug("[eAVSwitch] FP_GET_VCR failed: %m");
	}
	return val;
}

void eAVSwitch::fp_event(int what)
{
	if (what & POLLERR) // driver not ready for fp polling
	{
		eDebug("[eAVSwitch] fp driver not read for polling.. so disable polling");
		m_fp_notifier->stop();
	}
	else
	{
		CFile f("/proc/stb/fp/events", "r");
		if (f)
		{
			int events;
			if (fscanf(f, "%d", &events) != 1)
				eDebug("[eAVSwitch] read /proc/stb/fp/events failed: %m");
			else if (events & FP_EVENT_VCR_SB_CHANGED)
				/* emit */ vcr_sb_notifier(getVCRSlowBlanking());
		}
		else
		{
			int val = FP_EVENT_VCR_SB_CHANGED;  // ask only for this event
			if (ioctl(m_fp_fd, FP_IOCTL_GET_EVENT, &val) < 0)
				eDebug("[eAVSwitch] FP_IOCTL_GET_EVENT failed: %m");
			else if (val & FP_EVENT_VCR_SB_CHANGED)
				/* emit */ vcr_sb_notifier(getVCRSlowBlanking());
		}
	}
}

eAVSwitch::~eAVSwitch()
{
	if ( m_fp_fd >= 0 )
		close(m_fp_fd);
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
	read(fd, tmp, 255);
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

	write(fd, input[val], strlen(input[val]));
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

	if ((fd = open("/proc/stb/avs/0/colorformat", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/avs/0/colorformat: %m");
		return;
	}
	write(fd, fmt, strlen(fmt));
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
	if((fd = open("/proc/stb/video/aspect", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/video/aspect: %m");
		return;
	}
//	eDebug("set aspect to %s", aspect[ratio]);
	write(fd, aspect[ratio], strlen(aspect[ratio]));
	close(fd);

	if((fd = open("/proc/stb/video/policy", O_WRONLY)) < 0) {
		eDebug("[eAVSwitch] cannot open /proc/stb/video/policy: %m");
		return;
	}
//	eDebug("set ratio to %s", policy[ratio]);
	write(fd, policy[ratio], strlen(policy[ratio]));
	close(fd);

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
		write(fd1, pal, strlen(pal));
		write(fd2, ntsc, strlen(ntsc));
		close(fd1);
		close(fd2);
	}
	else
	{
		int fd = open("/proc/stb/video/videomode", O_WRONLY);
		if(fd < 0) {
			eDebug("[eAVSwitch] cannot open /proc/stb/video/videomode: %m");
			return;
		}
		switch(mode) {
			case 0:
				write(fd, pal, strlen(pal));
				break;
			case 1:
				write(fd, ntsc, strlen(ntsc));
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
	write(fd, wss[val], strlen(wss[val]));
//	eDebug("set wss to %s", wss[val]);
	close(fd);
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eAVSwitch> init_avswitch(eAutoInitNumbers::rc, "AVSwitch Driver");
