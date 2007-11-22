#ifndef __mmi_ui_h
#define __mmi_ui_h

#include <string>
                /* avoid warnigs :) */
#undef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
#include <lib/python/python.h>

#ifndef SWIG
struct slot_ui_data
{
	std::string appName;
	int state;
	ePyObject mmiScreen;
	int mmiTuplePos;
	int mmiScreenReady;
};
#endif

class eMMI_UI: public Object
{
	int m_max_slots;
	virtual void stateChanged(int)=0;
protected:
	slot_ui_data *slotdata;
	eMMI_UI(int max_slots);
	virtual ~eMMI_UI();
public:
	int getState(int slot);
	void setState(int slot, int state);
	std::string getAppName(int slot);
	void setAppName(int slot, const char *name);
#ifndef SWIG
	virtual void setInit(int slot)=0;
	virtual void setReset(int slot)=0;
	virtual int startMMI(int slot)=0;
	virtual int stopMMI(int slot)=0;
	virtual int answerMenu(int slot, int answer)=0;
	virtual int answerEnq(int slot, char *val)=0;
	virtual int cancelEnq(int slot)=0;
	virtual int getMMIState(int slot)=0;
#endif
	int availableMMI(int slot);
	PyObject *getMMIScreen(int slot);
#ifndef SWIG
	int processMMIData(int slot, const unsigned char *tag, const void *data, int len);
	int mmiScreenClose(int slot, int timeout);
	int mmiScreenEnq(int slot, int blind, int answerLen, char *text);
	int mmiScreenBegin(int slot, int listmenu);
	int mmiScreenAddText(int slot, int type, char *value);
	int mmiScreenFinish(int slot);
	void mmiSessionDestroyed(int slot);
#endif
};

#endif
