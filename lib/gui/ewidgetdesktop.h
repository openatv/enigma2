#ifndef __lib_gui_ewidgetdesktop_h
#define __lib_gui_ewidgetdesktop_h

#include <lib/gdi/grc.h>
#include <lib/base/eptrlist.h>

class eWidget;

class eWidgetDesktop
{
public: // weil debug
	eSize m_screen_size;
	gRegion m_dirty_region;
	ePtr<gDC> m_dc;
public:
	eWidgetDesktop(eSize screen);
	~eWidgetDesktop();
	void addRootWidget(eWidget *root, int top);
	void recalcClipRegions();
	
	void invalidate(const gRegion &region);
	void paint();
	void setDC(gDC *dc);
private:
	ePtrList<eWidget> m_root;
	void calcWidgetClipRegion(eWidget *widget, gRegion &parent_visible);
};

#endif
