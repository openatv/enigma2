#ifndef __dvbci_ui_h
#define __dvbci_ui_h

#include <string>
#include <Python.h>

#define MAX_SLOTS	2	

class eDVBCI_UI
{
	int state[MAX_SLOTS];
	static eDVBCI_UI *instance;
	std::string appName;
protected:
public:
	eDVBCI_UI();
	~eDVBCI_UI();

	static eDVBCI_UI *getInstance();
	
	int getState(int slot);
	void setState(int slot, int state);
	std::string getAppName(int slot);
	void setAppName(int slot, const char *name);
	void setReset(int slot);
	int initialize(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int availableMMI(int slot);
	int getMMIState(int slot);

	int answerMenu(int slot, int answer);
	int answerEnq(int slot, char *val);
	int cancelEnq(int slot);

	PyObject *eDVBCI_UI::getMMIScreen(int slot);
	PyObject *mmiScreen;
	int mmiTuplePos;
	int mmiScreenReady;

	int mmiScreenEnq(int slot, int blind, int answerLen, char *text);
	int mmiScreenBegin(int slot, int listmenu);
	int mmiScreenAddText(int slot, int type, char *value);
	int mmiScreenFinish(int slot);
};

#endif
