#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/gui/eslider.h>
#include <lib/actions/action.h>
#include <lib/base/nconfig.h>
#ifdef USE_LIBVUGLES2
#include "vuplus_gles.h"
#endif

int eListbox::defaultScrollBarWidth = eListbox::DefaultScrollBarWidth;
int eListbox::defaultScrollBarOffset = eListbox::DefaultScrollBarOffset;
int eListbox::defaultScrollBarBorderWidth = eListbox::DefaultScrollBarBorderWidth;
int eListbox::defaultScrollBarScroll = eListbox::DefaultScrollBarScroll;
int eListbox::defaultScrollBarMode = eListbox::DefaultScrollBarMode;
int eListbox::defaultPageSize = eListbox::DefaultPageSize;
bool eListbox::defaultWrapAround = eListbox::DefaultWrapAround;
eRect eListbox::defaultPadding = eRect(1, 1, 1, 1);

eListbox::eListbox(eWidget *parent) : eWidget(parent), m_scrollbar_mode(showNever), m_prev_scrollbar_page(-1),
									  m_scrollbar_scroll(byPage), m_content_changed(false), m_enabled_wrap_around(false), m_scrollbar_width(10),
									  m_scrollbar_height(10), m_top(0), m_left(0), m_selected(0), m_itemheight(25), m_itemwidth(25),
									  m_orientation(orVertical), m_max_columns(0), m_max_rows(0), m_selection_enabled(1), m_page_size(0), m_item_alignment(0),
									  m_native_keys_bound(false), m_first_selectable_item(-1), m_last_selectable_item(-1), m_scrollbar(nullptr)
{
	m_scrollbar_width = eListbox::defaultScrollBarWidth;
	m_scrollbar_height = eListbox::defaultScrollBarWidth; // TODO
	m_scrollbar_offset = eListbox::defaultScrollBarOffset;
	m_scrollbar_border_width = eListbox::defaultScrollBarBorderWidth;
	m_scrollbar_scroll = eListbox::defaultScrollBarScroll;
	m_enabled_wrap_around = eListbox::defaultWrapAround;
	m_scrollbar_mode = eListbox::defaultScrollBarMode;
	m_page_size = eListbox::defaultPageSize;

	memset(static_cast<void *>(&m_style), 0, sizeof(m_style));
	m_style.m_text_padding = eListbox::defaultPadding;
	//	setContent(new eListboxStringContent());

	allowNativeKeys(true);

	if (m_scrollbar_mode != showNever)
		setScrollbarMode(m_scrollbar_mode);
}

eListbox::~eListbox()
{
	if (m_scrollbar)
		delete m_scrollbar;

	allowNativeKeys(false);
}

void eListbox::setScrollbarMode(int mode)
{
	m_scrollbar_mode = mode;
	if (m_scrollbar)
	{
		if (m_scrollbar_mode == showNever)
		{
			delete m_scrollbar;
			m_scrollbar = 0;
		}
	}
	else
	{
		m_scrollbar = new eSlider(this);
		m_scrollbar->setIsScrollbar();
		m_scrollbar->hide();
		m_scrollbar->setBorderWidth(m_scrollbar_border_width);
		m_scrollbar->setOrientation(m_orientation == orHorizontal ? eSlider::orHorizontal : eSlider::orVertical);
		m_scrollbar->setRange(0, 100);
		if (m_scrollbarbackgroundpixmap)
			m_scrollbar->setBackgroundPixmap(m_scrollbarbackgroundpixmap);
		if (m_scrollbarpixmap)
			m_scrollbar->setPixmap(m_scrollbarpixmap);
		if (m_style.m_scollbarborder_color_set)
			m_scrollbar->setBorderColor(m_style.m_scollbarborder_color);
		if (m_style.m_scrollbarforeground_color_set)
			m_scrollbar->setForegroundColor(m_style.m_scrollbarforeground_color);
		if (m_style.m_scrollbarbackground_color_set)
			m_scrollbar->setBackgroundColor(m_style.m_scrollbarbackground_color);
	}
}

void eListbox::setScrollbarScroll(int scroll)
{
	if (m_scrollbar && m_scrollbar_scroll != scroll)
	{
		m_scrollbar_scroll = scroll;
		updateScrollBar();
		return;
	}
	m_scrollbar_scroll = scroll;
}

void eListbox::setContent(iListboxContent *content)
{
	m_content = content;
	if (content)
		m_content->setListbox(this);
	entryReset();
}

void eListbox::allowNativeKeys(bool allow)
{
	if (m_native_keys_bound != allow)
	{
		ePtr<eActionMap> ptr;
		eActionMap::getInstance(ptr);
		if (allow)
			ptr->bindAction("ListboxActions", (int64_t)0, 0, this);
		else
			ptr->unbindAction(this, 0);
		m_native_keys_bound = allow;
	}
}

bool eListbox::atBegin()
{
	if (m_content && !m_selected)
		return true;
	return false;
}

bool eListbox::atEnd()
{
	if (m_content && m_content->size() == m_selected + 1)
		return true;
	return false;
}

// Deprecated
void eListbox::moveToEnd()
{
	eWarning("[eListbox] moveToEnd is deprecated. Use moveSelection or goBottom instead.");
	if (!m_content)
		return;
	/* move to last existing one ("end" is already invalid) */
	m_content->cursorEnd();
	m_content->cursorMove(-1);
	/* current selection invisible? */

	int topLeft = m_top;
	int maxItems = m_max_rows;

	if (m_orientation == orHorizontal)
	{
		topLeft = m_left;
		maxItems = m_max_columns;
	}

	if (topLeft + maxItems <= m_content->cursorGet())
	{
		int rest = m_content->size() % maxItems;
		if (rest)
			topLeft = m_content->cursorGet() - rest + 1;
		else
			topLeft = m_content->cursorGet() - maxItems + 1;
		if (topLeft < 0)
			topLeft = 0;
	}

	if (m_orientation == orHorizontal)
		m_left = topLeft;
	else
		m_top = topLeft;
}

