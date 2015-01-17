#include <lib/driver/rfmod.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>

#define IOCTL_SET_CHANNEL						0
#define IOCTL_SET_TESTMODE					1
#define IOCTL_SET_SOUNDENABLE				2
#define IOCTL_SET_SOUNDSUBCARRIER		3
#define IOCTL_SET_FINETUNE					4
#define IOCTL_SET_STANDBY						5

eRFmod *eRFmod::instance = 0;

eRFmod::eRFmod()
{
	ASSERT(!instance);
	instance = this;

	fd = open("/dev/rfmod0", O_RDWR);
	if (fd < 0)
		eDebug("couldnt open /dev/rfmod0!!!!");
}

eRFmod::~eRFmod()
{
	if(fd >= 0)
		close(fd);
}

eRFmod *eRFmod::getInstance()
{
	return instance;
}

void eRFmod::setFunction(int val)		//0=Enable 1=Disable
{
	ioctl(fd, IOCTL_SET_STANDBY, &val);
}

void eRFmod::setTestmode(int val)		//0=Enable 1=Disable
{
	ioctl(fd, IOCTL_SET_TESTMODE, &val);
}

void eRFmod::setSoundFunction(int val)		//0=Enable 1=Disable
{
	ioctl(fd, IOCTL_SET_SOUNDENABLE, &val);
}

void eRFmod::setSoundCarrier(int val)
{
	ioctl(fd, IOCTL_SET_SOUNDSUBCARRIER, &val);
}

void eRFmod::setChannel(int val)
{
	ioctl(fd, IOCTL_SET_CHANNEL, &val);
}

void eRFmod::setFinetune(int val)
{
	ioctl(fd, IOCTL_SET_FINETUNE, &val);
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eRFmod> init_rfmod(eAutoInitNumbers::rc, "UHF Modulator");
