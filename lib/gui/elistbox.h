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
		  
	virtual void cursorHome()=0;
	virtual void cursorEnd()=0;
	virtual int cursorMove(int count=1)=0;
	virtual int cursorValid()=0;
	virtual int cursorSet(int n)=0;
	virtual int cursorGet()=0;
	
	virtual void cursorSave()=0;
	virtual void cursorRestore()=0;
	
	virtual int size()=0;
	
	virtual RESULT connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection)=0;
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	virtual void setSize(const eSize &size)=0;
	
		/* the following functions always refer to the selected item */
	virtual void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)=0;
};

class eListbox: public eWidget
{
public:
	eListbox(eWidget *parent);
	void setContent(iListboxContent *content);
	
	void moveSelection(int how);
	enum {
		moveUp,
		moveDown,
		moveTop,
		moveEnd
	};
protected:
	int event(int event, void *data=0, void *data2=0);
	void recalcSize();
private:
	int m_top, m_selected;
	int m_itemheight;
	int m_items_per_page;
	ePtr<iListboxContent> m_content;
};

#endif
