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
	
	avsfd = open("/dev/dbox/avs0", O_RDWR);
	
	//enable colors on thedoc's tv 
	ioctl(avsfd, 0x1000 | 35, 2);
	ioctl(avsfd, 0x1000 | 9, 1);
}

eAVSwitch::~eAVSwitch()
{
	if(avsfd > 0)
		close(avsfd);
}

eAVSwitch *eAVSwitch::getInstance()
{
	return instance;
}

void eAVSwitch::setColorFormat(int format)
{
	printf("eAVSwitch::setColorFormat(%d)\n",format);
	/*there are no ioctl for controling this in avs - scart api needed 
		no, not the gillem one */
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eAVSwitch> init_avswitch(eAutoInitNumbers::rc, "AVSwitch Driver");
