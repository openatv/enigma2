#ifndef __lib_gui_elistboxcontent_h
#define __lib_gui_elistboxcontent_h

#include <lib/python/python.h>
#include <lib/gui/elistbox.h>

class eListboxPythonStringContent : public virtual iListboxContent
{
	DECLARE_REF(eListboxPythonStringContent);

public:
	eListboxPythonStringContent();
	~eListboxPythonStringContent();

	void updateEntry(int index, SWIG_PYOBJECT(ePyObject) entry);
	void setList(SWIG_PYOBJECT(ePyObject) list);
	void setOrientation(uint8_t orientation);
	void setItemHeight(int height);
	void setItemWidth(int width);
	PyObject *getCurrentSelection();
	int getCurrentSelectionIndex() { return m_cursor; }
	void invalidateEntry(int index);
	void invalidate();
	eSize getItemSize() { return m_itemsize; }
	int getMaxItemTextWidth();
	uint8_t getOrientation() { return m_orientation; }
	
#ifndef SWIG
protected:
	void cursorHome();
	void cursorEnd();
	int cursorMove(int count = 1);
	int cursorValid();
	int cursorSet(int n);
	int cursorGet();
	virtual int currentCursorSelectable();

	void cursorSave();
	void cursorRestore();
	void cursorSaveLine(int n);
	int cursorRestoreLine();
	int size();

#if SIGCXX_MAJOR_VERSION == 2
	RESULT connectItemChanged(const sigc::slot0<void> &itemChanged, ePtr<eConnection> &connection);
#else
	RESULT connectItemChanged(const sigc::slot<void()> &itemChanged, ePtr<eConnection> &connection);
#endif

	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	void setSize(const eSize &size);

	/* the following functions always refer to the selected item */
	virtual void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);

	int getItemHeight() { return m_itemheight; }
	int getItemWidth() { return m_itemwidth; }

private:
	int m_saved_cursor_line;
	ePtr<gFont> m_font_zoomed;

protected:
	int m_cursor;
	int m_saved_cursor;
	ePyObject m_list;
	eSize m_itemsize;
	int m_itemheight;
	int m_itemwidth;
	int m_max_text_width;
	uint8_t m_orientation;
#endif
};

class eListboxPythonConfigContent : public eListboxPythonStringContent
{
public:
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
	void setSeperation(int sep) { m_seperation = sep; }
	int getEntryLeftOffset();
	int getHeaderLeftOffset();
	int currentCursorSelectable();
	void setSlider(int height, int space)
	{
		m_slider_height = height;
		m_slider_space = space;
	}
	eSize calculateEntryTextSize(const std::string &string, bool headerFont = true);

private:
	int m_seperation, m_slider_height, m_slider_space;
	std::map<int, int> m_text_offset;
};

class eListboxPythonMultiContent : public eListboxPythonStringContent
{
	ePyObject m_buildFunc;
	ePyObject m_selectableFunc;
	ePyObject m_template;
	eRect m_selection_clip;
	gRegion m_clip, m_old_clip;

public:
	eListboxPythonMultiContent();
	~eListboxPythonMultiContent();
	enum
	{
		TYPE_RECT,
		TYPE_TEXT,
		TYPE_PROGRESS,
		TYPE_LINEAR_GRADIENT,
		TYPE_LINEAR_GRADIENT_ALPHABLEND,
		TYPE_PIXMAP,
		TYPE_PIXMAP_ALPHATEST,
		TYPE_PIXMAP_ALPHABLEND,
		TYPE_PROGRESS_PIXMAP
	};
	void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected);
	int currentCursorSelectable();
	void setList(SWIG_PYOBJECT(ePyObject) list);
	void setFont(int fnt, gFont *font);
	void setBuildFunc(SWIG_PYOBJECT(ePyObject) func);
	void setSelectableFunc(SWIG_PYOBJECT(ePyObject) func);
	void setSelectionClip(eRect &rect, bool update = false);
	void updateClip(gRegion &);
	void resetClip();
	void entryRemoved(int idx);
	void setTemplate(SWIG_PYOBJECT(ePyObject) tmplate);
	int getMaxItemTextWidth();
protected:
	virtual void setBuildArgs(int selected) {}
	virtual bool getIsMarked(int selected) { return false; }
	bool m_servicelist = false;
	ePyObject m_pArgs;

private:
	std::map<int, ePtr<gFont>> m_fonts;
	std::map<int, ePtr<gFont>> m_fonts_zoomed;
};

#ifdef SWIG
#define RT_HALIGN_BIDI 0
#define RT_HALIGN_LEFT 1
#define RT_HALIGN_RIGHT 2
#define RT_HALIGN_CENTER 4
#define RT_HALIGN_BLOCK 8
#define RT_VALIGN_TOP 0
#define RT_VALIGN_CENTER 16
#define RT_VALIGN_BOTTOM 32
#define RT_WRAP 64
#define RT_ELLIPSIS 128
#define RT_BLEND 256
#define RT_UNDERLINE 512
#define BT_ALPHATEST 1
#define BT_ALPHABLEND 2
#define BT_SCALE 4
#define BT_KEEP_ASPECT_RATIO 8
#define BT_FIXRATIO 8
#define BT_HALIGN_LEFT 0
#define BT_HALIGN_CENTER 16
#define BT_HALIGN_RIGHT 32
#define BT_VALIGN_TOP 0
#define BT_VALIGN_CENTER 64
#define BT_VALIGN_BOTTOM 128
#define BT_ALIGN_CENTER BT_HALIGN_CENTER | BT_VALIGN_CENTER

#define GRADIENT_OFF 0
#define GRADIENT_VERTICAL 1
#define GRADIENT_HORIZONTAL 2

#define RADIUS_TOP_LEFT 1
#define RADIUS_TOP_RIGHT 2
#define RADIUS_TOP 3
#define RADIUS_BOTTOM_LEFT 4
#define RADIUS_BOTTOM_RIGHT 8
#define RADIUS_BOTTOM 12
#define RADIUS_LEFT 5
#define RADIUS_RIGHT 10
#define RADIUS_ALL RADIUS_TOP | RADIUS_BOTTOM

#endif // SWIG

#endif
