#ifndef __lib_gui_ewidgetdesktop_h
#define __lib_gui_ewidgetdesktop_h

#include <lib/gdi/grc.h>
#include <lib/base/eptrlist.h>

class eWidget;
class eMainloop;
class eTimer;

		/* an eWidgetDesktopCompBuffer is a composition buffer. in
		   immediate composition  mode, we only have one composition
		   buffer - the screen.
		   in buffered mode, we have one buffer for each widget, plus
		   the screen.

		   even in buffered mode, we have a background region, because
		   a window can be arbitrary shaped. the screen size acts as a bounding
		   box in these cases. */

struct eWidgetDesktopCompBuffer
{
	ePoint m_position;
	eSize m_screen_size;
	gRegion m_dirty_region;
	gRegion m_background_region;
	ePtr<gDC> m_dc;
	gRGB m_background_color;
};

class eWidgetDesktop: public Object
{
public:
	eWidgetDesktop(eSize screen);
	~eWidgetDesktop();
	void addRootWidget(eWidget *root);
	void removeRootWidget(eWidget *root);

		/* try to move widget content. */
		/* returns -1 if there's no move support. */
		/* call this after recalcClipRegions for that widget. */
		/* you probably want to invalidate if -1 was returned. */
	int movedWidget(eWidget *root);

	void recalcClipRegions(eWidget *root);

	void invalidateWidgetLayer(const gRegion &region, const eWidget *widget, int layer);
	void invalidateWidget(const gRegion &region, const eWidget *widget, int layer = -1);
	void invalidate(const gRegion &region, const eWidget *widget = 0, int layer = -1);
	void paintLayer(eWidget *widget, int layer);
	void paint();
	void setDC(gDC *dc);

	void setBackgroundColor(gRGB col);
	void setBackgroundColor(eWidgetDesktopCompBuffer *comp, gRGB col);

	void setPalette(gPixmap &pm);

	void setRedrawTask(eMainloop &ml);

	void makeCompatiblePixmap(ePtr<gPixmap> &pm);
	void makeCompatiblePixmap(gPixmap &pm);

	enum {
		cmImmediate,
		cmBuffered
	};

	void setCompositionMode(int mode);

	int getStyleID() { return m_style_id; }
	void setStyleID(int id) { m_style_id = id; }

	void resize(eSize size);
	eSize size() const { return m_screen.m_screen_size; }
	void sendShow(ePoint point, eSize size);
	void sendHide(ePoint point, eSize size);
	eRect bounds() const; // returns area inside margins
	eRect margins() const { return m_margins; }
	void setMargins(const eRect& value) { m_margins = value; }
private:
	ePtrList<eWidget> m_root;
	void calcWidgetClipRegion(eWidget *widget, gRegion &parent_visible);
	void paintBackground(eWidgetDesktopCompBuffer *comp);

	eMainloop *m_mainloop;
	ePtr<eTimer> m_timer;

	int m_comp_mode;
	int m_require_redraw;

	eWidgetDesktopCompBuffer m_screen;

	void createBufferForWidget(eWidget *widget, int layer);
	void removeBufferForWidget(eWidget *widget, int layer);

	void redrawComposition(int notifed);
	void notify();

	void clearVisibility(eWidget *widget);

	int m_style_id;
	eRect m_margins;
};

#endif
