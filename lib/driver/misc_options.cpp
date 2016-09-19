#include <cstring>
#include <lib/driver/misc_options.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>

Misc_Options *Misc_Options::instance = 0;

Misc_Options::Misc_Options()
	:m_12V_output_state(-1)
{
	ASSERT(!instance);
	instance = this;
}

int Misc_Options::set_12V_output(int state)
{
	if (state == m_12V_output_state)
		return 0;
	int fd = open("/proc/stb/misc/12V_output", O_WRONLY);
	if (fd < 0)
	{
		eDebug("[Misc_Options] cannot open /proc/stb/misc/12V_output: %m");
		return -1;
	}
	const char *str=0;
	if (state == 0)
		str = "off";
	else if (state == 1)
		str = "on";
	if (str)
		write(fd, str, strlen(str));
	m_12V_output_state = state;
	close(fd);
	return 0;
}

bool Misc_Options::detected_12V_output()
{
	int fd = open("/proc/stb/misc/12V_output", O_WRONLY);
	if (fd < 0)
	{
		eDebug("[Misc_Options] 12Vdetect cannot open /proc/stb/misc/12V_output: %m");
		return false;
	}
	close(fd);
	eDebug("[Misc_Options] 12V output detected");
	return true;
}

Misc_Options *Misc_Options::getInstance()
{
	return instance;
}

//FIXME: correct "run/startlevel"
eAutoInitP0<Misc_Options> init_misc_options(eAutoInitNumbers::rc, "misc options");