void eListbox::moveSelectionTo(int index)
{
	if (m_content)
	{
		m_content->cursorSet(index);
		m_content_changed = true;
		moveSelection(justCheck + 100);
	}
}

void eListbox::setTopIndex(int index)
{
	if (m_content)
	{
		if (m_content->size() > index)
		{
			m_top = index;
			m_content_changed = true;
			moveSelection(justCheck);
		}
	}
}

int eListbox::getCurrentIndex()
{
	if (m_content && m_content->cursorValid())
		return m_content->cursorGet();
	return 0;
}

void eListbox::updateScrollBar()
{
	if (!m_scrollbar || !m_content || m_scrollbar_mode == showNever)
		return;
	int entries = (m_orientation == orGrid) ? (m_content->size() + m_max_columns - 1) / m_max_columns : m_content->size();
	bool scrollbarvisible = m_scrollbar->isVisible();
	int maxItems = (m_orientation == orHorizontal) ? m_max_columns : m_max_rows;

	if (m_content_changed)
	{
		int width = size().width();
		int height = size().height();

		if (m_scrollbar_scroll == byLine)
		{
			if (m_orientation == orHorizontal)
				m_scrollbar->setRange(0, width - (m_scrollbar_border_width * 2));
			else
				m_scrollbar->setRange(0, height - (m_scrollbar_border_width * 2));
		}

		m_content_changed = false;
		if (m_scrollbar_mode == showTopAlways || m_scrollbar_mode == showTopOnDemand)
		{
			m_content->setSize(eSize(m_itemwidth, height - m_scrollbar_height - m_scrollbar_offset));
			m_scrollbar->move(ePoint(0, 0));
			m_scrollbar->resize(eSize(width, m_scrollbar_height));
			if (entries > m_max_columns || m_scrollbar_mode == showLeftAlways)
			{
				m_scrollbar->show();
				scrollbarvisible = true;
			}
			else
			{
				m_scrollbar->hide();
				scrollbarvisible = false;
			}
		}
		else if (m_scrollbar_mode == showLeftOnDemand || m_scrollbar_mode == showLeftAlways)
		{
			if (m_orientation == orVertical)
				m_content->setSize(eSize(width - m_scrollbar_width - m_scrollbar_offset, m_itemheight));
			else
				m_content->setSize(eSize(m_itemwidth, m_itemheight));
			m_scrollbar->move(ePoint(0, 0));
			m_scrollbar->resize(eSize(m_scrollbar_width, height));
			if (entries > m_max_rows || m_scrollbar_mode == showLeftAlways)
			{
				m_scrollbar->show();
				scrollbarvisible = true;
			}
			else
			{
				m_scrollbar->hide();
				scrollbarvisible = false;
			}
		}
		else if (entries > maxItems || m_scrollbar_mode == showAlways)
		{
			if (m_orientation == orHorizontal)
			{
				m_scrollbar->move(ePoint(0, height - m_scrollbar_height));
				m_scrollbar->resize(eSize(width, m_scrollbar_height));
				m_content->setSize(eSize(m_itemwidth, height - m_scrollbar_height - m_scrollbar_offset));
			}
			else if (m_orientation == orVertical)
			{
				m_scrollbar->move(ePoint(width - m_scrollbar_width, 0));
				m_scrollbar->resize(eSize(m_scrollbar_width, height));
				m_content->setSize(eSize(width - m_scrollbar_width - m_scrollbar_offset, m_itemheight));
			}
			else
			{
				m_scrollbar->move(ePoint(width - m_scrollbar_width, 0));
				m_scrollbar->resize(eSize(m_scrollbar_width, height));
				m_content->setSize(eSize(m_itemwidth, m_itemheight));
			}
			m_scrollbar->show();
			scrollbarvisible = true;
		}
		else
		{
			if (m_orientation == orHorizontal)
				m_content->setSize(eSize(m_itemwidth, height));
			else if (m_orientation == orVertical)
				m_content->setSize(eSize(width, m_itemheight));
			else
				m_content->setSize(eSize(m_itemwidth, m_itemheight));
			m_scrollbar->hide();
			scrollbarvisible = false;
		}
	}

	// Don't set Start/End if scollbar not visible or entries/maxItems = 0
	if (maxItems && entries && scrollbarvisible)
	{

		if (m_scrollbar_scroll == byLine)
		{

			if (m_prev_scrollbar_page != m_selected)
			{
				m_prev_scrollbar_page = m_selected;

				int start = 0;
				int selected = (m_orientation == orGrid) ? m_selected / m_max_columns : m_selected;
				int range = size().height() - (m_scrollbar_border_width * 2);
				if (m_orientation == orHorizontal)
					range = size().width() - (m_scrollbar_border_width * 2);
				int end = range;
				// calculate thumb only if needed
				if (entries > 1 && entries > maxItems)
				{
					float fthumb = (float)maxItems / (float)entries * range;
					float fsteps = ((float)(range - fthumb) / (float)entries);
					float fstart = (float)selected * fsteps;
					fthumb = (float)range - (fsteps * (float)(entries - 1));
					int visblethumb = fthumb < 4 ? 4 : (int)(fthumb + 0.5);
					start = (int)(fstart + 0.5);
					end = start + visblethumb;
					if (end > range)
					{
						end = range;
						start = range - visblethumb;
					}
				}

				m_scrollbar->setStartEnd(start, end, true);
			}
			return;
		}

		int topLeft = (m_orientation == orHorizontal) ? m_left : m_top;
		int curVisiblePage = topLeft / maxItems;

		if (m_prev_scrollbar_page != curVisiblePage)
		{
			m_prev_scrollbar_page = curVisiblePage;
			int pages = entries / maxItems;
			if ((pages * maxItems) < entries)
				++pages;
			int start = (topLeft * 100) / (pages * maxItems);
			int vis = (maxItems * 100 + pages * maxItems - 1) / (pages * maxItems);
			if (vis < 3)
				vis = 3;
			m_scrollbar->setStartEnd(start, start + vis);
		}
	}
}

