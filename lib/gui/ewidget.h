#ifndef __lib_gui_ewidget_h
#define __lib_gui_ewidget_h

#include <lib/gdi/grc.h> /* for gRegion */
#include <lib/base/eptrlist.h> /* for eSmartPtrList */
#include <lib/gui/ewindowstyle.h> /* for eWindowStyle */

class eWindowStyle;

class eWidget
{
	friend class eWidgetDesktop;
public:
	eWidget(eWidget *parent);
	
	void move(ePoint pos);
	void resize(eSize size);
	
	ePoint position() const { return m_position; }
	eSize size() const { return m_size; }

	void invalidate(const gRegion &region = gRegion::invalidRegion());
	
		/* the window were to attach childs to. Normally, this 
		   is "this", but it can be overridden in case a widget
		   has a "client area", which is implemented as a child
		   widget. eWindow overrides this, for example. */
	virtual eWidget *child() { return this; }

	void show();
	void hide();
	
	void destruct();
	
	int getStyle(ePtr<eWindowStyle> &style) { if (!m_style) return 1; style = m_style; return 0; }
	void setStyle(eWindowStyle *style) { m_style = style; }
	
private:
	eWidgetDesktop *m_desktop;

	enum { 
		wVisShow = 1,
		wVisTransparent = 2,
	};
	
	int m_vis;	

	ePtrList<eWidget> m_childs;
	ePoint m_position;
	eSize m_size;
	eWidget *m_parent;
	
	ePtr<eWindowStyle> m_style;
	
	void doPaint(gPainter &painter, const gRegion &region);
	void recalcClipRegionsWhenVisible();
protected:
	virtual ~eWidget();
public:

		// all in local space!
	gRegion	m_clip_region, m_visible_region, m_visible_with_childs;
	
	enum eWidgetEvent
	{
		evtPaint,
		evtKey,
		evtChangedPosition,
		evtChangedSize,
		
		evtWillShow,
		evtWillHide,
		evtWillChangePosition, /* new size is eRect *data */
		evtWillChangeSize,
		
		evtUserWidget,
	};
	virtual int event(int event, void *data = 0, void *data2 = 0);
};

extern eWidgetDesktop *getDesktop();

#endif
