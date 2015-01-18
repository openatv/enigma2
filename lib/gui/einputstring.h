#ifndef __lib_gui_einputstring_h
#define __lib_gui_einputstring_h

#include <lib/gui/einput.h>

class eInputContentString: public eInputContent
{
	DECLARE_REF(eInputContentString);
public:
	eInputContentString();

	void getDisplay(std::string &res, int &cursor);
	void moveCursor(int dir);
	int haveKey(int code, int overwrite);
	void deleteChar(int dir);
	int isValid();

	void validate();

	void setText(const std::string &text);
	std::string getText();

private:
	void insertChar(int pos, int ch);

	std::string m_string;

	int m_cursor, m_len;
};

#endif
