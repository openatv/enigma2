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
	mmiScreenReady = 0;
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
	//printf("set name to -%c-\n", name);
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

int eDVBCI_UI::stopMMI(int slot)
{
	eDVBCIInterfaces::getInstance()->stopMMI(slot);
}

int eDVBCI_UI::initialize(int slot)
{
	eDVBCIInterfaces::getInstance()->initialize(slot);
}

int eDVBCI_UI::answerMenu(int slot, int answer)
{
	eDVBCIInterfaces::getInstance()->answerText(slot, answer);
}

int eDVBCI_UI::answerEnq(int slot, int answer, char *value)
{
	eDVBCIInterfaces::getInstance()->answerEnq(slot, answer, value);
}

int eDVBCI_UI::availableMMI(int slot)
{
	return mmiScreenReady;
}

int eDVBCI_UI::mmiScreenBegin(int slot, int listmenu)
{
	printf("eDVBCI_UI::mmiScreenBegin\n");

	mmiScreenReady = 0;
	
	mmiScreen = PyList_New(1);

  PyObject *tuple = PyTuple_New(1);
	if(listmenu)
	 	PyTuple_SetItem(tuple, 0, PyString_FromString("LIST"));
	else	
	 	PyTuple_SetItem(tuple, 0, PyString_FromString("MENU"));
  PyList_SetItem(mmiScreen, 0, tuple);
	
	mmiTuplePos = 1;
	
	return 0;
}

int eDVBCI_UI::mmiScreenAddText(int slot, int type, char *value)
{
	printf("eDVBCI_UI::mmiScreenAddText(%s)\n",value);

  PyObject *tuple = PyTuple_New(3);
	
	if(type == 0)							//title
	 	PyTuple_SetItem(tuple, 0, PyString_FromString("TITLE"));
	else if(type == 1)				//subtitle
	 	PyTuple_SetItem(tuple, 0, PyString_FromString("SUBTITLE"));
	else if(type == 2)				//bottom
	 	PyTuple_SetItem(tuple, 0, PyString_FromString("BOTTOM"));
	else
	 	PyTuple_SetItem(tuple, 0, PyString_FromString("TEXT"));

	printf("addText %s with id %d\n", value, type);

 	PyTuple_SetItem(tuple, 1, PyString_FromString(value));
	
	if(type > 2)
	  PyTuple_SetItem(tuple, 2, PyInt_FromLong(type-2));
	else	
	  PyTuple_SetItem(tuple, 2, PyInt_FromLong(-1));
	
	PyList_Append(mmiScreen, tuple);
	
	return 0;
}

int eDVBCI_UI::mmiScreenFinish(int slot)
{
	printf("eDVBCI_UI::mmiScreenFinish\n");

	mmiScreenReady = 1;

	return 0;
}

int eDVBCI_UI::getMMIState(int slot)
{
	return eDVBCIInterfaces::getInstance()->getMMIState(slot);
}

PyObject *eDVBCI_UI::getMMIScreen(int slot)
{
	if(mmiScreenReady != 1)
		return Py_None;
		
	mmiScreenReady = 0;

	return mmiScreen;
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eDVBCI_UI> init_dvbciui(eAutoInitNumbers::rc, "DVB-CI UI");
