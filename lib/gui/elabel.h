#ifndef __lib_gui_elabel_h
#define __lib_gui_elabel_h

#include <lib/gui/ewidget.h>

class eLabel: public eWidget
{
public:
	eLabel(eWidget *parent);
	void setText(const std::string &string);
	void setFont(gFont *font);
	
	enum
	{
		alignLeft,
		alignTop=alignLeft,
		alignCenter,
		alignRight,
		alignBottom=alignRight,
		alignBlock
	};
	
	void setVAlign(int align);
	void setHAlign(int align);
protected:
	ePtr<gFont> m_font;
	int m_valign, m_halign;
	std::string m_text;
	int event(int event, void *data=0, void *data2=0);
private:
	enum eLabelEvent
	{
		evtChangedText = evtUserWidget,
		evtChangedFont,
		evtChangedAlignment
	};
};

#endif
