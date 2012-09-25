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

evfd* evfd::instance = NULL;

evfd* evfd::getInstance()
{
	if (instance == NULL)
		instance = new evfd;
	return instance;
}

evfd::evfd()
{
}

int vfd_init( void )
{
	evfd vfd;
	vfd.vfd_symbol_network(0);
	vfd.vfd_symbol_circle(0);
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

void evfd::vfd_symbol_network(int net)
{
	FILE *f;
	if((f = fopen("/proc/stb/lcd/symbol_network","w")) == NULL) {
		eDebug("cannot open /proc/stb/lcd/symbol_network (%m)");
		return;
	}	
	fprintf(f,"%i", net);
	fclose(f);
}

void evfd::vfd_symbol_circle(int cir)
{
	FILE *f;
	if((f = fopen("/proc/stb/lcd/symbol_circle","w")) == NULL) {
		eDebug("cannotopen /proc/stb/lcd/symbol_circle (%m)");
	
		return;
	}
	fprintf(f,"%i", cir);
	fclose(f);
}