int eListbox::getEntryTop()
{
	/*
		Please Note! This will currently only work for verticial list box.
		It's only used in eListboxPythonMultiContent::setSelectionClip.
	*/
	if (m_orientation == orHorizontal)
		return (m_selected - m_left) * m_itemwidth;
	else if (m_orientation == orVertical)
		return (m_selected - m_top) * m_itemheight;
	else
		return (m_selected - m_top) * m_itemheight;
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
		ASSERT(m_content);

		getStyle(style);

		if (!m_content)
			return 0;

		gPainter &painter = *(gPainter *)data2;

		m_content->cursorSave();
		gRegion entryRect = m_orientation == orVertical ? eRect(0, 0, size().width(), m_itemheight) : eRect(0, 0, m_itemwidth, size().height());
		if (m_orientation == orVertical)
			m_content->cursorMove(m_top - m_selected);
		else if (m_orientation == orHorizontal)
			m_content->cursorMove(m_left - m_selected);
		else
		{
			m_content->cursorMove((m_max_columns * m_top) - m_selected);
			entryRect = eRect(0, 0, m_itemwidth, m_itemheight);
		}

		const gRegion &paint_region = *(gRegion *)data;

		int xOffset = 0;
		int yOffset = 0;
		if (m_scrollbar)
		{
			if (m_scrollbar_mode == showLeftOnDemand || m_scrollbar_mode == showLeftAlways)
			{
				xOffset = m_scrollbar->size().width() + m_scrollbar_offset;
			}

			if (m_scrollbar_mode == showTopOnDemand || m_scrollbar_mode == showTopAlways)
			{
				yOffset = m_scrollbar->size().height() + m_scrollbar_offset;
			}
		}

		int itemOffset = 0;
		if (m_orientation == orGrid)
		{
			style->setStyle(painter, eWindowStyle::styleListboxNormal);
			painter.clear();

			if (m_item_alignment != itemAlignDefault)
			{
				int fullSpace = size().width() - ((m_scrollbar) ? m_scrollbar->size().width() + m_scrollbar_offset : 0);
				int itemSpace = m_max_columns * m_itemwidth;
				if (fullSpace > itemSpace)
				{
					if (m_item_alignment == itemAlignCenter)
					{
						xOffset = (fullSpace - itemSpace) / 2;
					}
					else if (m_item_alignment == itemAlignJustify && m_max_columns > 1)
					{
						itemOffset = (fullSpace - itemSpace) / (m_max_columns - 1);
					}
				}
			}
		}

		int line = 0;

		if (m_orientation == orVertical)
		{

			for (int y = 0, i = 0; i <= m_max_rows; y += m_itemheight, ++i)
			{
				gRegion entry_clip_rect = paint_region & entryRect;

				bool sel = (m_selected == m_content->cursorGet() && m_content->size() && m_selection_enabled);

				if (sel)
					line = i;

				if (!entry_clip_rect.empty())
					m_content->paint(painter, *style, ePoint(xOffset, y), sel);
#ifdef USE_LIBVUGLES2
				if (sel)
				{
					ePoint pos = getAbsolutePosition();
					painter.sendShowItem(m_dir, ePoint(pos.x(), pos.y() + y), eSize(m_scrollbar && m_scrollbar->isVisible() ? size().width() - m_scrollbar->size().width() : size().width(), m_itemheight));
					gles_set_animation_listbox_current(pos.x(), pos.y() + y, m_scrollbar && m_scrollbar->isVisible() ? size().width() - m_scrollbar->size().width() : size().width(), m_itemheight);
					m_dir = justCheck;
				}
#endif
				/* (we could clip with entry_clip_rect, but
				this shouldn't change the behavior of any
				well behaving content, so it would just
				degrade performance without any gain.) */

				m_content->cursorMove(+1);
				entryRect.moveBy(ePoint(0, m_itemheight));
			}
		}

		if (m_orientation == orHorizontal)
		{

			for (int x = 0, i = 0; i <= m_max_columns; x += m_itemwidth, ++i)
			{
				gRegion entry_clip_rect = paint_region & entryRect;

				bool sel = (m_selected == m_content->cursorGet() && m_content->size() && m_selection_enabled);

				if (sel)
					line = i;

				if (!entry_clip_rect.empty())
					m_content->paint(painter, *style, ePoint(x, yOffset), sel);

				/* (we could clip with entry_clip_rect, but
				this shouldn't change the behavior of any
				well behaving content, so it would just
				degrade performance without any gain.) */

				m_content->cursorMove(+1);
				entryRect.moveBy(ePoint(m_itemwidth, 0));
			}
		}

		if (m_orientation == orGrid)
		{
			int i = 0;
			int l = 0;
			int m_max_items = m_max_columns * m_max_rows;
			for (int y = 0; y < m_max_rows; y++)
			{
				for (int x = 0; x < m_max_columns; x++)
				{

					int leftOffset = (itemOffset > 0) ? (itemOffset * x) : xOffset;

					gRegion entry_clip_rect = paint_region & entryRect;

					// This is a workaround because there is a bug in gRegion intersect
					bool paint = !entry_clip_rect.empty();
					if (!paint)
					{
						paint = (paint_region.extends.height() >= (entryRect.extends.y() + entryRect.extends.height()));
					}

					bool sel = (m_selected == m_content->cursorGet() && m_content->size() && m_selection_enabled);

					if (sel)
						line = l;

					if (paint)
						m_content->paint(painter, *style, ePoint(leftOffset + (x * m_itemwidth), y * m_itemheight), sel);

					m_content->cursorMove(+1);
					entryRect.moveBy(ePoint(m_itemwidth, 0));
					++i;
					if (i > m_max_items)
						break;
				}
				l++;

				entryRect.moveBy(ePoint(0, m_itemheight));
				entryRect.extends.setX(0);
				entryRect.extends.setWidth(m_itemwidth);
			}
		}

		// clear/repaint empty/unused space between scrollbar and listbox entries
		if (m_scrollbar)
		{
			if (m_scrollbar_mode == showLeftOnDemand || m_scrollbar_mode == showLeftAlways)
			{
				style->setStyle(painter, eWindowStyle::styleListboxNormal);
				if (m_scrollbar->isVisible())
				{
					painter.clip(eRect(m_scrollbar->position() + ePoint(m_scrollbar->size().width(), 0), eSize(m_scrollbar_offset, m_scrollbar->size().height())));
				}
				else
				{
					painter.clip(eRect(m_scrollbar->position(), eSize(m_scrollbar->size().width() + m_scrollbar_offset, m_scrollbar->size().height())));
				}
				painter.clear();
				painter.clippop();
			}
			else if (m_scrollbar_mode == showTopOnDemand || m_scrollbar_mode == showTopAlways)
			{
				style->setStyle(painter, eWindowStyle::styleListboxNormal);
				if (m_scrollbar->isVisible())
				{
					painter.clip(eRect(m_scrollbar->position() + ePoint(0, m_scrollbar->size().height()), eSize(m_scrollbar->size().width(), m_scrollbar_offset)));
				}
				else
				{
					painter.clip(eRect(m_scrollbar->position(), eSize(m_scrollbar->size().width(), m_scrollbar->size().height() + m_scrollbar_offset)));
				}
				painter.clear();
				painter.clippop();
			}
			else if (m_scrollbar->isVisible())
			{
				style->setStyle(painter, eWindowStyle::styleListboxNormal);
				if (m_orientation == orHorizontal)
				{
					painter.clip(eRect(m_scrollbar->position() - ePoint(0, m_scrollbar_offset), eSize(m_scrollbar->size().width(), m_scrollbar_offset)));
				}
				else
				{
					painter.clip(eRect(m_scrollbar->position() - ePoint(m_scrollbar_offset, 0), eSize(m_scrollbar_offset, m_scrollbar->size().height())));
				}
				painter.clear();
				painter.clippop();
			}
		}

		m_content->cursorSaveLine(line);
		m_content->cursorRestore();

		return 0;
	}

	case evtChangedSize:
		recalcSize();
		return eWidget::event(event, data, data2);

	case evtAction:
		if (isVisible() && !isLowered())
		{
			moveSelection((long)data2);
			return 1;
		}
		return 0;
	default:
		return eWidget::event(event, data, data2);
	}
}

