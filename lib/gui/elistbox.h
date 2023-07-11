#ifndef __lib_listbox_h
#define __lib_listbox_h

#include <lib/gui/ewidget.h>
#include <connection.h>

class eListbox;
class eSlider;

class iListboxContent : public iObject
{
public:
	virtual ~iListboxContent() = 0;

	/* indices go from 0 to size().
	   the end is reached when the cursor is on size(),
	   i.e. one after the last entry (this mimics
	   stl behavior)

	   cursors never invalidate - they can become invalid
	   when stuff is removed. Cursors will always try
	   to stay on the same data, however when the current
	   item is removed, this won't work. you'll be notified
	   anyway. */
#ifndef SWIG
protected:
	iListboxContent();
	friend class eListbox;
	virtual void updateClip(gRegion &){};
	virtual void resetClip(){};
	virtual void cursorHome() = 0;
	virtual void cursorEnd() = 0;
	virtual int cursorMove(int count = 1) = 0;
	virtual int cursorValid() = 0;
	virtual int cursorSet(int n) = 0;
	virtual int cursorGet() = 0;

	virtual void cursorSave() = 0;
	virtual void cursorRestore() = 0;
	virtual void cursorSaveLine(int n) = 0;
	virtual int cursorRestoreLine() = 0;

	virtual int size() = 0;

	virtual int currentCursorSelectable();

	void setListbox(eListbox *lb);

	// void setOutputDevice ? (for allocating colors, ...) .. requires some work, though
	virtual void setSize(const eSize &size) = 0;

	/* the following functions always refer to the selected item */
	virtual void paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected) = 0;

	virtual int getItemHeight() = 0;
	virtual int getItemWidth() { return -1; }
	virtual int getOrientation() { return 1; }

	eListbox *m_listbox;
#endif
};

#ifndef SWIG
struct eListboxStyleSetted
{
	bool transparent_background : 1;
	bool border : 1;
	bool background_color : 1;
	bool foreground_color : 1;
	bool background_color_selected : 1;
	bool foreground_color_selected : 1;
	bool scrollbarforeground_color : 1;
	bool scrollbarbackground_color : 1;
	bool scollbarborder_color : 1;
	bool scrollbarborder_width : 1;
	bool spacing_color : 1;
	bool overlay : 1;
	bool max_rows : 1;
	bool max_columns : 1;
	bool use_vti_workaround : 1;
};

struct eListboxStyle
{
	ePtr<gPixmap> m_background, m_selection, m_overlay;
	gRGB m_background_color, m_background_color_selected, m_foreground_color, m_foreground_color_selected, m_border_color, m_scollbarborder_color, m_scrollbarforeground_color, m_scrollbarbackground_color, m_spacing_color;
	int m_max_columns;
	int m_max_rows;
	float m_selection_zoom;

	eListboxStyleSetted is_set;

	/*
		{transparent_background background_color background}
		{0 0 0} use global background color
		{0 1 x} use background color
		{0 0 p} use background picture
		{1 x 0} use transparent background
		{1 x p} use transparent background picture
	*/

	enum
	{
		alignLeft,
		alignTop = alignLeft,
		alignCenter,
		alignRight,
		alignBottom = alignRight,
		alignBlock
	};
	int m_valign, m_halign, m_border_size, m_scrollbarborder_width;
	ePtr<gFont> m_font, m_font_zoomed, m_valuefont;
	eRect m_text_padding;
};
#endif

class eListbox : public eWidget
{
	void updateScrollBar();

public:
	eListbox(eWidget *parent);
	~eListbox();

	PSignal0<void> selectionChanged;

	enum
	{
		showOnDemand,
		showAlways,
		showNever,
		showLeftOnDemand,
		showLeftAlways,
		showTopOnDemand,
		showTopAlways
	};

	enum
	{
		byPage,
		byLine
	};

	enum
	{
		DefaultScrollBarWidth = 10,
		DefaultScrollBarOffset = 5,
		DefaultScrollBarBorderWidth = 1,
		DefaultScrollBarScroll = eListbox::byPage,
		DefaultScrollBarMode = eListbox::showNever,
		DefaultWrapAround = true,
		DefaultPageSize = 0
	};
	enum
	{
		orVertical = 1,
		orHorizontal = 2,
		orGrid = 3
	};

	enum
	{
		itemVertialAlignTop = 1 << 0,
		itemVertialAlignMiddle = 1 << 1,
		itemVertialAlignBottom = 1 << 2,
		itemVertialAlignJustify = 1 << 3,
		itemHorizontalAlignLeft = 1 << 4,
		itemHorizontalAlignCenter = 1 << 5,
		itemHorizontalAlignRight = 1 << 6,
		itemHorizontalAlignJustify = 1 << 7,
	};

