#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/actions/action.h>

eListbox::eListbox(eWidget *parent): eWidget(parent)
{
	setContent(new eListboxStringContent());

	ePtr<eActionMap> ptr;
	eActionMap::getInstance(ptr);
	
	m_itemheight = 25;
	
	ptr->bindAction("ListboxActions", 0, 0, this);
}

eListbox::~eListbox()
{
	ePtr<eActionMap> ptr;
	eActionMap::getInstance(ptr);
	ptr->unbindAction(this, 0);
}

void eListbox::setContent(iListboxContent *content)
{
	m_content = content;
	if (content)
		m_content->setListbox(this);
	entryReset();
}

void eListbox::moveSelection(int dir)
{
		/* refuse to do anything without a valid list. */
	if (!m_content)
		return;
		
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
	case pageUp:
		if (m_content->cursorGet() >= m_items_per_page)
		{
			m_content->cursorMove(-m_items_per_page);
			m_top -= m_items_per_page;
			if (m_top < 0)
				m_top = 0;
		} else
		{
			m_top = 0;
			m_content->cursorHome();
		}
		break;
	case moveTop:
		m_content->cursorHome();
		m_top = 0; /* align with top, speeds up process */
		break;

	case pageDown:
		m_content->cursorMove(m_items_per_page);
		if (m_content->cursorValid())
			break;
				/* fall through */
	case moveEnd:
			/* move to last existing one ("end" is already invalid) */
		m_content->cursorEnd(); m_content->cursorMove(-1); 
			/* current selection invisible? */
		if (m_top + m_items_per_page <= m_content->cursorGet())
		{
			m_top = m_content->cursorGet() - m_items_per_page + 1;
			if (m_top < 0)
				m_top = 0;
		}
		break;
	case justCheck:
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
	else if (m_selected != oldsel)
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
		
		if (!m_content)
			return eWidget::event(event, data, data2);
		assert(m_content);
		
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
	case evtChangedSize:
		recalcSize();
		return eWidget::event(event, data, data2);
		
	case evtAction:
		if (isVisible())
		{
			moveSelection((int)data2);
			return 1;
		}
		return 0;
	default:
		return eWidget::event(event, data, data2);
	}
}

void eListbox::recalcSize()
{
	m_content->setSize(eSize(size().width(), m_itemheight));
	m_items_per_page = size().height() / m_itemheight;
}

void eListbox::setItemHeight(int h)
{
	if (h)
		m_itemheight = h;
	else
		m_itemheight = 20;
	recalcSize();
}

void eListbox::entryAdded(int index)
{
		/* manage our local pointers. when the entry was added before the current position, we have to advance. */
		
		/* we need to check <= - when the new entry has the (old) index of the cursor, the cursor was just moved down. */
	if (index <= m_selected)
		++m_selected;
	if (index <= m_top)
		++m_top;
		
		/* we have to check wether our current cursor is gone out of the screen. */
		/* moveSelection will check for this case */
	moveSelection(justCheck);
	
		/* now, check if the new index is visible. */
	if ((m_top <= index) && (index < (m_top + m_items_per_page)))
	{
			/* todo, calc exact invalidation... */
		invalidate();
	}
}

void eListbox::entryRemoved(int index)
{
	if (index == m_selected)
		m_selected = m_content->cursorGet();

	moveSelection(justCheck);
	
	if ((m_top <= index) && (index < (m_top + m_items_per_page)))
	{
			/* todo, calc exact invalidation... */
		invalidate();
	}
}

void eListbox::entryChanged(int index)
{
	if ((m_top <= index) && (index < (m_top + m_items_per_page)))
	{
		gRegion inv = eRect(0, m_itemheight * (index-m_top), size().width(), m_itemheight);
		invalidate(inv);
	}
}

void eListbox::entryReset()
{
	if (m_content)
		m_content->cursorHome();
	m_top = 0;
	m_selected = 0;
	invalidate();
}
