#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/gdi/font.h>
#include <lib/python/python.h>

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

iListboxContent::iListboxContent(): m_listbox(0)
{
}

void iListboxContent::setListbox(eListbox *lb)
{
	m_listbox = lb;
	m_listbox->setItemHeight(getItemHeight());
}

int iListboxContent::currentCursorSelectable()
{
	return 1;
}

//////////////////////////////////////

DEFINE_REF(eListboxPythonStringContent);

eListboxPythonStringContent::eListboxPythonStringContent(): m_itemheight(25)
{
}

eListboxPythonStringContent::~eListboxPythonStringContent()
{
	Py_XDECREF(m_list);
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

int eListboxPythonStringContent::currentCursorSelectable()
{
	if (m_list && cursorValid())
	{
		ePyObject item = PyList_GET_ITEM(m_list, m_cursor);
		if (!PyTuple_Check(item))
			return 1;
		if (PyTuple_Size(item) >= 2)
			return 1;
	}
	return 0;
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
	
void eListboxPythonStringContent::setSize(const eSize &size)
{
	m_itemsize = size;
}

void eListboxPythonStringContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt = new gFont("Regular", 20);
	painter.clip(eRect(offset, m_itemsize));
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);

	eListboxStyle *local_style = 0;

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

		/* if we have a local background color set, use that. */
	if (local_style && local_style->m_background_color_set)
		painter.setBackgroundColor(local_style->m_background_color);

		/* same for foreground */
	if (local_style && local_style->m_foreground_color_set)
		painter.setForegroundColor(local_style->m_foreground_color);

		/* if we have no transparent background */
	if (!local_style || !local_style->m_transparent_background)
	{
			/* blit background picture, if available (otherwise, clear only) */
		if (local_style && local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), 0);
		else
			painter.clear();
	} else
	{
		if (local_style && local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), gPainter::BT_ALPHATEST);
	}

	if (m_list && cursorValid())
	{
		int gray = 0;
		ePyObject item = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!
		painter.setFont(fnt);

			/* the user can supply tuples, in this case the first one will be displayed. */		
		if (PyTuple_Check(item))
		{
			if (PyTuple_Size(item) == 1)
				gray = 1;
			item = PyTuple_GET_ITEM(item, 0);
		}

		if (selected && local_style && local_style->m_selection)
			painter.blit(local_style->m_selection, offset, eRect(), gPainter::BT_ALPHATEST);

		if (item == Py_None)
		{
				/* seperator */
			int half_height = m_itemsize.height() / 2;
			painter.fill(eRect(offset.x() + half_height, offset.y() + half_height - 2, m_itemsize.width() - m_itemsize.height(), 4));
		} else
		{
			const char *string = PyString_Check(item) ? PyString_AsString(item) : "<not-a-string>";
			ePoint text_offset = offset + (selected ? ePoint(2, 2) : ePoint(1, 1));
			if (gray)
				painter.setForegroundColor(gRGB(0x808080));
			painter.renderText(eRect(text_offset, m_itemsize), string);
		}

		if (selected && (!local_style || !local_style->m_selection))
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
	}

	painter.clippop();
}

void eListboxPythonStringContent::setList(ePyObject list)
{
	Py_XDECREF(m_list);
	if (!PyList_Check(list))
	{
		m_list = ePyObject();
	} else
	{
		m_list = list;
		Py_INCREF(m_list);
	}

	if (m_listbox)
		m_listbox->entryReset(false);
}

PyObject *eListboxPythonStringContent::getCurrentSelection()
{
	if (!(m_list && cursorValid()))
		Py_RETURN_NONE;

	ePyObject r = PyList_GET_ITEM(m_list, m_cursor);
	Py_XINCREF(r);
	return r;
}

void eListboxPythonStringContent::invalidateEntry(int index)
{
	if (m_listbox)
		m_listbox->entryChanged(index);
}

