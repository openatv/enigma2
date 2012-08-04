#ifndef __lib_gui_einputnumber_h
#define __lib_gui_einputnumber_h

#include <lib/gui/einput.h>

class eInputContentNumber: public eInputContent
{
	DECLARE_REF(eInputContentNumber);
public:
	eInputContentNumber(int cur, int min, int max);

	void getDisplay(std::string &res, int &cursor);
	void moveCursor(int dir);
	int haveKey(int code, int overwrite);
	void deleteChar(int dir);
	int isValid();
	
	void validate();
	
	void setValue(int num);
	int getValue();
	
private:
	void recalcLen();
	
	void insertDigit(int pos, int dig);
	
	int m_value;
	int m_cursor, m_len;
	
	int m_min, m_max;
};


#endif
