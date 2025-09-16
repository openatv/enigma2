#ifndef __lib_gui_ewidget_h
#define __lib_gui_ewidget_h

#include <lib/base/eptrlist.h> /* for eSmartPtrList */
#include <lib/gdi/grc.h> /* for gRegion */
#include <lib/gui/ewidgetanimation.h>
#include <lib/gui/ewindowstyle.h> /* for eWindowStyle */
#include <sstream>
#include <vector>

#define MAX_LAYER 16

class eWidgetDesktop;

class eWidget {
	friend class eWidgetDesktop;

public:
	eWidget(eWidget* parent);
	virtual ~eWidget();

	void move(ePoint pos);
	void resize(eSize size);

	ePoint position() const { return m_position; }
	eSize size() const { return m_size; }
	eSize csize() const { return m_client_size; }

	virtual void invalidate(const gRegion& region = gRegion::invalidRegion());

	/* the window were to attach childs to. Normally, this
	   is "this", but it can be overridden in case a widget
	   has a "client area", which is implemented as a child
	   widget. eWindow overrides this, for example. */
	virtual eWidget* child() { return this; }

	eWidget* getParent() { return m_parent; }

	void show();
	void hide();

	void raise();
	void lower();

	void destruct();

	SWIG_VOID(int) getStyle(ePtr<eWindowStyle>& SWIG_NAMED_OUTPUT(style)) {
		if (!m_style)
			return 1;
		style = m_style;
		return 0;
	}
	void setStyle(eWindowStyle* style) { m_style = style; }

	virtual void setBackgroundColor(const gRGB& col);
	virtual void clearBackgroundColor() { m_have_background_color = false; }

	virtual void setBorderWidth(int width) { setWidgetBorderWidth(width); }
	virtual void setBorderColor(const gRGB& color) { setWidgetBorderColor(color); }

	virtual void setWidgetBorderWidth(int width) {
		m_border_width = width;
		invalidate();
	}
	virtual void setWidgetBorderColor(const gRGB& color) {
		m_border_color = color;
		m_have_border_color = true;
		invalidate();
	}

	virtual void setWidgetAlphaBlend(bool blend) {
		m_alphaBlend = blend;
		invalidate();
	}

	virtual void setPadding(const eRect& padding) { m_padding = padding; }
	virtual eRect getPadding() { return m_padding; }

	void setZPosition(int z);
	void setTransparent(int transp);

	/* untested code */
	int isVisible() { return (m_vis & wVisShow) && ((!m_parent) || m_parent->isVisible()); }

	int isLowered() { return (m_lowered > 0); }

	int isTransparent() { return m_vis & wVisTransparent; }

	ePoint getAbsolutePosition();

	eWidgetAnimation m_animation;

	int getTag() const { return m_tag; }
	void setTag(int tag) { m_tag = tag; }

private:
	eWidgetDesktop* m_desktop;

	enum {
		wVisShow = 1,
		wVisTransparent = 2,
	};

	int m_vis;

	int m_layer;

	ePtrList<eWidget> m_childs;
	ePoint m_position;
	eSize m_size, m_client_size;
	/* will be accounted when there's a client offset */
	eSize m_client_offset;
	eWidget* m_parent;

	ePtr<eWindowStyle> m_style;

	void insertIntoParent();
	void doPaint(gPainter& painter, const gRegion& region, int layer);
	void recalcClipRegionsWhenVisible();
	void parentRemoved();

	eWidget *m_current_focus, *m_focus_owner;

	int m_z_position;
	int m_lowered;
	int m_notify_child_on_position_change;

	bool m_gradient_set;
	bool m_gradient_alphablend;
	uint8_t m_gradient_direction;
	std::vector<gRGB> m_gradient_colors;

	int m_cornerRadius;
	uint8_t m_cornerRadiusEdges;
	int m_tag;

protected:
	void mayKillFocus();

	gRGB m_background_color;
	bool m_have_background_color = false;

	bool m_have_border_color;
	int m_border_width;
	gRGB m_border_color;
	eRect m_padding;
	bool m_alphaBlend = false;
	uint8_t m_align = eStackAlignNone;
	virtual void invalidateChilds() {} // This will be overwritten in subclass

public:
	// all in local space!
	gRegion m_clip_region, m_visible_region, m_visible_with_childs;
	struct eWidgetDesktopCompBuffer* m_comp_buffer[MAX_LAYER];

	enum eWidgetEvent {
		evtPaint,
		evtKey,
		evtChangedPosition,
		evtChangedSize,
		evtParentChangedPosition,
		evtParentVisibilityChanged,
		evtWillChangePosition, /* new size is eRect *data */
		evtWillChangeSize,
		evtAction,
		evtFocusGot,
		evtFocusLost,
		evtUserWidget,
	};
	virtual int event(int event, void* data = 0, void* data2 = 0);
	void setFocus(eWidget* focus);

	/* enable this if you need the absolute position of the widget */
	void setPositionNotifyChild(int n) { m_notify_child_on_position_change = 1; }

	void notifyShowHide();

	void setBackgroundGradient(const gRGB& startcolor, const gRGB& midcolor, const gRGB& endcolor, uint8_t direction, bool alphablend);

	void setCornerRadius(int radius, uint8_t edges);
	uint8_t getCornerRadiusEdges() { return m_cornerRadiusEdges; }
	int getCornerRadius();

	bool isGradientSet() { return m_gradient_set; }

	enum {
		GRADIENT_OFF = 0,
		GRADIENT_VERTICAL = 1,
		GRADIENT_HORIZONTAL = 2
	};

	enum {
		RADIUS_TOP_LEFT = 1,
		RADIUS_TOP_RIGHT = 2,
		RADIUS_TOP = 3,
		RADIUS_BOTTOM_LEFT = 4,
		RADIUS_BOTTOM_RIGHT = 8,
		RADIUS_BOTTOM = 12,
		RADIUS_LEFT = 5,
		RADIUS_RIGHT = 10,
		RADIUS_ALL = 15,
	};

	enum {
		eStackAlignNone = 0,
		eStackAlignLeft = 1,
		eStackAlignRight = 2,
		eStackAlignTop = 4,
		eStackAlignBottom = 8,
		eStackAlignCenter = 16
	};

	void setAlign(uint8_t a) { m_align = a; }
	uint8_t align() const { return m_align; }
	eWidget* m_stack;
	void setStack(eWidget* stack) { m_stack = stack; }

	virtual std::string getClassName() const { return std::string("eWidget"); }

	virtual std::string dumpObject() const {
		std::ostringstream oss;
		oss << "<" << getClassName() << " Size=(" << size().width() << "," << size().height() << ") Position=(" << position().x() << "," << position().y() << ") Tag=" << getTag() << ">";
		return oss.str();
	}
};

extern eWidgetDesktop* getDesktop(int which);

#endif
