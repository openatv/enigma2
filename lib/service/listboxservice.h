#ifndef __lib_service_listboxservice_h
#define __lib_service_listboxservice_h

#include <lib/gdi/gpixmap.h>
#include <lib/gui/elistbox.h>
#include <lib/service/iservice.h>
#include <set>

class eListboxServiceContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxServiceContent);
public:
	eListboxServiceContent();

	void addService(const eServiceReference &ref, bool beforeCurrent=false);
	void removeCurrent();
	void FillFinished();

	void setIgnoreService( const eServiceReference &service );
	void setRoot(const eServiceReference &ref, bool justSet=false);
	void getCurrent(eServiceReference &ref);
	
	int getNextBeginningWithChar(char c);
	int getPrevMarkerPos();
	int getNextMarkerPos();
	
		/* support for marked services */
	void initMarked();
	void addMarked(const eServiceReference &ref);
	void removeMarked(const eServiceReference &ref);
	int isMarked(const eServiceReference &ref);

		/* this is NOT thread safe! */
	void markedQueryStart();
	int markedQueryNext(eServiceReference &ref);

	int lookupService(const eServiceReference &ref);
	void setCurrent(const eServiceReference &ref);

	enum {
		visModeSimple,
		visModeComplex
	};
	
	void setVisualMode(int mode);
	
		/* only in complex mode: */
	enum {
		celServiceNumber,
		celMarkerPixmap,
		celFolderPixmap,
		celServiceEventProgressbar,
		celServiceName,
		celServiceTypePixmap,
		celServiceInfo, // "now" event
		celElements
	};

	enum {
		picDVB_S,
		picDVB_T,
		picDVB_C,
		picServiceGroup,
		picFolder,
		picMarker,
		picServiceEventProgressbar,
		picElements
	};

	void setElementPosition(int element, eRect where);
	void setElementFont(int element, gFont *font);
	void setPixmap(int type, ePtr<gPixmap> &pic);
	
	void sort();

	int setCurrentMarked(bool);

	void setNumberOffset(int offset) { m_numberoffset = offset; }
	
	int getItemHeight() { return m_itemheight; }
	void setItemHeight(int height);

	enum {
		markedForeground,
		markedForegroundSelected,
		markedBackground,
		markedBackgroundSelected,
		serviceNotAvail,
		eventForeground,
		eventForegroundSelected,
		eventborderForeground,
		eventborderForegroundSelected,
		serviceEventProgressbarColor,
		serviceEventProgressbarColorSelected,
		serviceEventProgressbarBorderColor,
		serviceEventProgressbarBorderColorSelected,
		colorElements
	};
	
	void setColor(int color, gRGB &col);
protected:
	void cursorHome();
	void cursorEnd();
	int cursorMove(int count=1);
	int cursorValid();
	int cursorSet(int n);
	int cursorGet();
	int currentCursorSelectable();

	void cursorSave();
	void cursorRestore();
	int size();
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);
	
		/* the following functions always refer to the selected item */
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
	
	int m_visual_mode;
		/* for complex mode */
	eRect m_element_position[celElements];
	ePtr<gFont> m_element_font[celElements];
	ePtr<gPixmap> m_pixmaps[picElements];
	gRGB m_color[colorElements];
	bool m_color_set[colorElements];
private:
	typedef std::list<eServiceReference> list;
	
	list m_list;
	list::iterator m_cursor, m_saved_cursor;
	
	int m_cursor_number, m_saved_cursor_number;
	int m_size;
	
	eSize m_itemsize;
	ePtr<iServiceHandler> m_service_center;
	ePtr<iListableService> m_lst;
	
	eServiceReference m_root;

		/* support for marked services */
	std::set<eServiceReference> m_marked;
	std::set<eServiceReference>::const_iterator m_marked_iterator;

		/* support for movemode */
	bool m_current_marked;

	int m_numberoffset;

	eServiceReference m_is_playable_ignore;

	int m_itemheight;
};

#endif
