#include <stdarg.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <ctype.h>
#include <sys/stat.h>
#include  <pthread.h> 

#include <lib/base/eerror.h>
#include <lib/driver/vfd.h>

#define VFD_DEVICE "/proc/vfd"

evfd* evfd::instance = NULL;

evfd* evfd::getInstance()
{
	if (instance == NULL)
		instance = new evfd;
	return instance;
}

evfd::evfd()
{
	file_vfd = 0;
}


int vfd_init( void )
{
	evfd vfd;
	vfd.vfd_led("1");
	char str[]="RED";
	return 0;
}

void evfd::init()
{
	vfd_init();
	return;
}

evfd::~evfd()
{
}

void evfd::vfd_led(char * led)
{
	FILE *f;
	if((f = fopen("/proc/stb/fp/led0_pattern","w")) == NULL) {
		eDebug("cannot open /proc/stb/fp/led0_pattern (%m)");
		return;
	}
	
	fprintf(f,"%s", led);
	fclose(f);
}

void evfd::vfd_write_string(char * str)
{
	FILE *f;
	if((f = fopen("/proc/vfd","w")) == NULL) {
		eDebug("cannotopen /proc/vfd (%m)");
	
		return;
	}
	
	fprintf(f,"%s", str);
	
	fclose(f);
}