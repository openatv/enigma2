#ifndef __lib_service_listboxservice_h
#define __lib_service_listboxservice_h

#include <lib/gui/elistbox.h>
#include <lib/service/iservice.h>

class eServiceCenter;

class eListboxServiceContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxServiceContent);
public:
	eListboxServiceContent();
	void setRoot(const eServiceReference &ref);
	void getCurrent(eServiceReference &ref);

protected:
	void cursorHome();
	void cursorEnd();
	int cursorMove(int count=1);
	int cursorValid();
	int cursorSet(int n);
	int cursorGet();
	
	void cursorSave();
	void cursorRestore();
	int size();
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);
	
		/* the following functions always refer to the selected item */
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
private:
	typedef std::list<eServiceReference> list;
	
	list m_list;
	list::iterator m_cursor, m_saved_cursor;
	
	int m_cursor_number, m_saved_cursor_number;
	int m_size;
	
	eSize m_itemsize;
	ePtr<eServiceCenter> m_service_center;
	
	eServiceReference m_root;
};

#endif
