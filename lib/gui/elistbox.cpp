#include <lib/gui/elistbox.h>

/*
    The basic idea is to have an interface which gives all relevant list
    processing functions, and can be used by the listbox to browse trough
    the list.
    
    The listbox directly uses the implemented cursor. It tries hard to avoid
    iterating trough the (possibly very large) list, so it should be O(1),
    i.e. the performance should not be influenced by the size of the list.
    
    The list interface knows how to draw the current entry to a specified 
    offset. Different interfaces can be used to adapt different lists,
    pre-filter lists on the fly etc.
    
		cursorSave/Restore is used to avoid re-iterating the list on redraw.
		The current selection is always selected as cursor position, the
    cursor is then positioned to the start, and then iterated. This gives
    at most 2x m_items_per_page cursor movements per redraw, indepenent
    of the size of the list.
    
    Although cursorSet is provided, it should be only used when there is no
    other way, as it involves iterating trough the list.
 */

class eListboxTestContent: public virtual iListboxContent
{
	DECLARE_REF;
public:
	void cursorHome();
	void cursorEnd();
	int cursorMove(int count=1);
	int cursorValid();
	int cursorSet(int n);
	int cursorGet();
	
	void cursorSave();
	void cursorRestore();
	int size();
	
	RESULT connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection);
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);
	
		/* the following functions always refer to the selected item */
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
private:
	int m_cursor, m_saved_cursor;
	eSize m_size;
};

DEFINE_REF(eListboxTestContent);

void eListboxTestContent::cursorHome()
{
	m_cursor = 0;
}

void eListboxTestContent::cursorEnd()
{
	m_cursor = size();
}

int eListboxTestContent::cursorMove(int count)
{
	m_cursor += count;
	
	if (m_cursor < 0)
		cursorHome();
	else if (m_cursor > size())
		cursorEnd();
	return 0;
}

int eListboxTestContent::cursorValid()
{
	return m_cursor < size();
}

int eListboxTestContent::cursorSet(int n)
{
	m_cursor = n;
	
	if (m_cursor < 0)
		cursorHome();
	else if (m_cursor > size())
		cursorEnd();
	return 0;
}

int eListboxTestContent::cursorGet()
{
	return m_cursor;
}

void eListboxTestContent::cursorSave()
{
	m_saved_cursor = m_cursor;
}

void eListboxTestContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
}

int eListboxTestContent::size()
{
	return 10;
}
	
RESULT eListboxTestContent::connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection)
{
	return 0;
}

void eListboxTestContent::setSize(const eSize &size)
{
	m_size = size;
}

void eListboxTestContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt = new gFont("Arial", 14);
	painter.clip(eRect(offset, m_size));
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	painter.clear();

	if (cursorValid())
	{
		painter.setFont(fnt);
		char string[10];
		sprintf(string, "%d.)", m_cursor);
		
		ePoint text_offset = offset + (selected ? ePoint(2, 2) : ePoint(1, 1));
		
		painter.renderText(eRect(text_offset, m_size), string);
		
		if (selected)
			style.drawFrame(painter, eRect(offset, m_size), eWindowStyle::frameListboxEntry);
	}
	
	painter.clippop();
}

eListbox::eListbox(eWidget *parent): eWidget(parent)
{
	setContent(new eListboxTestContent());
	m_content->cursorHome();
	m_top = 0;
	m_selected = 0;
}

void eListbox::setContent(iListboxContent *content)
{
	m_content = content;
}

void eListbox::moveSelection(int dir)
{
		/* we need the old top/sel to see what we have to redraw */
	int oldtop = m_top;
	int oldsel = m_selected;
	
		/* first, move cursor */
	switch (dir)
	{
	case moveUp:
		m_content->cursorMove(-1);
		break;
	case moveDown:
		m_content->cursorMove(1);
			/* ok - we could have reached the end. we just go one back then. */
		if (!m_content->cursorValid())
			m_content->cursorMove(-1);
		break;
	case moveTop:
		m_content->cursorHome();
		m_top = 0; /* align with top, speeds up process */
		break;
	case moveEnd:
			/* move to last existing one ("end" is already invalid) */
		m_content->cursorEnd(); m_content->cursorMove(-1); 
		
		m_top = m_content->cursorGet() - m_items_per_page + 1;
		if (m_top < 0)
			m_top = 0;
		break;
	}
	
		/* note that we could be on an invalid cursor position, but we don't
		   care. this only happens on empty lists, and should have almost no
		   side effects. */
	
		/* now, look wether the current selection is out of screen */
	m_selected = m_content->cursorGet();
	if (m_selected < m_top)
	{
		m_top -= m_items_per_page;
		if (m_top < 0)
			m_top = 0;
	} else if (m_selected >= m_top + m_items_per_page)
	{
			/* m_top should be always valid here as it's selected */
		m_top += m_items_per_page;
	}
	
	if (m_top != oldtop)
		invalidate();
	else
	{
			/* redraw the old and newly selected */
		gRegion inv = eRect(0, m_itemheight * (m_selected-m_top), size().width(), m_itemheight);
		inv |= eRect(0, m_itemheight * (oldsel-m_top), size().width(), m_itemheight);
		
		invalidate(inv);
	}
}

int eListbox::event(int event, void *data, void *data2)
{
	switch (event)
	{
	case evtPaint:
	{
		ePtr<eWindowStyle> style;
		
		assert(m_content);
		recalcSize(); // move to event
		
		getStyle(style);
		
		if (!m_content)
			return 0;
		
		gPainter &painter = *(gPainter*)data2;
		
		m_content->cursorSave();
		m_content->cursorMove(m_top - m_selected);
		
		for (int y = 0, i = 0; i < m_items_per_page; y += m_itemheight, ++i)
		{
			m_content->paint(painter, *style, ePoint(0, y), m_selected == m_content->cursorGet());
			m_content->cursorMove(+1);
		}
		
		m_content->cursorRestore();
		
		return 0;
	}
	default:
		return eWidget::event(event, data, data2);
	}
}

void eListbox::recalcSize()
{
	m_itemheight = 20;
	m_content->setSize(eSize(size().width(), m_itemheight));
	m_items_per_page = size().height() / m_itemheight;
}
