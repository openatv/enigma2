#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <string>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/econfig.h>
#include <lib/base/eerror.h>

eDVBCI_UI *eDVBCI_UI::instance = 0;

eDVBCI_UI::eDVBCI_UI()
{
	int i;
	
	for(i=0;i<MAX_SLOTS;i++)
		state[i] = 0;		//no module

	ASSERT(!instance);
	instance = this;
}

eDVBCI_UI::~eDVBCI_UI()
{
}

eDVBCI_UI *eDVBCI_UI::getInstance()
{
	return instance;
}

int eDVBCI_UI::getState(int slot)
{
	return state[slot];	//exploit me ;)
}

void eDVBCI_UI::setState(int slot, int newState)
{
	state[slot] = newState;
}

std::string eDVBCI_UI::getAppName(int slot)
{
	return appName;
}

void eDVBCI_UI::setAppName(int slot, const char *name)
{
	printf("set name to -%c-\n", name);
	appName = name;
}

void eDVBCI_UI::setReset(int slot)
{
	eDVBCIInterfaces::getInstance()->reset(slot);
}

int eDVBCI_UI::startMMI(int slot)
{
	eDVBCIInterfaces::getInstance()->startMMI(slot);
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eDVBCI_UI> init_dvbciui(eAutoInitNumbers::rc, "DVB-CI UI");
