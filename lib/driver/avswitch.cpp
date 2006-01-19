#include <lib/driver/avswitch.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/econfig.h>
#include <lib/base/eerror.h>

eAVSwitch *eAVSwitch::instance = 0;

eAVSwitch::eAVSwitch()
{
	ASSERT(!instance);
	instance = this;
}

eAVSwitch::~eAVSwitch()
{
}

eAVSwitch *eAVSwitch::getInstance()
{
	return instance;
}

void eAVSwitch::setInput(int val)
{
	/*
	0-encoder
	1-scart
	2-aux
	*/

	char *input[] = {"encoder", "scart", "aux"};

	int fd;
	
	if((fd = open("/proc/stb/avs/0/input", O_WRONLY)) < 0) {
		printf("cannot open /proc/stb/avs/0/input\n");
		return;
	}

	write(fd, input[val], strlen(input[val]));
	close(fd);
}

void eAVSwitch::setFastBlank(int val)
{
	int fd;
	char *fb[] = {"low", "high", "vcr"};

	
	if((fd = open("/proc/stb/avs/0/fb", O_WRONLY)) < 0) {
		printf("cannot open /proc/stb/avs/0/fb\n");
		return;
	}

	write(fd, fb[val], strlen(fb[0]));
	close(fd);
}

void eAVSwitch::setColorFormat(int format)
{
	/*
	0-CVBS
	1-RGB
	2-S-Video
	*/
	char *cvbs="cvbs";
	char *rgb="rgb";
	char *svideo="svideo";
	int fd;
	
	if((fd = open("/proc/stb/avs/0/colorformat", O_WRONLY)) < 0) {
		printf("cannot open /proc/stb/avs/0/colorformat\n");
		return;
	}
	switch(format) {
		case 0:
			write(fd, cvbs, strlen(cvbs));
			break;
		case 1:
			write(fd, rgb, strlen(rgb));
			break;
		case 2:
			write(fd, svideo, strlen(svideo));
			break;
	}	
	close(fd);
}

void eAVSwitch::setAspectRatio(int ratio)
{
	/*
	0-4:3 Letterbox
	1-4:3 PanScan
	2-16:9
	3-16:9 forced
	*/
	
	char *aspect[] = {"4:3", "4:3", "any", "16:9"};
	char *policy[] = {"letterbox", "panscan", "bestfit", "panscan"};

	int fd;
	if((fd = open("/proc/stb/video/aspect", O_WRONLY)) < 0) {
		printf("cannot open /proc/stb/video/aspect\n");
		return;
	}
	write(fd, aspect[ratio], strlen(aspect[ratio]));
	close(fd);

	if((fd = open("/proc/stb/video/policy", O_WRONLY)) < 0) {
		printf("cannot open /proc/stb/video/policy\n");
		return;
	}
	write(fd, policy[ratio], strlen(policy[ratio]));
	close(fd);

}

void eAVSwitch::setVideomode(int mode)
{
	char *pal="pal";
	char *ntsc="ntsc";
	int fd;
	
	return;
	//FIXME: bug in driver (cannot set PAL)
	if((fd = open("/proc/stb/video/videomode", O_WRONLY)) < 0) {
		printf("cannot open /proc/stb/video/videomode\n");
		return;
	}
	switch(mode) {
		case 0:
			write(fd, pal, strlen(pal));
			break;
		case 1:
			write(fd, ntsc, strlen(ntsc));
			break;
	}	
	close(fd);
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eAVSwitch> init_avswitch(eAutoInitNumbers::rc, "AVSwitch Driver");
