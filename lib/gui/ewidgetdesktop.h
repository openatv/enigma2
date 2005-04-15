#ifndef __lib_gui_ewidgetdesktop_h
#define __lib_gui_ewidgetdesktop_h

#include <lib/gdi/grc.h>
#include <lib/base/eptrlist.h>

class eWidget;
class eMainloop;
class eTimer;

class eWidgetDesktop: public Object
{
public: // weil debug
	eSize m_screen_size;
	gRegion m_dirty_region;
	gRegion m_background_region;
	ePtr<gDC> m_dc;
	gColor m_background_color;
public:
	eWidgetDesktop(eSize screen);
	~eWidgetDesktop();
	void addRootWidget(eWidget *root, int top);
	void removeRootWidget(eWidget *root);
	void recalcClipRegions();
	
	void invalidate(const gRegion &region);
	void paint();
	void setDC(gDC *dc);
	
	void setBackgroundColor(gColor col);
	
	void setRedrawTask(eMainloop &ml);
	
	void makeCompatiblePixmap(gPixmap &pm);
private:
	ePtrList<eWidget> m_root;
	void calcWidgetClipRegion(eWidget *widget, gRegion &parent_visible);
	
	eMainloop *m_mainloop;
	eTimer *m_timer;
};

#endif
