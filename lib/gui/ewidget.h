#ifndef __lib_gui_ewidget_h
#define __lib_gui_ewidget_h

#include <lib/gdi/grc.h> /* for gRegion */
#include <lib/base/eptrlist.h> /* for eSmartPtrList */

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

	void show();
	void hide();
	
	void destruct();
private:
	eWidgetDesktop *m_desktop;

	enum { 
		wVisShow = 1,
		wVisTransparent = 2,
	};
	
	int m_vis;	

	ePtrList<eWidget> m_childs;
	eWidget *m_parent;
	ePoint m_position;
	eSize m_size;
	
	
	void doPaint(gPainter &painter, const gRegion &region);
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

#endif
