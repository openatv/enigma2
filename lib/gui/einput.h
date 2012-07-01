#ifndef __lib_gui_einput_h
#define __lib_gui_einput_h

#include <lib/gui/ewidget.h>
#include <lib/python/connections.h>

class eInputContent;

class eInput: public eWidget
{
public:
	eInput(eWidget *parent);
	virtual ~eInput();
	PSignal0<void> changed;

	int m_cursor;

	enum {
		INPUT_ACTIONS,
		ASCII_ACTIONS
	};

	enum InputActions {
		moveLeft, 
		moveRight, 
		moveHome, 
		moveEnd,
		deleteForward,
		deleteBackward,
		toggleOverwrite,
		accept
	};

	enum AsciiActions {
		gotAsciiCode
	};

	void setContent(eInputContent *cnt);
	
	void setOverwriteMode(int o);
	
	void setFont(gFont *font);
protected:
	ePtr<gFont> m_font;
	int m_mode, m_have_focus;
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
	
	enum {
		deleteForward, deleteBackward
	};
	virtual void deleteChar(int dir)=0;
	
		/* no movement keys except stuff like '.' or so*/
	virtual int haveKey(int code, int overwrite)=0;
	
	virtual int isValid()=0;
	virtual void validate()=0;
protected:
	eInput *m_input;
};

#endif