	enum
	{
		itemAlignLeftTop = itemVertialAlignTop + itemHorizontalAlignLeft,
		itemAlignLeftMiddle = itemVertialAlignMiddle + itemHorizontalAlignLeft,
		itemAlignLeftBottom = itemVertialAlignBottom + itemHorizontalAlignLeft,
		itemAlignRightTop = itemVertialAlignTop + itemHorizontalAlignRight,
		itemAlignRightMiddle = itemVertialAlignMiddle + itemHorizontalAlignRight,
		itemAlignRightBottom = itemVertialAlignBottom + itemHorizontalAlignRight,
		itemAlignCenterTop = itemVertialAlignTop + itemHorizontalAlignCenter,
		itemAlignCenterMiddle = itemVertialAlignMiddle + itemHorizontalAlignCenter,
		itemAlignCenterBottom = itemVertialAlignBottom + itemHorizontalAlignCenter,
		itemAlignJustifyTop = itemVertialAlignTop + itemHorizontalAlignJustify,
		itemAlignJustifyMiddle = itemVertialAlignMiddle + itemHorizontalAlignJustify,
		itemAlignJustifyBottom = itemVertialAlignBottom + itemHorizontalAlignJustify,
		itemAlignJustifyLeft = itemVertialAlignJustify + itemHorizontalAlignLeft,
		itemAlignJustifyRight = itemVertialAlignJustify + itemHorizontalAlignRight,
		itemAlignJustifyFull =  itemVertialAlignJustify + itemHorizontalAlignJustify,

		itemAlignDefault = itemAlignLeftTop,
		itemAlignCenter = itemAlignCenterMiddle,
		itemAlignJustify = itemAlignJustifyFull
	};

	void setItemAlignment(int align);
	void setScrollbarScroll(int scroll);
	void setScrollbarMode(int mode);
	void setWrapAround(bool state) { m_enabled_wrap_around = state; }

	void setOrientation(int orientation);
	void setContent(iListboxContent *content);

	void allowNativeKeys(bool allow);
	void enableAutoNavigation(bool allow) { allowNativeKeys(allow); }

	int getCurrentIndex();
	void moveSelection(int how);
	void moveSelectionTo(int index);
	void moveToEnd(); // Deprecated
	bool atBegin();
	bool atEnd();

	void goTop() { moveSelection(moveTop); }
	void goBottom() { moveSelection(moveBottom); }
	void goLineUp() { moveSelection(moveUp); }
	void goLineDown() { moveSelection(moveDown); }
	void goPageUp() { moveSelection(movePageUp); }
	void goPageDown() { moveSelection(movePageDown); }
	void goLeft() { moveSelection(moveLeft); }
	void goRight() { moveSelection(moveRight); }

	// for future use
	void goPageLeft() { moveSelection(movePageLeft); }
	void goPageRight() { moveSelection(movePageRight); }
	void goFirst() { moveSelection(moveFirst); }
	void goLast() { moveSelection(moveLast); }

	enum ListboxActions
	{
		moveUp,
		moveDown,
		moveTop,
		moveBottom,
		movePageUp,
		movePageDown,
		justCheck,
		refresh,
		moveLeft,
		moveRight,
		moveFirst,				// for future use
		moveLast,				// for future use
		movePageLeft,			// for future use
		movePageRight,			// for future use
		moveEnd = moveBottom,	// deprecated
		pageUp = movePageUp,	// deprecated
		pageDown = movePageDown // deprecated
	};

	void setItemHeight(int h);
	void setItemWidth(int w);
	void setSelectionEnable(int en);

	void setBackgroundColor(gRGB &col);
	void setBackgroundColorSelected(gRGB &col);
	void setForegroundColor(gRGB &col);
	void setForegroundColorSelected(gRGB &col);

	void setSpacingColor(gRGB &col);
	void clearSpacingColor() { m_style.is_set.spacing_color = 0; }

	void clearBackgroundColor() { m_style.is_set.background_color = 0; }
	void clearBackgroundColorSelected() { m_style.is_set.background_color_selected = 0; }
	void clearForegroundColor() { m_style.is_set.foreground_color = 0; }
	void clearForegroundColorSelected() { m_style.is_set.foreground_color_selected = 0; }

	void setBorderColor(const gRGB &col) { m_style.m_border_color = col; }
	void setBorderWidth(int size);

	void setBackgroundPixmap(ePtr<gPixmap> &pm) { m_style.m_background = pm; }
	void setSelectionPixmap(ePtr<gPixmap> &pm) { m_style.m_selection = pm; }
	void setSelectionBorderHidden() { m_style.is_set.border = 1; }

	void setScrollbarForegroundPixmap(ePtr<gPixmap> &pm);
	void setScrollbarBackgroundPixmap(ePtr<gPixmap> &pm);
	void setScrollbarBorderWidth(int width);

	void setScrollbarWidth(int size) { m_scrollbar_width = size; }
	void setScrollbarHeight(int size) { m_scrollbar_height = size; }
	void setScrollbarOffset(int size) { m_scrollbar_offset = size; }
	void setScrollbarLength(int size) { m_scrollbar_length = size; }

	void setFont(gFont *font);
	void setEntryFont(gFont *font) { m_style.m_font = font; }
	void setValueFont(gFont *font) { m_style.m_valuefont = font; }
	void setVAlign(int align) { m_style.m_valign = align; }
	void setHAlign(int align) { m_style.m_halign = align; }
	void setTextPadding(const eRect &padding) { m_style.m_text_padding = padding; }
	void setUseVTIWorkaround(void) { m_style.is_set.use_vti_workaround = 1; }

