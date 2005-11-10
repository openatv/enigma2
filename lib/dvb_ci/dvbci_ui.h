#ifndef __dvbci_ui_h
#define __dvbci_ui_h

#include <string>

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
};

#endif
