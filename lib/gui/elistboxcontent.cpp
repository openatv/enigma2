#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <Python.h>

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

iListboxContent::~iListboxContent()
{
}


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

//////////////////////////////////////

DEFINE_REF(eListboxStringContent);

eListboxStringContent::eListboxStringContent()
{
	m_size = 0;
	cursorHome();
}

void eListboxStringContent::cursorHome()
{
	m_cursor = m_list.begin();
	m_cursor_number = 0;
}

void eListboxStringContent::cursorEnd()
{
	m_cursor = m_list.end();
	m_cursor_number = m_size;
}

int eListboxStringContent::cursorMove(int count)
{
	if (count > 0)
	{
		while (count && (m_cursor != m_list.end()))
		{
			++m_cursor;
			++m_cursor_number;
			--count;
		}
	} else if (count < 0)
	{
		while (count && (m_cursor != m_list.begin()))
		{
			--m_cursor;
			--m_cursor_number;
			++count;
		}
	}
	
	return 0;
}

int eListboxStringContent::cursorValid()
{
	return m_cursor != m_list.end();
}

int eListboxStringContent::cursorSet(int n)
{
	cursorHome();
	cursorMove(n);
	
	return 0;
}

int eListboxStringContent::cursorGet()
{
	return m_cursor_number;
}

void eListboxStringContent::cursorSave()
{
	m_saved_cursor = m_cursor;
	m_saved_cursor_number = m_cursor_number;
}

void eListboxStringContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
	m_cursor_number = m_saved_cursor_number;
}

int eListboxStringContent::size()
{
	return m_size;
}
	
RESULT eListboxStringContent::connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection)
{
	return 0;
}

void eListboxStringContent::setSize(const eSize &size)
{
	m_itemsize = size;
}

void eListboxStringContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt = new gFont("Arial", 14);
	painter.clip(eRect(offset, m_itemsize));
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	painter.clear();
	
	eDebug("item %d", m_cursor_number);
	if (cursorValid())
	{
		eDebug("is valid..");
		painter.setFont(fnt);
		
		ePoint text_offset = offset + (selected ? ePoint(2, 2) : ePoint(1, 1));
		
		painter.renderText(eRect(text_offset, m_itemsize), *m_cursor);
		
		if (selected)
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
	}
	
	painter.clippop();
}

void eListboxStringContent::setList(std::list<std::string> &list)
{
	m_list = list;
	m_size = list.size();
	cursorHome();
}

//////////////////////////////////////

DEFINE_REF(eListboxPythonStringContent);

eListboxPythonStringContent::eListboxPythonStringContent()
{
	m_list = 0;
}

eListboxPythonStringContent::~eListboxPythonStringContent()
{
}

void eListboxPythonStringContent::cursorHome()
{
	m_cursor = 0;
}

void eListboxPythonStringContent::cursorEnd()
{
	m_cursor = size();
}

int eListboxPythonStringContent::cursorMove(int count)
{
	m_cursor += count;
	
	if (m_cursor < 0)
		cursorHome();
	else if (m_cursor > size())
		cursorEnd();
	return 0;
}

int eListboxPythonStringContent::cursorValid()
{
	return m_cursor < size();
}

int eListboxPythonStringContent::cursorSet(int n)
{
	m_cursor = n;
	
	if (m_cursor < 0)
		cursorHome();
	else if (m_cursor > size())
		cursorEnd();
	return 0;
}

int eListboxPythonStringContent::cursorGet()
{
	return m_cursor;
}

void eListboxPythonStringContent::cursorSave()
{
	m_saved_cursor = m_cursor;
}

void eListboxPythonStringContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
}

int eListboxPythonStringContent::size()
{
	if (!m_list)
		return 0;
	return PyList_Size(m_list);
}
	
RESULT eListboxPythonStringContent::connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection)
{
	return 0;
}

void eListboxPythonStringContent::setSize(const eSize &size)
{
	m_itemsize = size;
}

void eListboxPythonStringContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt = new gFont("Arial", 14);
	painter.clip(eRect(offset, m_itemsize));
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	painter.clear();

	if (m_list && cursorValid())
	{
		PyObject *item = PyList_GetItem(m_list, m_cursor); // borrowed reference!
		painter.setFont(fnt);

			/* the user can supply tuples, in this case the first one will be displayed. */		
		if (PyTuple_Check(item))
			item = PyTuple_GetItem(item, 0);
		
		const char *string = PyString_Check(item) ? PyString_AsString(item) : "<not-a-string>";
		
		ePoint text_offset = offset + (selected ? ePoint(2, 2) : ePoint(1, 1));
		
		painter.renderText(eRect(text_offset, m_itemsize), string);
		
		if (selected)
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
	}
	
	painter.clippop();
}

void eListboxPythonStringContent::setList(PyObject *list)
{
	Py_XDECREF(m_list);
	if (!PyList_Check(list))
	{
		m_list = 0;
	} else
	{
		m_list = list;
		Py_INCREF(m_list);
	}
}

PyObject *eListboxPythonStringContent::getCurrentSelection()
{
	if (!m_list)
		return 0;
	if (!cursorValid())
		return 0;
	PyObject *r = PyList_GetItem(m_list, m_cursor);
	Py_XINCREF(r);
	return r;
}

//////////////////////////////////////
