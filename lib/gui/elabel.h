#ifndef __lib_gui_elabel_h
#define __lib_gui_elabel_h

#include <lib/gui/ewidget.h>

class eLabel: public eWidget
{
public:
	eLabel(eWidget *parent);
	void setText(const std::string &string);
protected:
	int event(int event, void *data=0, void *data2=0);
private:
	enum eLabelEvent
	{
		evtChangedText = evtUserWidget
	};
	std::string m_text;
};

#endif
