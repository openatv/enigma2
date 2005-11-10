#ifndef __dvbci_ui_h
#define __dvbci_ui_h

#define MAX_SLOTS	2	

class eDVBCI_UI
{
	int state[MAX_SLOTS];
	static eDVBCI_UI *instance;
protected:
public:
	eDVBCI_UI();
	~eDVBCI_UI();

	static eDVBCI_UI *getInstance();
	
	int eDVBCI_UI::getState(int slot);
};

#endif