void eListbox::recalcSize()
{
	m_content_changed = true;
	m_prev_scrollbar_page = -1;
	if (m_orientation == orVertical)
	{
		if (m_content)
			m_content->setSize(eSize(size().width(), m_itemheight));
		m_max_rows = size().height() / m_itemheight;
	}
	else if (m_orientation == orHorizontal)
	{
		if (m_content)
			m_content->setSize(eSize(m_itemwidth, size().height()));
		m_max_columns = size().width() / m_itemwidth;
	}
	else
	{
		if (m_content)
			m_content->setSize(eSize(m_itemwidth, m_itemheight));

		m_max_columns = size().width() / m_itemwidth;
		m_max_rows = size().height() / m_itemheight;
	}

	/* TODO: whyever - our size could be invalid, or itemheigh could be wrongly specified. */
	if (m_max_columns < 0)
		m_max_columns = 0;
	if (m_max_rows < 0)
		m_max_rows = 0;

	moveSelection(justCheck);
}

void eListbox::setItemHeight(int h)
{
	if (h)
		m_itemheight = h;
	else
		m_itemheight = 20; // TODO : why 20
	recalcSize();
}

void eListbox::setItemWidth(int w)
{
	if (w)
		m_itemwidth = w;
	else
		m_itemwidth = 20; // TODO : why 20
	recalcSize();
}

void eListbox::setSelectionEnable(int en)
{
	if (m_selection_enabled == en)
		return;
	m_selection_enabled = en;
	entryChanged(m_selected); /* redraw current entry */
}

