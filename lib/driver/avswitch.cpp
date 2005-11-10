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
	
	char *any="any";
	char *norm="4:3";
	char *wide="16:9";
	int fd;

	if((fd = open("/proc/stb/video/aspect", O_WRONLY)) < 0) {
		printf("cannot open /proc/stb/video/aspect\n");
		return;
	}
	switch(ratio) {
		case 0:
			write(fd, any, strlen(any));
			break;
		case 1:
			write(fd, norm, strlen(norm));
			break;
		case 2:
		case 3:
			write(fd, wide, strlen(wide));
			break;
	}	
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
