#ifndef __dvbci_ui_h
#define __dvbci_ui_h

#include <string>
                /* avoid warnigs :) */
#undef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
#include <Python.h>

#define MAX_SLOTS 4

struct slot_ui_data
{
	std::string appName;
	int state;
	PyObject *mmiScreen;
	int mmiTuplePos;
	int mmiScreenReady;
};

class eDVBCI_UI
{
	static eDVBCI_UI *instance;
	slot_ui_data slotdata[MAX_SLOTS];
#ifdef SWIG
	eDVBCI_UI();
	~eDVBCI_UI();
#endif
public:
#ifndef SWIG
	eDVBCI_UI();
	~eDVBCI_UI();
#endif
	static eDVBCI_UI *getInstance();

	int getState(int slot);
	void setState(int slot, int state);
	std::string getAppName(int slot);
	void setAppName(int slot, const char *name);
	void setInit(int slot);
	void setReset(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int availableMMI(int slot);
	int getMMIState(int slot);

	int answerMenu(int slot, int answer);
	int answerEnq(int slot, char *val);
	int cancelEnq(int slot);

	PyObject *getMMIScreen(int slot);

	int mmiScreenEnq(int slot, int blind, int answerLen, char *text);
	int mmiScreenBegin(int slot, int listmenu);
	int mmiScreenAddText(int slot, int type, char *value);
	int mmiScreenFinish(int slot);
};

#endif
