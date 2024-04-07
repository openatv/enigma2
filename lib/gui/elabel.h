#ifndef __lib_gui_elabel_h
#define __lib_gui_elabel_h

#include <lib/gui/ewidget.h>

class eLabel : public eWidget
{
public:
	eLabel(eWidget *parent, int markedPos = -1);
	void setText(const std::string &string);
	void setMarkedPos(int markedPos);
	void setFont(gFont *font);
	gFont *getFont() { return m_font; }

	enum
	{
		alignLeft,
		alignTop = alignLeft,
		alignCenter,
		alignRight,
		alignBottom = alignRight,
		alignBlock,
		alignBidi
	};

	void setVAlign(int align);
	void setHAlign(int align);

	void setForegroundColor(const gRGB &col);
	void setShadowColor(const gRGB &col);
	void setShadowOffset(const ePoint &offset) { m_shadow_offset = offset; }
	void setBorderColor(const gRGB &col) override { setTextBorderColor(col); } // WILL BE CHANGED !!!!
	void setBorderWidth(int width) override { setTextBorderWidth(width); } // WILL BE CHANGED !!!!
	void setTextBorderColor(const gRGB &col);
	void setTextBorderWidth(int width) { m_text_border_width = width; }
	void setWrap(int wrap);
	void setNoWrap(int nowrap) { setWrap((nowrap == 1) ? 0 : 1); } // DEPRECATED
	void clearForegroundColor();
	int getWrap() const { return m_wrap; }
	int getNoWrap() const { return (m_wrap == 0) ? 1 : 0; } // DEPRECATED
	void setTextPadding(const eRect &padding) { m_padding = padding; }
	void setAlphatest(int alphatest);

	eSize calculateSize();
	static eSize calculateTextSize(gFont *font, const std::string &string, eSize targetSize, bool nowrap = false);

protected:
	ePtr<gFont> m_font;
	int m_valign, m_halign;
	std::string m_text;
	int event(int event, void *data = 0, void *data2 = 0);
	int m_pos;
	int m_text_offset = 0;

private:
	int m_have_foreground_color = 0;
	int m_have_shadow_color = 0;
	gRGB m_foreground_color, m_shadow_color, m_text_border_color;
	ePoint m_shadow_offset;
	eRect m_padding = eRect(0, 0, 0, 0);
	int m_text_border_width = 0;
	int m_wrap = 1;
	bool m_blend = false;

	enum eLabelEvent
	{
		evtChangedText = evtUserWidget,
		evtChangedFont,
		evtChangedAlignment,
		evtChangedMarkedPos
	};
};

#endif