void eListboxPythonStringContent::invalidate()
{
	if (m_listbox)
	{
		int s = size();
		if ( m_cursor >= s )
			m_listbox->moveSelectionTo(s?s-1:0);
		m_listbox->invalidate();
	}
}

//////////////////////////////////////

void eListboxPythonConfigContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt = new gFont("Regular", 20);
	ePtr<gFont> fnt2 = new gFont("Regular", 16);
	eRect itemrect(offset, m_itemsize);
	eListboxStyle *local_style = 0;

	painter.clip(itemrect);
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

		/* if we have a local background color set, use that. */
	if (local_style && local_style->m_background_color_set)
		painter.setBackgroundColor(local_style->m_background_color);

		/* same for foreground */
	if (local_style && local_style->m_foreground_color_set)
		painter.setForegroundColor(local_style->m_foreground_color);

	if (!local_style || !local_style->m_transparent_background)
		/* if we have no transparent background */
	{
		/* blit background picture, if available (otherwise, clear only) */
		if (local_style && local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), 0);
		else
			painter.clear();
	} else
	{
		if (local_style && local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), gPainter::BT_ALPHATEST);
	}

	if (m_list && cursorValid())
	{
			/* get current list item */
		ePyObject item = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!
		ePyObject text, value;
		painter.setFont(fnt);

		if (selected && local_style && local_style->m_selection)
			painter.blit(local_style->m_selection, offset, eRect(), gPainter::BT_ALPHATEST);

			/* the first tuple element is a string for the left side.
			   the second one will be called, and the result shall be an tuple.
			   
			   of this tuple,
			   the first one is the type (string).
			   the second one is the value. */
		if (PyTuple_Check(item))
		{
				/* handle left part. get item from tuple, convert to string, display. */
				
			text = PyTuple_GET_ITEM(item, 0);
			text = PyObject_Str(text); /* creates a new object - old object was borrowed! */
			const char *string = (text && PyString_Check(text)) ? PyString_AsString(text) : "<not-a-string>";
			eSize item_left = eSize(m_seperation, m_itemsize.height());
			eSize item_right = eSize(m_itemsize.width() - m_seperation, m_itemsize.height());
			painter.renderText(eRect(offset, item_left), string, gPainter::RT_HALIGN_LEFT);
			Py_XDECREF(text);
			
				/* when we have no label, align value to the left. (FIXME: 
				   don't we want to specifiy this individually?) */
			int value_alignment_left = !*string;
			
				/* now, handle the value. get 2nd part from tuple*/
			value = PyTuple_GET_ITEM(item, 1);
			if (value)
			{
				ePyObject args = PyTuple_New(1);
				PyTuple_SET_ITEM(args, 0, PyInt_FromLong(selected));
				
					/* CallObject will call __call__ which should return the value tuple */
				value = PyObject_CallObject(value, args);
				
				if (PyErr_Occurred())
					PyErr_Print();

				Py_DECREF(args);
					/* the PyInt was stolen. */
			}
			
				/*  check if this is really a tuple */
			if (value && PyTuple_Check(value))
			{
					/* convert type to string */
				ePyObject type = PyTuple_GET_ITEM(value, 0);
				const char *atype = (type && PyString_Check(type)) ? PyString_AsString(type) : 0;
				
				if (atype)
				{
					if (!strcmp(atype, "text"))
					{
						ePyObject pvalue = PyTuple_GET_ITEM(value, 1);
						const char *value = (pvalue && PyString_Check(pvalue)) ? PyString_AsString(pvalue) : "<not-a-string>";
						painter.setFont(fnt2);
						if (value_alignment_left)
							painter.renderText(eRect(offset, item_right), value, gPainter::RT_HALIGN_LEFT);
						else
							painter.renderText(eRect(offset + eSize(m_seperation, 0), item_right), value, gPainter::RT_HALIGN_RIGHT);

							/* pvalue is borrowed */
					} else if (!strcmp(atype, "slider"))
					{
						ePyObject pvalue = PyTuple_GET_ITEM(value, 1);
						ePyObject psize = PyTuple_GET_ITEM(value, 2);
						
							/* convert value to Long. fallback to -1 on error. */
						int value = (pvalue && PyInt_Check(pvalue)) ? PyInt_AsLong(pvalue) : -1;
						int size = (pvalue && PyInt_Check(psize)) ? PyInt_AsLong(psize) : 100;
						
							/* calc. slider length */
						int width = item_right.width() * value / size;
						int height = item_right.height();
						
												
							/* draw slider */
						//painter.fill(eRect(offset.x() + m_seperation, offset.y(), width, height));
						//hack - make it customizable
						painter.fill(eRect(offset.x() + m_seperation, offset.y() + 5, width, height-10));
						
							/* pvalue is borrowed */
					} else if (!strcmp(atype, "mtext"))
					{
						ePyObject pvalue = PyTuple_GET_ITEM(value, 1);
						const char *text = (pvalue && PyString_Check(pvalue)) ? PyString_AsString(pvalue) : "<not-a-string>";
						int xoffs = value_alignment_left ? 0 : m_seperation;
						ePtr<eTextPara> para = new eTextPara(eRect(offset + eSize(xoffs, 0), item_right));
						para->setFont(fnt2);
						para->renderString(text, 0);
						para->realign(value_alignment_left ? eTextPara::dirLeft : eTextPara::dirRight);
						int glyphs = para->size();
						
						ePyObject plist;
						
						if (PyTuple_Size(value) >= 3)
							plist = PyTuple_GET_ITEM(value, 2);
						
						int entries = 0;

						if (plist && PyList_Check(plist))
							entries = PyList_Size(plist);
						
						for (int i = 0; i < entries; ++i)
						{
							ePyObject entry = PyList_GET_ITEM(plist, i);
							int num = PyInt_Check(entry) ? PyInt_AsLong(entry) : -1;
							
							if ((num < 0) || (num >= glyphs))
								eWarning("glyph index %d in PythonConfigList out of bounds!", num);
							else
							{
								para->setGlyphFlag(num, GS_INVERT);
								eRect bbox;
								bbox = para->getGlyphBBox(num);
								bbox = eRect(bbox.left(), offset.y(), bbox.width(), m_itemsize.height());
								painter.fill(bbox);
							}
								/* entry is borrowed */
						}
						
						painter.renderPara(para, ePoint(0, 0));
							/* pvalue is borrowed */
							/* plist is 0 or borrowed */
					}
				}
					/* type is borrowed */
			} else
				eWarning("eListboxPythonConfigContent: second value of tuple is not a tuple.");
				/* value is borrowed */
		}

		if (selected && (!local_style || !local_style->m_selection))
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
	}
	
	painter.clippop();
}

