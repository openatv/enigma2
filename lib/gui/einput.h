#ifndef __lib_gui_einput_h
#define __lib_gui_einput_h

#include <lib/gui/elabel.h>
#include <lib/python/connections.h>

class eInputContent;

class eInput: public eLabel
{
public:
	eInput(eWidget *parent);
	virtual ~eInput();
	PSignal0<void> changed;

	int m_cursor;
	
	enum InputActions {
		moveLeft, 
		moveRight, 
		moveHome, 
		moveEnd,
		deleteChar
	};
	
	void setContent(eInputContent *cnt);
	
	int getNumber();
protected:
	ePtr<eInputContent> m_content;
	int event(int event, void *data=0, void *data2=0);
};

class eInputContent: public iObject
{
public:
		/* management stuff */
	void setInput(eInput *widget);
		/* display stuff */
	virtual void getDisplay(std::string &res, int &cursor)=0;

		/* movement / user actions */
	enum {
		dirLeft, dirRight,
		dirHome, dirEnd,
			/* contents can define their own directions */
		dirUser
	};
	virtual void moveCursor(int dir)=0;
		/* no movement keys except stuff like '.' or so*/
	virtual int haveKey(int code)=0;
	
	virtual int isValid()=0;
protected:
	eInput *m_input;
};

class eInputContentNumber: public eInputContent
{
	DECLARE_REF(eInputContentNumber);
public:
	eInputContentNumber(int cur, int min, int max);

	void getDisplay(std::string &res, int &cursor);
	void moveCursor(int dir);
	int haveKey(int code);
	int isValid();
	
private:
	void recalcLen();
	
	void insertDigit(int pos, int dig);
	
	int m_value;
	int m_cursor, m_len;
	
	int m_min, m_max;
};

#endif
