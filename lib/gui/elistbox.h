#ifndef __lib_listbox_h
#define __lib_listbox_h

#include <lib/gui/ewidget.h>
#include <connection.h>

class iListboxContent: public iObject
{
public:
	virtual ~iListboxContent()=0;
	
		/* indices go from 0 to size().
		   the end is reached when the cursor is on size(), 
		   i.e. one after the last entry (this mimics 
		   stl behaviour)
		   
		   cursors never invalidate - they can become invalid
		   when stuff is removed. Cursors will always try
		   to stay on the same data, however when the current
		   item is removed, this won't work. you'll be notified
		   anyway. */
#ifndef SWIG	
protected:
	iListboxContent();
	friend class eListbox;
	virtual void cursorHome()=0;
	virtual void cursorEnd()=0;
	virtual int cursorMove(int count=1)=0;
	virtual int cursorValid()=0;
	virtual int cursorSet(int n)=0;
	virtual int cursorGet()=0;
	
	virtual void cursorSave()=0;
	virtual void cursorRestore()=0;
	
	virtual int size()=0;
	
	void setListbox(eListbox *lb);
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	virtual void setSize(const eSize &size)=0;
	
		/* the following functions always refer to the selected item */
	virtual void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)=0;
	
	eListbox *m_listbox;
#endif
};

class eListbox: public eWidget
{
public:
	eListbox(eWidget *parent);
	~eListbox();
	void setContent(iListboxContent *content);
	
/*	enum Movement {
		moveUp,
		moveDown,
		moveTop,
		moveEnd,
		justCheck
	}; */
	
	void moveSelection(int how);

	enum ListboxActions {
		moveUp,
		moveDown,
		moveTop,
		moveEnd,
		pageUp,
		pageDown,
		justCheck
	};
	
	void setItemHeight(int h);

#ifndef SWIG
		/* entryAdded: an entry was added *before* the given index. it's index is the given number. */
	void entryAdded(int index);
		/* entryRemoved: an entry with the given index was removed. */
	void entryRemoved(int index);
		/* entryChanged: the entry with the given index was changed and should be redrawn. */
	void entryChanged(int index);
		/* the complete list changed. you should not attemp to keep the current index. */
	void entryReset();

protected:
	int event(int event, void *data=0, void *data2=0);
	void recalcSize();
	
private:
	int m_top, m_selected;
	int m_itemheight;
	int m_items_per_page;
	ePtr<iListboxContent> m_content;
#endif

};

#endif