void eListbox::entryAdded(int index)
{
	m_first_selectable_item = -1;
	m_last_selectable_item = -1;
	if (m_content)
	{
		if (m_orientation == orVertical)
		{
			if ((m_content->size() % m_max_rows) == 1)
				m_content_changed = true;
		}
		else if (m_orientation == orHorizontal)
		{
			if ((m_content->size() % m_max_columns) == 1)
				m_content_changed = true;
		}
		else
			m_content_changed = true;
	}

	/* manage our local pointers. when the entry was added before the current position, we have to advance. */
	/* we need to check <= - when the new entry has the (old) index of the cursor, the cursor was just moved down. */

	if (index <= m_selected)
		++m_selected;
	if (m_orientation == orVertical)
	{
		if (index <= m_top)
			++m_top;
	}
	else
	{
		if (index <= m_left)
			++m_left;
	}

	/* we have to check wether our current cursor is gone out of the screen. */
	/* moveSelection will check for this case */
	moveSelection(justCheck);

	/* now, check if the new index is visible. */
	if (m_orientation == orVertical)
	{
		if ((m_top <= index) && (index < (m_top + m_max_rows)))
		{
			/* todo, calc exact invalidation... */
			invalidate();
		}
	}
	else if (m_orientation == orHorizontal)
	{
		if ((m_left <= index) && (index < (m_left + m_max_columns)))
		{
			/* todo, calc exact invalidation... */
			invalidate();
		}
	}
	else
		invalidate();
}

void eListbox::entryRemoved(int index)
{
	m_first_selectable_item = -1;
	m_last_selectable_item = -1;

	if (m_content)
	{
		if (m_orientation == orVertical)
		{
			if (!(m_content->size() % m_max_rows))
				m_content_changed = true;
		}
		else if (m_orientation == orHorizontal)
		{
			if (!(m_content->size() % m_max_columns))
				m_content_changed = true;
		}
		else
			m_content_changed = true;
	}

	if (index == m_selected && m_content)
		m_selected = m_content->cursorGet();

	if (m_content && m_content->cursorGet() >= m_content->size())
		moveSelection(moveUp);
	else
		moveSelection(justCheck);

	if (m_orientation == orVertical)
	{
		if ((m_top <= index) && (index < (m_top + m_max_rows)))
		{
			/* todo, calc exact invalidation... */
			invalidate();
		}
	}
	else if (m_orientation == orHorizontal)
	{
		if ((m_left <= index) && (index < (m_left + m_max_columns)))
		{
			/* todo, calc exact invalidation... */
			invalidate();
		}
	}
	else
		invalidate();
}

void eListbox::entryChanged(int index)
{
	if (m_orientation == orVertical)
	{
		if ((m_top <= index) && (index < (m_top + m_max_rows)))
		{
			gRegion inv = eRect(0, m_itemheight * (index - m_top), size().width(), m_itemheight);
			invalidate(inv);
		}
	}
	else if (m_orientation == orHorizontal)
	{
		if ((m_left <= index) && (index < (m_left + m_max_columns)))
		{
			gRegion inv = eRect(m_itemwidth * (index - m_left), 0, m_itemwidth, size().height());
			invalidate(inv);
		}
	}
	else
	{
		int col = index % m_max_columns;
		int row = index / m_max_rows;
		gRegion inv = eRect(col * m_itemwidth, row * m_itemheight, m_itemwidth, m_itemheight);
		invalidate(inv);
	}
}

void eListbox::entryReset(bool selectionHome)
{
	m_first_selectable_item = -1;
	m_last_selectable_item = -1;
	m_content_changed = true;
	m_prev_scrollbar_page = -1;
	int oldSel;

	if (selectionHome)
	{
		if (m_content)
			m_content->cursorHome();
		m_top = 0;
		m_left = 0;
		m_selected = 0;
	}

	if (m_content && (m_selected >= m_content->size()))
	{
		if (m_content->size())
			m_selected = m_content->size() - 1;
		else
			m_selected = 0;
		m_content->cursorSet(m_selected);
	}

	oldSel = m_selected;
	moveSelection(justCheck);
	/* if oldSel != m_selected, selectionChanged was already
	   emitted in moveSelection. we want it in any case, so otherwise,
	   emit it now. */
	if (oldSel == m_selected)
		/* emit */ selectionChanged();
	invalidate();
}

void eListbox::setBackgroundColor(gRGB &col)
{
	m_style.m_background_color = col;
	m_style.m_background_color_set = 1;
}

void eListbox::setBackgroundColorSelected(gRGB &col)
{
	m_style.m_background_color_selected = col;
	m_style.m_background_color_selected_set = 1;
}

void eListbox::setForegroundColor(gRGB &col)
{
	m_style.m_foreground_color = col;
	m_style.m_foreground_color_set = 1;
}

void eListbox::setForegroundColorSelected(gRGB &col)
{
	m_style.m_foreground_color_selected = col;
	m_style.m_foreground_color_selected_set = 1;
}

void eListbox::setBorderWidth(int size)
{
	m_style.m_border_size = size;
	if (m_scrollbar)
		m_scrollbar->setBorderWidth(size);
}

void eListbox::setScrollbarBorderWidth(int width)
{
	m_style.m_scrollbarborder_width = width;
	m_style.m_scrollbarborder_width_set = 1;
	if (m_scrollbar)
		m_scrollbar->setBorderWidth(width);
}

void eListbox::setScrollbarForegroundPixmap(ePtr<gPixmap> &pm)
{
	m_scrollbarpixmap = pm;
	if (m_scrollbar && m_scrollbarpixmap)
		m_scrollbar->setPixmap(pm);
}

void eListbox::setScrollbarBackgroundColor(gRGB &col)
{
	m_style.m_scrollbarbackground_color = col;
	m_style.m_scrollbarbackground_color_set = 1;
	if (m_scrollbar)
		m_scrollbar->setBackgroundColor(col);
}

