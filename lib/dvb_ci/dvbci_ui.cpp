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
	:mmiScreen(NULL)
	,mmiTuplePos(0)
	,mmiScreenReady(0)
{
	ASSERT(!instance);
	instance = this;
	for(int i=0;i<MAX_SLOTS;i++)
		state[i] = 0;		//no module
}

eDVBCI_UI::~eDVBCI_UI()
{
	if(mmiScreen)
		Py_DECREF(mmiScreen);
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
	
	if(newState == 2)		//enable TS
		eDVBCIInterfaces::getInstance()->enableTS(slot, 1);
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
	return;
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

int eDVBCI_UI::initialize(int slot)
{
	eDVBCIInterfaces::getInstance()->initialize(slot);
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

int eDVBCI_UI::availableMMI(int slot)
{
	return mmiScreenReady;
}

int eDVBCI_UI::mmiScreenEnq(int slot, int blind, int answerLen, char *text)
{
	mmiScreenReady = 0;

	if(mmiScreen)
		Py_DECREF(mmiScreen);
	mmiScreen = PyList_New(2);

	PyObject *tuple = PyTuple_New(1);
	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("ENQ"));
	PyList_SET_ITEM(mmiScreen, 0, tuple);

	tuple = PyTuple_New(4);
	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("PIN"));
	PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(answerLen));
	PyTuple_SET_ITEM(tuple, 2, PyString_FromString(text));
	PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(blind));

	PyList_SET_ITEM(mmiScreen, 1, tuple);

	mmiScreenReady = 1;

	return 0;
}

int eDVBCI_UI::mmiScreenBegin(int slot, int listmenu)
{
	printf("eDVBCI_UI::mmiScreenBegin\n");

	mmiScreenReady = 0;

	if(mmiScreen)
		Py_DECREF(mmiScreen);
	mmiScreen = PyList_New(1);

	PyObject *tuple = PyTuple_New(1);
	if(listmenu == 0)				//menu
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("MENU"));
	else 	//list
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("LIST"));

	PyList_SET_ITEM(mmiScreen, 0, tuple);

	mmiTuplePos = 1;

	return 0;
}

int eDVBCI_UI::mmiScreenAddText(int slot, int type, char *value)
{
	eDebug("eDVBCI_UI::mmiScreenAddText(%s)",value);

	PyObject *tuple = PyTuple_New(3);

	if(type == 0)					//title
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("TITLE"));
	else if(type == 1)				//subtitle
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("SUBTITLE"));
	else if(type == 2)				//bottom
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("BOTTOM"));
	else
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("TEXT"));

	eDebug("addText %s with id %d", value, type);

	PyTuple_SET_ITEM(tuple, 1, PyString_FromString(value));

	if(type > 2)
		PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(type-2));
	else
		PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(-1));

	PyList_Append(mmiScreen, tuple);
	Py_DECREF(tuple);

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
	if(mmiScreenReady)
	{
		mmiScreenReady = 0;
		Py_INCREF(mmiScreen);
		return mmiScreen;
	}
	Py_INCREF(Py_None);
	return Py_None;
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eDVBCI_UI> init_dvbciui(eAutoInitNumbers::rc, "DVB-CI UI");
