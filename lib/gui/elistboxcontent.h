#ifndef __lib_gui_elistboxcontent_h
#define __lib_gui_elistboxcontent_h

#include <lib/python/python.h>
#include <lib/gui/elistbox.h>

class eListboxPythonStringContent: public virtual iListboxContent
{
	DECLARE_REF(eListboxPythonStringContent);
public:
	eListboxPythonStringContent();
	~eListboxPythonStringContent();

	void setList(SWIG_PYOBJECT(ePyObject) list);
	PyObject *getCurrentSelection();
	int getCurrentSelectionIndex() { return m_cursor; }
	void invalidateEntry(int index);
	void invalidate();
	eSize getItemSize() { return m_itemsize; }
#ifndef SWIG
protected:
	void cursorHome();
	void cursorEnd();
	int cursorMove(int count=1);
	int cursorValid();
	int cursorSet(int n);
	int cursorGet();
	virtual int currentCursorSelectable();
		
	void cursorSave();
	void cursorRestore();
	int size();
	
	RESULT connectItemChanged(const Slot0<void> &itemChanged, ePtr<eConnection> &connection);
	
	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);
	
		/* the following functions always refer to the selected item */
	virtual void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
	
	int getItemHeight() { return m_itemheight; }

protected:
	ePyObject m_list;
	int m_cursor, m_saved_cursor;
	eSize m_itemsize;
	int m_itemheight;
#endif
};

class eListboxPythonConfigContent: public eListboxPythonStringContent
{
public:
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
	void setSeperation(int sep) { m_seperation = sep; }
	int currentCursorSelectable();
private:
	int m_seperation;
};

class eListboxPythonMultiContent: public eListboxPythonStringContent
{
	ePyObject m_buildFunc;
	ePyObject m_selectableFunc;
	ePyObject m_template;
	eRect m_selection_clip;
	gRegion m_clip, m_old_clip;
public:
	eListboxPythonMultiContent();
	~eListboxPythonMultiContent();
	enum { TYPE_TEXT, TYPE_PROGRESS, TYPE_PIXMAP, TYPE_PIXMAP_ALPHATEST, TYPE_PIXMAP_ALPHABLEND, TYPE_PROGRESS_PIXMAP };
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
	int currentCursorSelectable();
	void setList(SWIG_PYOBJECT(ePyObject) list);
	void setFont(int fnt, gFont *font);
	void setBuildFunc(SWIG_PYOBJECT(ePyObject) func);
	void setSelectableFunc(SWIG_PYOBJECT(ePyObject) func);
	void setItemHeight(int height);
	void setSelectionClip(eRect &rect, bool update=false);
	void updateClip(gRegion &);
	void entryRemoved(int idx);
	void setTemplate(SWIG_PYOBJECT(ePyObject) tmplate);
private:
	std::map<int, ePtr<gFont> > m_font;
};

#ifdef SWIG
#define RT_HALIGN_LEFT 0
#define RT_HALIGN_RIGHT 1
#define RT_HALIGN_CENTER 2
#define RT_HALIGN_BLOCK 4
#define RT_VALIGN_TOP 0
#define RT_VALIGN_CENTER 8
#define RT_VALIGN_BOTTOM 16
#define RT_WRAP 32
#endif // SWIG

#endif