void eListbox::setScrollbarForegroundColor(gRGB &col)
{
	m_style.m_scrollbarforeground_color = col;
	m_style.m_scrollbarforeground_color_set = 1;
	if (m_scrollbar)
		m_scrollbar->setForegroundColor(col);
}

void eListbox::setScrollbarBorderColor(const gRGB &col)
{
	m_style.m_scollbarborder_color = col;
	m_style.m_scollbarborder_color_set = 1;
	if (m_scrollbar)
		m_scrollbar->setBorderColor(col);
}

void eListbox::setScrollbarBackgroundPixmap(ePtr<gPixmap> &pm)
{
	m_scrollbarbackgroundpixmap = pm;
	if (m_scrollbar && m_scrollbarbackgroundpixmap)
		m_scrollbar->setBackgroundPixmap(pm);
}

void eListbox::setItemAlignment(int align)
{
	if (m_item_alignment != align)
	{
		m_item_alignment = align;
		invalidate();
	}
}

void eListbox::invalidate(const gRegion &region)
{
	gRegion tmp(region);
	if (m_content)
		m_content->updateClip(tmp);
	eWidget::invalidate(tmp);
}

struct eListboxStyle *eListbox::getLocalStyle(void)
{
	/* transparency is set directly in the widget */
	m_style.m_transparent_background = isTransparent();
	return &m_style;
}

void eListbox::setOrientation(int newOrentation)
{
	if (m_orientation != newOrentation && m_scrollbar)
	{
		if (newOrentation == orHorizontal)
		{
			m_scrollbar->setOrientation(eSlider::orHorizontal);
		}
		else
		{
			m_scrollbar->setOrientation(eSlider::orVertical);
		}
	}
	m_orientation = newOrentation;
	invalidate();
}