int eListboxPythonConfigContent::currentCursorSelectable()
{
	return eListboxPythonStringContent::currentCursorSelectable();
}

//////////////////////////////////////

	/* todo: make a real infrastructure here! */
RESULT SwigFromPython(ePtr<gPixmap> &res, PyObject *obj);

eListboxPythonMultiContent::eListboxPythonMultiContent()
	:m_clip(gRegion::invalidRegion()), m_old_clip(gRegion::invalidRegion())
{
}

eListboxPythonMultiContent::~eListboxPythonMultiContent()
{
	Py_XDECREF(m_buildFunc);
	Py_XDECREF(m_selectableFunc);
}

void eListboxPythonMultiContent::setSelectionClip(eRect &rect, bool update)
{
	m_selection_clip = rect;
	if (m_listbox)
		rect.moveBy(ePoint(0, m_listbox->getEntryTop()));
	if (m_clip.valid())
		m_clip |= rect;
	else
		m_clip = rect;
	if (update && m_listbox)
		m_listbox->entryChanged(m_cursor);
}

static void clearRegion(gPainter &painter, eWindowStyle &style, eListboxStyle *local_style, ePyObject pforeColor, ePyObject pbackColor, ePyObject pbackColorSelected, int selected, gRegion &rc, eRect &sel_clip)
{
	if (selected && sel_clip.valid())
	{
		bool clear=true;
		painter.clip(rc-sel_clip);
		if (pbackColor)
		{
			int color = PyInt_AsLong(pbackColor);
			painter.setBackgroundColor(gRGB(color));
		} // transparent background?
		else if (local_style && local_style->m_transparent_background) 
			clear=false;
		// if we have a local background color set, use that. 
		else if (local_style && local_style->m_background_color_set)
			painter.setBackgroundColor(local_style->m_background_color);
		else
			style.setStyle(painter, eWindowStyle::styleListboxNormal);
		if (clear)
			painter.clear();
		painter.clippop();
		painter.clip(rc&sel_clip);
		style.setStyle(painter, eWindowStyle::styleListboxSelected);
		if (pbackColorSelected)
		{
			int color = PyInt_AsLong(pbackColorSelected);
			painter.setBackgroundColor(gRGB(color));
		}
		painter.clear();
		painter.clippop();
	}
	else
	{
		if (selected)
		{
			style.setStyle(painter, eWindowStyle::styleListboxSelected);
			if (pbackColorSelected)
			{
				int color = PyInt_AsLong(pbackColorSelected);
				painter.setBackgroundColor(gRGB(color));
			}
			painter.clear();
		}
		else
		{
			bool clear=true;
			style.setStyle(painter, eWindowStyle::styleListboxNormal);
			if (pbackColor)
			{
				int color = PyInt_AsLong(pbackColor);
				painter.setBackgroundColor(gRGB(color));
			}/* if we have a local background color set, use that. */
			else if (local_style)
			{
				if (local_style->m_transparent_background)
					clear=false;
				else if (local_style->m_background_color_set)
					painter.setBackgroundColor(local_style->m_background_color);
			}
			/* if we have no transparent background */
			if (clear)
				painter.clear();
		}
	}
	if (pforeColor)
	{
		int color = PyInt_AsLong(pforeColor);
		painter.setForegroundColor(gRGB(color));
	}/* if we have a local foreground color set, use that. */
	else if (local_style && local_style->m_foreground_color_set)
		painter.setForegroundColor(local_style->m_foreground_color);
}

void eListboxPythonMultiContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	gRegion itemregion(eRect(offset, m_itemsize));
	eListboxStyle *local_style = 0;
	eRect sel_clip(m_selection_clip);
	if (sel_clip.valid())
		sel_clip.moveBy(offset);

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

	painter.clip(itemregion);

	clearRegion(painter, style, local_style, ePyObject(), ePyObject(), ePyObject(), selected, itemregion, sel_clip);

	ePyObject items;

	if (m_list && cursorValid())
	{
		items = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!

		if (m_buildFunc)
		{
			if (PyCallable_Check(m_buildFunc))  // when we have a buildFunc then call it
			{
				if (PyTuple_Check(items))
					items = PyObject_CallObject(m_buildFunc, items);
				else
					eDebug("items is no tuple");
			}
			else
				eDebug("buildfunc is not callable");
		}

		if (!items)
		{
			eDebug("eListboxPythonMultiContent: error getting item %d", m_cursor);
			goto error_out;
		}

		if (!PyList_Check(items))
		{
			eDebug("eListboxPythonMultiContent: list entry %d is not a list", m_cursor);
			goto error_out;
		}

		int size = PyList_Size(items);
		for (int i = 1; i < size; ++i)
		{
			ePyObject item = PyList_GET_ITEM(items, i); // borrowed reference!
			bool reset_colors=false;

			if (!item)
			{
				eDebug("eListboxPythonMultiContent: ?");
				goto error_out;
			}

			if (!PyTuple_Check(item))
			{
				eDebug("eListboxPythonMultiContent did not receive a tuple.");
				goto error_out;
			}

			int size = PyTuple_Size(item);

			if (!size)
			{
				eDebug("eListboxPythonMultiContent receive empty tuple.");
				goto error_out;
			}

			int type = PyInt_AsLong(PyTuple_GET_ITEM(item, 0));

			switch (type)
			{
			case TYPE_TEXT: // text
			{
			/*
				(0, x, y, width, height, fnt, flags, "bla" [, color, backColor, backColorSelected, borderWidth, borderColor] )
			*/
				ePyObject px = PyTuple_GET_ITEM(item, 1),
							py = PyTuple_GET_ITEM(item, 2),
							pwidth = PyTuple_GET_ITEM(item, 3),
							pheight = PyTuple_GET_ITEM(item, 4),
							pfnt = PyTuple_GET_ITEM(item, 5),
							pflags = PyTuple_GET_ITEM(item, 6),
							pstring = PyTuple_GET_ITEM(item, 7),
							pforeColor, pbackColor, pbackColorSelected, pborderWidth, pborderColor;

				if (!(px && py && pwidth && pheight && pfnt && pflags && pstring))
				{
					eDebug("eListboxPythonMultiContent received too small tuple (must be (TYPE_TEXT, x, y, width, height, fnt, flags, string [, color, backColor, backColorSelected, borderWidth, borderColor])");
					goto error_out;
				}

				if (size > 8)
				{
					pforeColor = PyTuple_GET_ITEM(item, 8);
					if (pforeColor == Py_None)
						pforeColor=ePyObject();
				}
				if (size > 9)
				{
					pbackColor = PyTuple_GET_ITEM(item, 9);
					if (pbackColor == Py_None)
						pbackColor=ePyObject();
				}
				if (size > 10)
				{
					pbackColorSelected = PyTuple_GET_ITEM(item, 10);
					if (pbackColorSelected == Py_None)
						pbackColorSelected=ePyObject();
				}
				if (size > 11)
					pborderWidth = PyTuple_GET_ITEM(item, 11);
				if (size > 12)
					pborderColor = PyTuple_GET_ITEM(item, 12);

				const char *string = (PyString_Check(pstring)) ? PyString_AsString(pstring) : "<not-a-string>";
				int x = PyInt_AsLong(px) + offset.x();
				int y = PyInt_AsLong(py) + offset.y();
				int width = PyInt_AsLong(pwidth);
				int height = PyInt_AsLong(pheight);
				int flags = PyInt_AsLong(pflags);
				int fnt = PyInt_AsLong(pfnt);
				int bwidth = pborderWidth ? PyInt_AsLong(pborderWidth) : 0;

				if (m_font.find(fnt) == m_font.end())
				{
					eDebug("eListboxPythonMultiContent: specified font %d was not found!", fnt);
					goto error_out;
				}

				eRect rect(x+bwidth, y+bwidth, width-bwidth*2, height-bwidth*2);
				painter.clip(rect);
				if (pbackColor || pbackColorSelected || pforeColor)
				{
					gRegion rc(rect);
					clearRegion(painter, style, local_style, pforeColor, pbackColor, pbackColorSelected, selected, rc, sel_clip);
					reset_colors=true;
				}

				painter.setFont(m_font[fnt]);
				painter.renderText(rect, string, flags);
				painter.clippop();

				// draw border
				if (bwidth)
				{
					eRect rect(eRect(x, y, width, height));
					painter.clip(rect);
					if (pborderColor)
					{
						int color = PyInt_AsLong(pborderColor);
						painter.setForegroundColor(gRGB(color));
					}
					else if (pforeColor) // reset to normal color
						style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);

					rect.setRect(x, y, width, bwidth);
					painter.fill(rect);

					rect.setRect(x, y+bwidth, bwidth, height-bwidth);
					painter.fill(rect);

					rect.setRect(x+bwidth, y+height-bwidth, width-bwidth, bwidth);
					painter.fill(rect);

					rect.setRect(x+width-bwidth, y+bwidth, bwidth, height-bwidth);
					painter.fill(rect);

					painter.clippop();
				}
				break;
			}
			case TYPE_PROGRESS: // Progress
			{
			/*
				(1, x, y, width, height, filled_percent [, borderWidth, foreColor, backColor, backColorSelected] )
			*/
				ePyObject px = PyTuple_GET_ITEM(item, 1),
							py = PyTuple_GET_ITEM(item, 2),
							pwidth = PyTuple_GET_ITEM(item, 3),
							pheight = PyTuple_GET_ITEM(item, 4),
							pfilled_perc = PyTuple_GET_ITEM(item, 5),
							pborderWidth, pforeColor, pbackColor, pbackColorSelected;

				if (!(px && py && pwidth && pheight && pfilled_perc))
				{
					eDebug("eListboxPythonMultiContent received too small tuple (must be (TYPE_PROGRESS, x, y, width, height, filled percent [,border width, foreColor, backColor, backColorSelected]))");
					goto error_out;
				}

				if (size > 6)
					pborderWidth = PyTuple_GET_ITEM(item, 6);
				if (size > 7)
					pforeColor = PyTuple_GET_ITEM(item, 7);
				if (size > 8)
				{
					pbackColor = PyTuple_GET_ITEM(item, 8);
					if (pbackColor == Py_None)
						pbackColor=ePyObject();
				}
				if (size > 9)
				{
					pbackColorSelected = PyTuple_GET_ITEM(item, 9);
					if (pbackColorSelected == Py_None)
						pbackColorSelected=ePyObject();
				}

				int x = PyInt_AsLong(px) + offset.x();
				int y = PyInt_AsLong(py) + offset.y();
				int width = PyInt_AsLong(pwidth);
				int height = PyInt_AsLong(pheight);
				int filled = PyInt_AsLong(pfilled_perc);
				int bwidth = pborderWidth ? PyInt_AsLong(pborderWidth) : 2;

				eRect rect(x, y, width, height);
				painter.clip(rect);
				if (pbackColor || pbackColorSelected || pforeColor)
				{
					gRegion rc(rect);
					clearRegion(painter, style, local_style, pforeColor, pbackColor, pbackColorSelected, selected, rc, sel_clip);
					reset_colors=true;
				}

				// border
				rect.setRect(x, y, width, bwidth);
				painter.fill(rect);

				rect.setRect(x, y+bwidth, bwidth, height-bwidth);
				painter.fill(rect);

				rect.setRect(x+bwidth, y+height-bwidth, width-bwidth, bwidth);
				painter.fill(rect);

				rect.setRect(x+width-bwidth, y+bwidth, bwidth, height-bwidth);
				painter.fill(rect);

				// progress
				rect.setRect(x+bwidth, y+bwidth, (width-bwidth*2) * filled / 100, height-bwidth*2);
				painter.fill(rect);

				painter.clippop();

				break;
			}
			case TYPE_PIXMAP_ALPHATEST:
			case TYPE_PIXMAP: // pixmap
			{
			/*
				(2, x, y, width, height, pixmap [, backColor, backColorSelected] )
			*/

				ePyObject px = PyTuple_GET_ITEM(item, 1),
							py = PyTuple_GET_ITEM(item, 2),
							pwidth = PyTuple_GET_ITEM(item, 3),
							pheight = PyTuple_GET_ITEM(item, 4),
							ppixmap = PyTuple_GET_ITEM(item, 5),
							pbackColor, pbackColorSelected;

				if (!(px && py && pwidth && pheight && ppixmap))
				{
					eDebug("eListboxPythonMultiContent received too small tuple (must be (TYPE_PIXMAP, x, y, width, height, pixmap [, backColor, backColorSelected] ))");
					goto error_out;
				}

				int x = PyInt_AsLong(px) + offset.x();
				int y = PyInt_AsLong(py) + offset.y();
				int width = PyInt_AsLong(pwidth);
				int height = PyInt_AsLong(pheight);
				ePtr<gPixmap> pixmap;
				if (SwigFromPython(pixmap, ppixmap))
				{
					eDebug("eListboxPythonMultiContent (Pixmap) get pixmap failed");
					goto error_out;
				}

				if (size > 6)
				{
					pbackColor = PyTuple_GET_ITEM(item, 6);
					if (pbackColor == Py_None)
						pbackColor=ePyObject();
				}
				if (size > 7)
				{
					pbackColorSelected = PyTuple_GET_ITEM(item, 7);
					if (pbackColorSelected == Py_None)
						pbackColorSelected=ePyObject();
				}

				eRect rect(x, y, width, height);
				painter.clip(rect);
				if (pbackColor || pbackColorSelected)
				{
					gRegion rc(rect);
					clearRegion(painter, style, local_style, ePyObject(), pbackColor, pbackColorSelected, selected, rc, sel_clip);
					reset_colors=true;
				}
				
				painter.blit(pixmap, rect.topLeft(), rect, (type == TYPE_PIXMAP_ALPHATEST) ? gPainter::BT_ALPHATEST : 0);
				painter.clippop();
				break;
			}
			default:
				eWarning("eListboxPythonMultiContent received unknown type (%d)", type);
				goto error_out;
			}
			if (reset_colors)
				style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
		}
	}

	if (selected)
		style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);

