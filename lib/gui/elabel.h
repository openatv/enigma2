#ifndef __lib_gui_elabel_h
#define __lib_gui_elabel_h

#include <lib/gui/ewidget.h>

struct eScrollConfig {
	enum {
		scrollNone,
		scrollLeft,
		scrollRight,
		scrollTop,
		scrollBottom
	};

	enum {
		scrollModeNormal,
		scrollModeCached,
		scrollModeBounce,
		scrollModeBounceCached,
		scrollModeRoll
	};

	int direction = scrollNone;
	long delay = 100;
	long startDelay = 0;
	long endDelay = 0;
	int repeat = 0;
	int stepSize = 1;
	int mode = scrollModeNormal;
	bool cached = false;
};


class eLabel : public eWidget {
public:
	eLabel(eWidget* parent, int markedPos = -1);
	void setText(const std::string& string);
	void setMarkedPos(int markedPos);
	void setFont(gFont* font);
	gFont* getFont() { return m_font; }

	enum {
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

	void setForegroundColor(const gRGB& col);
	void setShadowColor(const gRGB& col);
	void setShadowOffset(const ePoint& offset) { m_shadow_offset = offset; }
	void setBorderColor(const gRGB& col) override { setTextBorderColor(col); } // WILL BE CHANGED !!!!
	void setBorderWidth(int width) override { setTextBorderWidth(width); } // WILL BE CHANGED !!!!
	void setTextBorderColor(const gRGB& col);
	void setTextBorderWidth(int width) { m_text_border_width = width; }
	void setWrap(int wrap);
	void setNoWrap(int nowrap) { setWrap((nowrap == 1) ? 0 : 1); } // DEPRECATED
	void setUnderline(bool underline);
	void setScrollText(int direction, long delay, long startDelay, long endDelay, int repeat, int stepSize, int mode);
	void clearForegroundColor();
	int getWrap() const { return m_wrap; }
	int getNoWrap() const { return (m_wrap == 0) ? 1 : 0; } // DEPRECATED
	void setAlphatest(int alphatest);
	void setTabWidth(int width);
	gRGB getForegroundColor(int styleID = 0);
	eSize calculateSize();
	static eSize calculateTextSize(gFont* font, const std::string& string, eSize targetSize, bool nowrap = false);

protected:
	ePtr<gFont> m_font;
	int m_valign, m_halign;
	std::string m_text;
	int event(int event, void* data = 0, void* data2 = 0);
	int m_pos;
	int m_text_offset = 0;
	int m_text_shaddowoffset = 0;
	std::string getClassName() const override { return std::string("eLabel"); }

private:
	int buildFlags() const {
		int flags = 0;
		if (m_valign == alignTop)
			flags |= gPainter::RT_VALIGN_TOP;
		else if (m_valign == alignCenter)
			flags |= gPainter::RT_VALIGN_CENTER;
		else if (m_valign == alignBottom)
			flags |= gPainter::RT_VALIGN_BOTTOM;

		if (m_halign == alignLeft)
			flags |= gPainter::RT_HALIGN_LEFT;
		else if (m_halign == alignCenter)
			flags |= gPainter::RT_HALIGN_CENTER;
		else if (m_halign == alignRight)
			flags |= gPainter::RT_HALIGN_RIGHT;
		else if (m_halign == alignBlock)
			flags |= gPainter::RT_HALIGN_BLOCK;

		if (m_wrap == 1)
			flags |= gPainter::RT_WRAP;
		else if (m_wrap == 2)
			flags |= gPainter::RT_ELLIPSIS;

		if (m_underline)
			flags |= gPainter::RT_UNDERLINE;

		return flags;
	}

	int m_have_foreground_color = 0;
	int m_have_shadow_color = 0;
	gRGB m_foreground_color, m_shadow_color, m_text_border_color;
	ePoint m_shadow_offset;
	int m_text_border_width = 0;
	int m_wrap = 1;
	bool m_blend = false;
	bool m_underline = false;
	int m_tab_width = -1;
	// Scroll
	eScrollConfig m_scroll_config;
	int m_repeat_count = 0;
	bool m_scroll_text = false;
	bool m_scroll_started = false;
	int m_scroll_pos = 0;
	bool m_end_delay_active = false;
	bool m_scroll_swap = false;
	bool m_paint_pixmap = false;
	eSize m_text_size;
	ePtr<eTimer> scrollTimer;
	void updateScrollPosition();
	void updateTextSize();
	void createScrollPixmap();
	void stopScroll();
	ePtr<gPixmap> m_textPixmap;

	enum eLabelEvent {
		evtChangedText = evtUserWidget,
		evtChangedFont,
		evtChangedAlignment,
		evtChangedMarkedPos
	};
};

#endif
