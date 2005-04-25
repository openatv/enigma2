#ifndef __lib_gui_elistboxcontent_h
#define __lib_gui_elistboxcontent_h

#include <lib/python/python.h>
#include <lib/gui/elistbox.h>

class eListboxTestContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxTestContent);
public:

#ifndef SWIG
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
	
	RESULT connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection);
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);
	
		/* the following functions always refer to the selected item */
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
private:
	int m_cursor, m_saved_cursor;
	eSize m_size;
#endif
};

class eListboxStringContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxStringContent);
public:
	eListboxStringContent();
	void setList(std::list<std::string> &list);
#ifndef SWI
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
	typedef std::list<std::string> list;
	
	list m_list;
	list::iterator m_cursor, m_saved_cursor;
	
	int m_cursor_number, m_saved_cursor_number;
	int m_size;
	
	eSize m_itemsize;
#endif
};

class eListboxPythonStringContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxPythonStringContent);
public:
	eListboxPythonStringContent();
	~eListboxPythonStringContent();

	void setList(PyObject *list);
	PyObject *getCurrentSelection();
	int getCurrentSelectionIndex() { return m_cursor; }
#ifndef SWIG
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
	
	RESULT connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection);
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);
	
		/* the following functions always refer to the selected item */
	virtual void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);

protected:
	PyObject *m_list;
	int m_cursor, m_saved_cursor;
	eSize m_itemsize;
#endif
};

class eListboxPythonConfigContent: public eListboxPythonStringContent
{
public:
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
	void invalidateEntry(int index);
	void setSeperation(int sep) { m_seperation = sep; }
private:
	int m_seperation;
};

#endif