error_out:
	if (m_buildFunc && PyCallable_Check(m_buildFunc) && items)
		Py_DECREF(items);

	painter.clippop();
}

void eListboxPythonMultiContent::setBuildFunc(ePyObject cb)
{
	Py_XDECREF(m_buildFunc);
	m_buildFunc=cb;
	Py_XINCREF(m_buildFunc);
}

void eListboxPythonMultiContent::setSelectableFunc(ePyObject cb)
{
	Py_XDECREF(m_selectableFunc);
	m_selectableFunc=cb;
	Py_XINCREF(m_selectableFunc);
}

int eListboxPythonMultiContent::currentCursorSelectable()
{
	/* each list-entry is a list of tuples. if the first of these is none, it's not selectable */
	if (m_list && cursorValid())
	{
		if (m_selectableFunc && PyCallable_Check(m_selectableFunc))
		{
			ePyObject args = PyList_GET_ITEM(m_list, m_cursor); // borrowed reference!
			if (PyTuple_Check(args))
			{
				ePyObject ret = PyObject_CallObject(m_selectableFunc, args);
				if (ret)
					return ret == Py_True;
				eDebug("call m_selectableFunc failed!!! assume not callable");
			}
			else
				eDebug("m_list[m_cursor] is not a tuple!!! assume not callable");
		}
		else
		{
			ePyObject item = PyList_GET_ITEM(m_list, m_cursor);
			if (PyList_Check(item))
			{
				item = PyList_GET_ITEM(item, 0);
				if (item != Py_None)
					return 1;
			}
			else if (m_buildFunc && PyCallable_Check(m_buildFunc))
				return 1;
		}
	}
	return 0;
}

void eListboxPythonMultiContent::setFont(int fnt, gFont *font)
{
	if (font)
		m_font[fnt] = font;
	else
		m_font.erase(fnt);
}

void eListboxPythonMultiContent::setItemHeight(int height)
{
	m_itemheight = height;
	if (m_listbox)
		m_listbox->setItemHeight(height);
}

void eListboxPythonMultiContent::setList(ePyObject list)
{
	m_old_clip = m_clip = gRegion::invalidRegion();
	eListboxPythonStringContent::setList(list);
}

void eListboxPythonMultiContent::updateClip(gRegion &clip)
{
	if (m_clip.valid())
	{
		clip &= m_clip;
		if (m_old_clip.valid() && !(m_clip-m_old_clip).empty())
			m_clip -= m_old_clip;
		m_old_clip = m_clip;
	}
	else
		m_old_clip = m_clip = gRegion::invalidRegion();
}
