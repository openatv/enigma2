#ifndef __lib_gui_elabel_h
#define __lib_gui_elabel_h

#include <lib/gui/ewidget.h>

class eLabel: public eWidget
{
public:
	eLabel(eWidget *parent, int markedPos = -1);
	void setText(const std::string &string);
	void setMarkedPos(int markedPos);
	void setFont(gFont *font);
	gFont* getFont();

	enum
	{
		alignLeft,
		alignTop=alignLeft,
		alignCenter,
		alignRight,
		alignBottom=alignRight,
		alignBlock,
		alignBidi
	};

	void setVAlign(int align);
	void setHAlign(int align);

	void setForegroundColor(const gRGB &col);
	void setShadowColor(const gRGB &col);
	void setShadowOffset(const ePoint &offset);
	void setBorderColor(const gRGB &col);
	void setBorderWidth(int size);
	void setNoWrap(int nowrap);
	void clearForegroundColor();
	int getNoWrap() { return m_nowrap; }

	eSize calculateSize();
	static eSize calculateTextSize(gFont* font, const std::string &string, eSize targetSize, bool nowrap = false);
protected:
	ePtr<gFont> m_font;
	int m_valign, m_halign;
	std::string m_text;
	int event(int event, void *data=0, void *data2=0);
	int m_pos;
private:
	int m_have_foreground_color, m_have_shadow_color;
	gRGB m_foreground_color, m_shadow_color, m_border_color;
	ePoint m_shadow_offset;
	int m_border_size;
	int m_nowrap;

	enum eLabelEvent
	{
		evtChangedText = evtUserWidget,
		evtChangedFont,
		evtChangedAlignment,
		evtChangedMarkedPos
	};
};

#endif