void eListbox::moveSelection(int dir)
{
	/* refuse to do anything without a valid list. */
	if (!m_content)
		return;
	/* if our list does not have one entry, don't do anything. */
	int maxItems = (m_orientation == orVertical) ? m_max_rows : m_max_columns;
	if (m_orientation == orGrid)
	{
		maxItems = m_max_rows * m_max_columns;
	}

	if (!maxItems || !m_content->size())
		return;

	// patch pageUp / pageDown for virtual listbox if native keys enabled
	if (m_orientation == orVertical && m_native_keys_bound)
	{
		if (dir == moveLeft)
			dir = movePageUp;
		if (dir == moveRight)
			dir = movePageDown;
	}

	bool isGrid = m_orientation == orGrid;

	/* we need the old top/sel to see what we have to redraw */
	int oldTop = m_top;
	int oldLeft = m_left;
	int oldSel = m_selected;
	int prevSel = oldSel;
	int newSel;
	int pageOffset = (m_page_size > 0 && m_scrollbar_scroll == byLine) ? m_page_size : maxItems;
	int oldRow = (isGrid && m_max_columns != 0) ? oldSel / m_max_columns : 0;
	int oldColumn = (isGrid && m_max_columns != 0) ? oldSel % m_max_columns : 0;

	bool indexChanged = dir > 100;
	if (indexChanged)
		dir -= 100;

#ifdef USE_LIBVUGLES2
	m_dir = dir;
#endif
	switch (dir)
	{
	case moveFirst:
		if (isGrid)
		{
			int newRow = oldRow;
			do
			{
				m_content->cursorMove(-1);
				newSel = m_content->cursorGet();
				newRow = newSel / m_max_columns;
				if (newRow != oldRow || !m_content->currentCursorSelectable())
				{
					m_content->cursorSet(prevSel);
					break;
				}
				if (newSel == prevSel)
				{
					break;
				}
				prevSel = newSel;

			} while (true);
		}
		break;
	case moveLast:
		if (isGrid)
		{
			int newRow = oldRow;
			do
			{
				m_content->cursorMove(1);
				newSel = m_content->cursorGet();
				newRow = newSel / m_max_columns;
				if (newRow != oldRow || !m_content->currentCursorSelectable())
				{
					m_content->cursorSet(prevSel);
					break;
				}
				if (newSel == prevSel)
				{
					break;
				}
				prevSel = newSel;
			} while (true);
		}
		break;
	case moveBottom:
		m_content->cursorEnd();
		[[fallthrough]];
	case moveUp:
		if (isGrid && dir != moveBottom)
		{
			do
			{
				if (oldRow == 0 && m_enabled_wrap_around)
				{
					m_content->cursorEnd();
					int newColumn = -1;
					do
					{
						m_content->cursorMove(-1);
						newSel = m_content->cursorGet();
						newColumn = newSel % m_max_columns;
					} while (oldColumn != newColumn);
					if (m_content->currentCursorSelectable())
						break;
				}
				else
					m_content->cursorMove(-m_max_columns);

				newSel = m_content->cursorGet();

				if (newSel == prevSel)
				{ // cursorMove reached top and left cursor position the same. Must wrap around ?
					if (m_enabled_wrap_around)
					{
						m_content->cursorEnd();
						m_content->cursorMove(-1);
						newSel = m_content->cursorGet();
					}
					else
					{
						m_content->cursorSet(oldSel);
						break;
					}
				}
				prevSel = newSel;

			} while (newSel != oldSel && !m_content->currentCursorSelectable());
			break;
		}
		[[fallthrough]];
	case moveLeft:
		/* upcoming new grid feature for wrap in a line
		if (isGrid && oldColumn == 0)
		{
			m_content->cursorMove(m_max_columns);
		}
		*/
		do
		{
			m_content->cursorMove(-1);
			newSel = m_content->cursorGet();
			if (newSel == prevSel)
			{ // cursorMove reached top and left cursor position the same. Must wrap around ?
				if (m_enabled_wrap_around)
				{
					m_content->cursorEnd();
					m_content->cursorMove(-1);
					newSel = m_content->cursorGet();
				}
				else
				{
					m_content->cursorSet(oldSel);
					break;
				}
			}
			prevSel = newSel;
		} while (newSel != oldSel && !m_content->currentCursorSelectable());
		break;
	case refresh:
		oldSel = ~m_selected;
		break;
	case moveTop:
		m_content->cursorHome();
		[[fallthrough]];
	case justCheck:
		if (m_content->cursorValid() && m_content->currentCursorSelectable())
			break;
		[[fallthrough]];
	case moveDown:
		if (isGrid)
		{
			do
			{

				bool wrap = (oldRow == (m_max_rows - 1)) || (oldSel + m_max_columns >= m_content->size());
				if (wrap && m_enabled_wrap_around)
				{
					m_content->cursorHome();
					m_content->cursorMove(oldColumn);
					if (m_content->currentCursorSelectable())
						break;
				}
				else
					m_content->cursorMove(m_max_columns);
				if (!m_content->cursorValid())
				{ // cursorMove reached end and left cursor position past the list. Must wrap around ?
					if (m_enabled_wrap_around)
						m_content->cursorHome();
					else
						m_content->cursorSet(oldSel);
				}
				newSel = m_content->cursorGet();
			} while (newSel != oldSel && !m_content->currentCursorSelectable());
			break;
		}
		[[fallthrough]];
	case moveRight:
		/* upcoming new grid feature for wrap in a line
		if (isGrid && oldColumn >= m_max_columns)
		{
			m_content->cursorMove(-m_max_columns);
			newSel = m_content->cursorGet();
			eDebug("[eListbox] moveRight newSel=%d oldColumn=%d m_max_columns=%d" , newSel, oldColumn, m_max_columns);
		}
		*/
		do
		{
			m_content->cursorMove(1);
			if (!m_content->cursorValid())
			{ // cursorMove reached end and left cursor position past the list. Must wrap around ?
				if (m_enabled_wrap_around)
					m_content->cursorHome();
				else
					m_content->cursorSet(oldSel);
			}
			newSel = m_content->cursorGet();
		} while (newSel != oldSel && !m_content->currentCursorSelectable());
		break;
	case movePageUp:
	{
		int pageind;
		do
		{
			m_content->cursorMove(-pageOffset);
			newSel = m_content->cursorGet();
			pageind = newSel % maxItems; // rememer were we land in thsi page (could be different on topmost page)
			prevSel = newSel - pageind;	 // get top of page index
			// find first selectable entry in new page. First check bottom part, than upper part
			while (newSel != prevSel + maxItems && m_content->cursorValid() && !m_content->currentCursorSelectable())
			{
				m_content->cursorMove(1);
				newSel = m_content->cursorGet();
			}
			if (!m_content->currentCursorSelectable()) // no selectable found in bottom part of page
			{
				m_content->cursorSet(prevSel + pageind);
				while (newSel != prevSel && !m_content->currentCursorSelectable())
				{
					m_content->cursorMove(-1);
					newSel = m_content->cursorGet();
				}
			}
			if (m_content->currentCursorSelectable())
				break;
			if (newSel == 0) // at top and nothing found . Go down till something selectable or old location
			{
				while (newSel != oldSel && !m_content->currentCursorSelectable())
				{
					m_content->cursorMove(1);
					newSel = m_content->cursorGet();
				}
				break;
			}
			m_content->cursorSet(prevSel + pageind);
		} while (newSel == prevSel);
		break;
	}
	case movePageDown:
	{
		int pageind;
		do
		{
			m_content->cursorMove(pageOffset);
			if (!m_content->cursorValid())
				m_content->cursorMove(-1);
			newSel = m_content->cursorGet();
			pageind = newSel % maxItems;
			prevSel = newSel - pageind; // get top of page index
			// find a selectable entry in the new page. first look up then down from current screenlocation on the page
			while (newSel != prevSel && !m_content->currentCursorSelectable())
			{
				m_content->cursorMove(-1);
				newSel = m_content->cursorGet();
			}
			if (!m_content->currentCursorSelectable()) // no selectable found in top part of page
			{
				m_content->cursorSet(prevSel + pageind);
				do
				{
					m_content->cursorMove(1);
					newSel = m_content->cursorGet();
				} while (newSel != prevSel + maxItems && m_content->cursorValid() && !m_content->currentCursorSelectable());
			}
			if (!m_content->cursorValid())
			{
				// we reached the end of the list
				// Back up till something selectable or we reach oldSel again
				// E.g this should bring us back to the last selectable item on the original page
				do
				{
					m_content->cursorMove(-1);
					newSel = m_content->cursorGet();
				} while (newSel != oldSel && !m_content->currentCursorSelectable());
				break;
			}
			if (newSel != prevSel + maxItems)
				break;
			m_content->cursorSet(prevSel + pageind); // prepare for next page down
		} while (newSel == prevSel + maxItems);
		break;
	}
	}

	/* now, look wether the current selection is out of screen */
	m_selected = m_content->cursorGet();
	if (m_orientation == orHorizontal)
		m_left = m_selected - (m_selected % maxItems);
	else
		m_top = (m_scrollbar_scroll == byLine) ? m_selected / maxItems : (m_selected / maxItems) * m_max_rows;

	/*  new scollmode by line if not on the first page .. only for vertical */
	if (m_scrollbar_scroll == byLine && m_content->size() > maxItems)
	{
		if (m_orientation == orHorizontal)
			m_left = moveSelectionLineMode((dir == moveLeft), (dir == moveRight), dir, oldSel, oldLeft, maxItems, indexChanged, pageOffset, m_left);
		else
			m_top = moveSelectionLineMode((dir == moveUp), (dir == moveDown), dir, oldSel, oldTop, maxItems, indexChanged, pageOffset, m_top);
	}

	// if it is, then the old selection clip is irrelevant, clear it or we'll get artifacts
	if (m_orientation == orHorizontal)
	{
		if (m_left != oldLeft && m_content)
			m_content->resetClip();
	}
	else
	{
		if (m_top != oldTop && m_content)
			m_content->resetClip();
	}

	if (oldSel != m_selected) /* emit */
		selectionChanged();

	updateScrollBar();

	if (m_orientation == orHorizontal)
	{
		if (m_left != oldLeft)
		{
			invalidate();
		}
		else if (m_selected != oldSel)
		{
			/* redraw the old and newly selected */
			gRegion inv = eRect(m_itemwidth * (m_selected - m_left), 0, m_itemwidth, size().height());
			inv |= eRect(m_itemwidth * (oldSel - m_left), 0, m_itemwidth, size().height());
			invalidate(inv);
		}
	}
	else
	{
		if (m_top != oldTop)
		{
			invalidate();
		}
		else if (m_selected != oldSel)
		{
			if (m_orientation == orGrid)
			{
				// TODO:
				// gRegion inv = eRect(0, m_itemheight * m_top, m_itemwidth, m_itemheight);
				// inv |= eRect(0, m_itemheight * (oldSel - m_top), m_itemwidth, m_itemheight);
				// invalidate(inv);
				invalidate();
			}
			else
			{
				/* redraw the old and newly selected */
				gRegion inv = eRect(0, m_itemheight * (m_selected - m_top), size().width(), m_itemheight);
				inv |= eRect(0, m_itemheight * (oldSel - m_top), size().width(), m_itemheight);
				invalidate(inv);
			}
		}
	}
}

