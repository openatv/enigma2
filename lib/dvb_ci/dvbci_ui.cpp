#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <string>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>

eDVBCI_UI *eDVBCI_UI::instance;

eDVBCI_UI::eDVBCI_UI()
{
	ASSERT(!instance);
	instance = this;
	for(int i=0;i<MAX_SLOTS;++i)
	{
		slotdata[i].mmiScreenReady=0;
		slotdata[i].mmiTuplePos=0;
		slotdata[i].state=-1;
	}
}

eDVBCI_UI::~eDVBCI_UI()
{
	for(int i=0;i<MAX_SLOTS;++i)
	{
		if (slotdata[i].mmiScreen)
			Py_DECREF(slotdata[i].mmiScreen);
	}
}

eDVBCI_UI *eDVBCI_UI::getInstance()
{
	return instance;
}

int eDVBCI_UI::getState(int slot)
{
	if (slot < MAX_SLOTS)
		return slotdata[slot].state;
	return 0;
}

void eDVBCI_UI::setState(int slot, int newState)
{
	if (slot < MAX_SLOTS)
	{
		slotdata[slot].state = newState;
		/*emit*/ ciStateChanged(slot);
	}
}

std::string eDVBCI_UI::getAppName(int slot)
{
	if (slot < MAX_SLOTS)
		return slotdata[slot].appName;
	return "";
}

void eDVBCI_UI::setAppName(int slot, const char *name)
{
	if (slot < MAX_SLOTS)
		slotdata[slot].appName = name;
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

int eDVBCI_UI::availableMMI(int slot)
{
	if (slot < MAX_SLOTS)
		return slotdata[slot].mmiScreenReady;
	return false;
}

int eDVBCI_UI::mmiScreenClose(int slot, int timeout)
{
	if (slot >= MAX_SLOTS)
		return 0;

	slot_ui_data &data = slotdata[slot];

	data.mmiScreenReady = 0;

	if (data.mmiScreen)
		Py_DECREF(data.mmiScreen);
	data.mmiScreen = PyList_New(1);

	ePyObject tuple = PyTuple_New(2);
	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("CLOSE"));
	PyTuple_SET_ITEM(tuple, 1, PyLong_FromLong(timeout));
	PyList_SET_ITEM(data.mmiScreen, 0, tuple);
	data.mmiScreenReady = 1;
	/*emit*/ ciStateChanged(slot);
	return 0;
}

int eDVBCI_UI::mmiScreenEnq(int slot, int blind, int answerLen, char *text)
{
	if (slot >= MAX_SLOTS)
		return 0;

	slot_ui_data &data = slotdata[slot];

	data.mmiScreenReady = 0;

	if (data.mmiScreen)
		Py_DECREF(data.mmiScreen);
	data.mmiScreen = PyList_New(2);

	ePyObject tuple = PyTuple_New(1);
	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("ENQ"));
	PyList_SET_ITEM(data.mmiScreen, 0, tuple);

	tuple = PyTuple_New(4);
	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("PIN"));
	PyTuple_SET_ITEM(tuple, 1, PyInt_FromLong(answerLen));
	PyTuple_SET_ITEM(tuple, 2, PyString_FromString(text));
	PyTuple_SET_ITEM(tuple, 3, PyInt_FromLong(blind));

	PyList_SET_ITEM(data.mmiScreen, 1, tuple);

	data.mmiScreenReady = 1;

	/*emit*/ ciStateChanged(slot);

	return 0;
}

int eDVBCI_UI::mmiScreenBegin(int slot, int listmenu)
{
	if (slot >= MAX_SLOTS)
		return 0;

	eDebug("eDVBCI_UI::mmiScreenBegin");

	slot_ui_data &data = slotdata[slot];

	data.mmiScreenReady = 0;

	if (data.mmiScreen)
		Py_DECREF(data.mmiScreen);

	data.mmiScreen = PyList_New(1);

	ePyObject tuple = PyTuple_New(1);
	if (listmenu == 0)				//menu
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("MENU"));
	else 	//list
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("LIST"));

	PyList_SET_ITEM(data.mmiScreen, 0, tuple);

	data.mmiTuplePos = 1;

	return 0;
}

int eDVBCI_UI::mmiScreenAddText(int slot, int type, char *value)
{
	if (slot >= MAX_SLOTS)
		return 0;

	eDebug("eDVBCI_UI::mmiScreenAddText(%s)",value ? value : "");

	slot_ui_data &data = slotdata[slot];

	ePyObject tuple = PyTuple_New(3);

	if (type == 0)					//title
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("TITLE"));
	else if (type == 1)				//subtitle
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("SUBTITLE"));
	else if (type == 2)				//bottom
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("BOTTOM"));
	else
	 	PyTuple_SET_ITEM(tuple, 0, PyString_FromString("TEXT"));

	eDebug("addText %s with id %d", value, type);

	PyTuple_SET_ITEM(tuple, 1, PyString_FromString(value));

	if (type > 2)
		PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(type-2));
	else
		PyTuple_SET_ITEM(tuple, 2, PyInt_FromLong(-1));

	PyList_Append(data.mmiScreen, tuple);
	Py_DECREF(tuple);

	return 0;
}

int eDVBCI_UI::mmiScreenFinish(int slot)
{
	if (slot < MAX_SLOTS)
	{
		eDebug("eDVBCI_UI::mmiScreenFinish");
		slotdata[slot].mmiScreenReady = 1;
		/*emit*/ ciStateChanged(slot);
	}
	return 0;
}

void eDVBCI_UI::mmiSessionDestroyed(int slot)
{
	/*emit*/ ciStateChanged(slot);
}

int eDVBCI_UI::getMMIState(int slot)
{
	return eDVBCIInterfaces::getInstance()->getMMIState(slot);
}

PyObject *eDVBCI_UI::getMMIScreen(int slot)
{
	if (slot < MAX_SLOTS)
	{
		slot_ui_data &data = slotdata[slot];
		if (data.mmiScreenReady)
		{
			data.mmiScreenReady = 0;
			Py_INCREF(data.mmiScreen);
			return data.mmiScreen;
		}
	}
	Py_INCREF(Py_None);
	return Py_None;
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eDVBCI_UI> init_dvbciui(eAutoInitNumbers::rc, "DVB-CI UI");