	void setScrollbarBorderColor(const gRGB &col);
	void setScrollbarForegroundColor(gRGB &col);
	void setScrollbarBackgroundColor(gRGB &col);

	void setMaxRows(int rows) {m_style.m_max_rows = rows; m_style.is_set.max_rows = 1;};
	void setMaxColumns(int columns) {m_style.m_max_columns = columns; m_style.is_set.max_columns = 1;};
	void setItemSpacing(const ePoint &spacing, bool innerOnly=false);
	void setSelectionZoom(float zoom);

	void setOverlay(ePtr<gPixmap> &pm) { m_style.m_overlay = pm; m_style.is_set.overlay = 1; }

	void setPageSize(int size) { m_page_size = size; }

	static void setDefaultScrollbarStyle(int width, int offset, int borderwidth, int scroll, int mode, bool enablewraparound, int pageSize)
	{
		defaultScrollBarWidth = width;
		defaultScrollBarOffset = offset;
		defaultScrollBarBorderWidth = borderwidth;
		defaultScrollBarScroll = scroll;
		defaultWrapAround = enablewraparound;
		defaultScrollBarMode = mode;
		defaultPageSize = pageSize;
	}

	static void setDefaultPadding(const eRect &padding) { defaultPadding = padding; }

	void setTopIndex(int idx);

	bool getWrapAround() { return m_enabled_wrap_around; }
	int getScrollbarScroll() { return m_scrollbar_scroll; }
	int getScrollbarMode() { return m_scrollbar_mode; }
	int getScrollbarWidth() { return m_scrollbar_width; }
	int getScrollbarHeight() { return m_scrollbar_height; }
	int getScrollbarOffset() { return m_scrollbar_offset; }
	int getScrollbarBorderWidth() { return m_scrollbar_border_width; }
	int getItemAlignment() { return m_item_alignment; }
	int getPageSize() { return m_page_size; }
	int getItemHeight() { return m_itemheight; }
	int getItemWidth() { return m_itemwidth; }
	int getOrientation() { return m_orientation; }
	int getTopIndex() { return m_top; }
	bool getSelectionEnable() { return m_selection_enabled; }
	gFont *getFont() { return m_style.m_font; }
	gFont *getEntryFont() { return m_style.m_font; }
	gFont *getValueFont() { return m_style.m_valuefont; }

#ifndef SWIG
	struct eListboxStyle *getLocalStyle(void);

	/* entryAdded: an entry was added *before* the given index. it's index is the given number. */
	void entryAdded(int index);
	/* entryRemoved: an entry with the given index was removed. */
	void entryRemoved(int index);
	/* entryChanged: the entry with the given index was changed and should be redrawn. */
	void entryChanged(int index);
	/* the complete list changed. you should not attemp to keep the current index. */
	void entryReset(bool cursorHome = true);

	int getEntryTop();
	void invalidate(const gRegion &region = gRegion::invalidRegion());

protected:
	int event(int event, void *data = 0, void *data2 = 0);
	void recalcSize();

private:
	ePoint getItemPostion(int index);
	int moveSelectionLineMode(bool doUp, bool doDown, int dir, int oldSel, int oldTopLeft, int maxItems, bool indexChanged, int pageOffset, int topLeft);
	void recalcSizeAlignment(bool scrollbarVisible);
	int setScrollbarPosition();

	static int defaultScrollBarWidth;
	static int defaultScrollBarOffset;
	static int defaultScrollBarBorderWidth;
	static int defaultScrollBarScroll;
	static int defaultScrollBarMode;
	static int defaultPageSize;
	static bool defaultWrapAround;
	static eRect defaultPadding;

	int m_scrollbar_mode, m_prev_scrollbar_page, m_scrollbar_scroll;
	bool m_content_changed;
	bool m_enabled_wrap_around;
	bool m_itemwidth_set;
	bool m_itemheight_set;

	int m_scrollbar_width;
	int m_scrollbar_height;
	int m_scrollbar_length;
	int m_scrollbar_offset;
	int m_scrollbar_border_width;
	int m_top, m_left, m_selected;
	int m_itemheight;
	int m_itemwidth;
	int m_orientation;
	int m_max_columns;
	int m_max_rows;
	int m_selection_enabled;
	int m_page_size;
	int m_item_alignment;
	int xOffset;
	int yOffset;

	bool m_native_keys_bound;
	int m_first_selectable_item;
	int m_last_selectable_item;
	int m_scrollbar_calcsize;

	ePoint m_spacing;
	bool m_spacing_innerOnly;
	ePtr<iListboxContent> m_content;
	eSlider *m_scrollbar;
	eListboxStyle m_style;
	ePtr<gPixmap> m_scrollbarpixmap, m_scrollbarbackgroundpixmap;
#ifdef USE_LIBVUGLES2
	long m_dir;
#endif
#endif
};

#endif
