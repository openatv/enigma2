#ifndef __lib_components_listboxepg_h
#define __lib_components_listboxepg_h

#include <lib/gui/elistbox.h>
#include <lib/service/iservice.h>

#include <set>

class eListboxEPGContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxEPGContent);
public:
	eListboxEPGContent();
	void setRoot(const eServiceReference &ref);
	void getCurrent(ePtr<eServiceEvent>&);

		/* only in complex mode: */
	enum {
		celBeginTime,
		celTitle,
		celElements
	};

	void setElementPosition(int element, eRect where);
	void setElementFont(int element, gFont *font);

	void sort();

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

	eRect m_element_position[celElements];
	ePtr<gFont> m_element_font[celElements];
private:
	typedef std::list<ePtr<eServiceEvent> > list;

	list m_list;
	list::iterator m_cursor, m_saved_cursor;

	int m_cursor_number, m_saved_cursor_number;
	int m_size;

	eSize m_itemsize;

	eServiceReference m_root;
};

#endif