int eListbox::moveSelectionLineMode(bool doUp, bool doDown, int dir, int oldSel, int oldTopLeft, int maxItems, bool indexChanged, int pageOffset, int topLeft)
{
	int oldLine = m_content->cursorRestoreLine();
	int max = m_content->size() - maxItems;
	bool customPageSize = pageOffset != maxItems;
	if (m_orientation == orGrid)
	{
		int newline = (m_selected / m_max_columns);
		if (newline < m_max_rows)
		{
			return 0;
		}
		int newlinecalc = (m_selected / m_max_columns) - oldTopLeft;
		if (doUp && m_enabled_wrap_around && oldSel == 0)
		{
			return newline - m_max_rows + 1;
		}
		if (doUp)
		{
			if ((oldLine > 0 && oldTopLeft > 0) || (newlinecalc > 0))
			{
				return oldTopLeft;
			}
		}
		if (newlinecalc == oldLine)
			return oldTopLeft;
		if (m_max_rows < newline)
		{
			return newline - m_max_rows + 1;
		}
		return topLeft;
	}

	bool jumpBottom = (dir == moveBottom);

	if (dir == movePageDown && m_selected > max && !customPageSize)
	{
		jumpBottom = true;
	}

	if (doUp || (customPageSize && dir == movePageUp))
	{
		if (m_selected > oldSel)
		{
			jumpBottom = true;
		}
		else if (oldLine > 0)
			oldLine -= oldSel - m_selected;

		if (oldLine < 0 && m_selected > maxItems)
			oldLine = 0;
	}

	if (m_last_selectable_item == -1 && dir == justCheck)
	{
		m_content->cursorEnd();
		do
		{
			m_content->cursorMove(-1);
			m_last_selectable_item = m_content->cursorGet();
		} while (!m_content->currentCursorSelectable());
		m_content->cursorSet(m_selected);
	}

	if (doDown || dir == movePageDown)
	{

		int newline = oldLine + (m_selected - oldSel);
		if (newline < maxItems && newline > 0)
		{
			topLeft = oldSel - oldLine;
		}
		else
		{
			topLeft = m_selected - (maxItems - 1);
			if (m_selected < maxItems)
			{
				topLeft = 0;
			}
		}

		if (m_last_selectable_item != m_content->size() - 1 && m_selected >= m_last_selectable_item)
			jumpBottom = true;
	}

	if (jumpBottom)
	{
		topLeft = max;
	}
	else if (dir == justCheck)
	{
		if (m_first_selectable_item == -1)
		{
			m_first_selectable_item = 0;
			if (m_selected > 0)
			{
				m_content->cursorHome();
				if (!m_content->currentCursorSelectable())
				{
					do
					{
						m_content->cursorMove(1);
						m_first_selectable_item = m_content->cursorGet();
					} while (!m_content->currentCursorSelectable());
				}
				m_content->cursorSet(m_selected);
				if (oldLine == 0)
					oldLine = m_selected;
			}
		}
		if (indexChanged && m_selected < maxItems)
		{
			oldLine = m_selected;
		}

		// special case for initial draw
		topLeft = m_selected - oldLine;
		if (topLeft == 0 && m_selected > maxItems)
		{
			topLeft = m_selected - (maxItems / 2);
		}
	}
	else if (doUp || dir == movePageUp)
	{
		if (m_first_selectable_item > 0 && m_selected == m_first_selectable_item)
		{
			oldLine = m_selected;
		}
		topLeft = m_selected - oldLine;
	}

	if (topLeft < 0 || oldLine < 0)
	{
		topLeft = 0;
	}

	return topLeft;
}
