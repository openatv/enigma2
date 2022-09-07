#ifndef __lib_gui_eslider_h
#define __lib_gui_eslider_h

#include <lib/gui/ewidget.h>

class eSlider: public eWidget
{
	int m_alphatest;
public:
	eSlider(eWidget *parent);
	void setValue(int val);
	void setStartEnd(int start, int end, bool pixel = false);
	void setRange(int min, int max);
	enum { orHorizontal, orVertical };
	void setOrientation(int orientation, int swapped = 0);
	void setBorderWidth(int width);
	void setBorderColor(const gRGB &color);
	void setForegroundColor(const gRGB &color);
	void setBackgroundColor(const gRGB &color); // FIXME overwrite setBackgroundColor and m_have_background_color from eWidget
	void setPixmap(gPixmap *pixmap);
	void setPixmap(ePtr<gPixmap> &pixmap);
	void setBackgroundPixmap(gPixmap *pixmap);
	void setBackgroundPixmap(ePtr<gPixmap> &pixmap);
	void setAlphatest(int alphatest); /* 1 for alphatest, 2 for alphablend */
	void setIsScrollbar();
	static void setDefaultBorderWidth(int borderwidth) { 
			defaultSliderBorderWidth = borderwidth; 
		}

	enum {
		DefaultBorderWidth = 0
	};

	int getBorderWidth() { return m_border_width; }


	// Mapping functions to have the same attributes for eListBox and Scrollabel
	void setScrollbarBorderWidth(int width);
	void setScrollbarBorderColor(const gRGB &color);
	void setScrollbarForegroundPixmap(gPixmap *pixmap);
	void setScrollbarForegroundPixmap(ePtr<gPixmap> &pixmap);
	void setScrollbarBackgroundPixmap(gPixmap *pixmap);
	void setScrollbarBackgroundPixmap(ePtr<gPixmap> &pixmap);
	void setScrollbarForegroundColor(const gRGB &color);
	void setScrollbarBackgroundColor(const gRGB &color); // dummy function not implemented yet reserved for future use.

protected:
	int event(int event, void *data=0, void *data2=0);
private:
	enum eSliderEvent
	{
		evtChangedSlider = evtUserWidget
	};
	bool m_have_border_color, m_have_foreground_color, m_have_background_color, m_scrollbar, m_pixel_mode;
	int m_min, m_max, m_value, m_start, m_orientation, m_orientation_swapped, m_border_width;
	ePtr<gPixmap> m_pixmap, m_backgroundpixmap;
	ePtr<gPixmap> m_scrollbarslidepixmap, m_scrollbarslidebackgroundpixmap;

	gRegion m_currently_filled;
	gRGB m_border_color, m_foreground_color, m_background_color;

	static int defaultSliderBorderWidth;

};

#endif
