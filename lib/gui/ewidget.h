#ifndef __lib_gui_ewidget_h
#define __lib_gui_ewidget_h

#include <lib/gdi/grc.h> /* for gRegion */
#include <lib/base/eptrlist.h> /* for eSmartPtrList */
#include <lib/gui/ewindowstyle.h> /* for eWindowStyle */
#include <lib/gui/ewidgetanimation.h>

#define MAX_LAYER 16

class eWidgetDesktop;

class eWidget
{
	friend class eWidgetDesktop;
public:
	eWidget(eWidget *parent);
	virtual ~eWidget();

	void move(ePoint pos);
	void resize(eSize size);

	ePoint position() const { return m_position; }
	eSize size() const { return m_size; }
	eSize csize() const { return m_client_size; }

	void invalidate(const gRegion &region = gRegion::invalidRegion());

		/* the window were to attach childs to. Normally, this
		   is "this", but it can be overridden in case a widget
		   has a "client area", which is implemented as a child
		   widget. eWindow overrides this, for example. */
	virtual eWidget *child() { return this; }

	eWidget *getParent() { return m_parent; }

	void show();
	void hide();

	void raise();
	void lower();

	void destruct();

	SWIG_VOID(int) getStyle(ePtr<eWindowStyle> &SWIG_NAMED_OUTPUT(style)) { if (!m_style) return 1; style = m_style; return 0; }
	void setStyle(eWindowStyle *style) { m_style = style; }

	void setBackgroundColor(const gRGB &col);
	void clearBackgroundColor();

	void setZPosition(int z);
	void setTransparent(int transp);

		/* untested code */
	int isVisible() { return (m_vis & wVisShow) && ((!m_parent) || m_parent->isVisible()); }
		/* ... */

	int isLowered() { return (m_lowered > 0); }

	int isTransparent() { return m_vis & wVisTransparent; }

	ePoint getAbsolutePosition();

	eWidgetAnimation m_animation;
private:
	eWidgetDesktop *m_desktop;

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
	eWidget *m_parent;

	ePtr<eWindowStyle> m_style;

	void insertIntoParent();
	void doPaint(gPainter &painter, const gRegion &region, int layer);
	void recalcClipRegionsWhenVisible();

	void parentRemoved();

	gRGB m_background_color;
	int m_have_background_color;

	eWidget *m_current_focus, *m_focus_owner;

	int m_z_position;
	int m_lowered;
	int m_notify_child_on_position_change;
protected:
	void mayKillFocus();
public:

		// all in local space!
	gRegion	m_clip_region, m_visible_region, m_visible_with_childs;
	struct eWidgetDesktopCompBuffer *m_comp_buffer[MAX_LAYER];

	enum eWidgetEvent
	{
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
	virtual int event(int event, void *data = 0, void *data2 = 0);
	void setFocus(eWidget *focus);

		/* enable this if you need the absolute position of the widget */
	void setPositionNotifyChild(int n) { m_notify_child_on_position_change = 1; }

	void notifyShowHide();
};

extern eWidgetDesktop *getDesktop(int which);

#endif
