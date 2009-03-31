#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>

#define MAX_SLOTS 4

eDVBCI_UI *eDVBCI_UI::instance;

eDVBCI_UI::eDVBCI_UI()
	:eMMI_UI(MAX_SLOTS)
{
	ASSERT(!instance);
	instance = this;
}

eDVBCI_UI *eDVBCI_UI::getInstance()
{
	return instance;
}

void eDVBCI_UI::setInit(int slot)
{
	eDVBCIInterfaces::getInstance()->initialize(slot);
}

void eDVBCI_UI::setReset(int slot)
{
	eDVBCIInterfaces::getInstance()->reset(slot);
}

int eDVBCI_UI::startMMI(int slot)
{
	eDVBCIInterfaces::getInstance()->startMMI(slot);
	return 0;
}

int eDVBCI_UI::stopMMI(int slot)
{
	eDVBCIInterfaces::getInstance()->stopMMI(slot);
	return 0;
}

int eDVBCI_UI::answerMenu(int slot, int answer)
{
	eDVBCIInterfaces::getInstance()->answerText(slot, answer);
	return 0;
}

int eDVBCI_UI::answerEnq(int slot, char *value)
{
	eDVBCIInterfaces::getInstance()->answerEnq(slot, value);
	return 0;
}

int eDVBCI_UI::cancelEnq(int slot)
{
	eDVBCIInterfaces::getInstance()->cancelEnq(slot);
	return 0;
}

int eDVBCI_UI::getMMIState(int slot)
{
	return eDVBCIInterfaces::getInstance()->getMMIState(slot);
}

int eDVBCI_UI::setClockRate(int slot, int rate)
{
	return eDVBCIInterfaces::getInstance()->setCIClockRate(slot, rate);
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eDVBCI_UI> init_dvbciui(eAutoInitNumbers::rc, "DVB-CI UI");
