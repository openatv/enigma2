#include <lib/service/listboxservice.h>
#include <lib/service/service.h>

void eListboxServiceContent::setRoot(const eServiceReference &root)
{
	m_list.clear();
	m_root = root;
	
	assert(m_service_center);
	
	ePtr<iListableService> lst;
	if (m_service_center->list(m_root, lst))
		eDebug("no list available!");
	else
		if (lst->getContent(m_list))
			eDebug("getContent failed");

	m_size = m_list.size();
	cursorHome();
	
	if (m_listbox)
		m_listbox->entryReset();
}

void eListboxServiceContent::setCurrent(const eServiceReference &ref)
{
	int index=0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i, ++index)
		if ( *i == ref )
		{
			m_cursor = i;
			m_cursor_number = index;
			break;
		}
}

void eListboxServiceContent::getCurrent(eServiceReference &ref)
{
	if (cursorValid())
		ref = *m_cursor;
	else
		ref = eServiceReference();
}

void eListboxServiceContent::initMarked()
{
	m_marked.clear();
}

void eListboxServiceContent::addMarked(const eServiceReference &ref)
{
	m_marked.insert(ref);
	if (m_listbox)
		m_listbox->entryChanged(lookupService(ref));
}

void eListboxServiceContent::removeMarked(const eServiceReference &ref)
{
	m_marked.erase(ref);
	if (m_listbox)
		m_listbox->entryChanged(lookupService(ref));
}

int eListboxServiceContent::isMarked(const eServiceReference &ref)
{
	return m_marked.find(ref) != m_marked.end();
}

void eListboxServiceContent::markedQueryStart()
{
	m_marked_iterator = m_marked.begin();
}

int eListboxServiceContent::markedQueryNext(eServiceReference &ref)
{
	if (m_marked_iterator == m_marked.end())
		return -1;
	ref = *m_marked_iterator++;
	return 0;
}

int eListboxServiceContent::lookupService(const eServiceReference &ref)
{
		/* shortcut for cursor */
	if (ref == *m_cursor)
		return m_cursor_number;
		/* otherwise, search in the list.. */
	int index = 0;
	for (list::const_iterator i(m_list.begin()); i != m_list.end(); ++i, ++index);
	
		/* this is ok even when the index was not found. */
	return index;
}

void eListboxServiceContent::setVisualMode(int mode)
{
	m_visual_mode = mode;
	
	if (m_visual_mode == visModeSimple)
	{
		m_element_position[celServiceName] = eRect(ePoint(0, 0), m_itemsize);
		m_element_font[celServiceName] = new gFont("Arial", 23);
		m_element_position[celServiceNumber] = eRect();
		m_element_font[celServiceNumber] = 0;
		m_element_position[celIcon] = eRect();
		m_element_position[celServiceInfo] = eRect();
		m_element_font[celServiceInfo] = 0;
	}
}

void eListboxServiceContent::setElementPosition(int element, eRect where)
{
	if ((element >= 0) && (element < celElements))
		m_element_position[element] = where;
}

void eListboxServiceContent::setElementFont(int element, gFont *font)
{
	if ((element >= 0) && (element < celElements))
		m_element_font[element] = font;
}

void eListboxServiceContent::sort()
{
	ePtr<iListableService> lst;
  if (!m_service_center->list(m_root, lst))
  {
		m_list.sort(iListableServiceCompare(lst));
			/* FIXME: is this really required or can we somehow keep the current entry? */
		cursorHome();
		if (m_listbox)
			m_listbox->entryReset();
	}
}

DEFINE_REF(eListboxServiceContent);

eListboxServiceContent::eListboxServiceContent()
	:m_visual_mode(visModeSimple), m_size(0), m_current_marked(false), m_numberoffset(0)
{
	cursorHome();
	eServiceCenter::getInstance(m_service_center);
}

void eListboxServiceContent::cursorHome()
{
	if (m_current_marked && m_saved_cursor == m_list.end())
	{
		while (m_cursor_number)
		{
			std::iter_swap(m_cursor--, m_cursor);
			--m_cursor_number;
			if (m_listbox && m_cursor_number)
				m_listbox->entryChanged(m_cursor_number);
		}
	}
	else
	{
		m_cursor = m_list.begin();
		m_cursor_number = 0;
	}
}

void eListboxServiceContent::cursorEnd()
{
	if (m_current_marked && m_saved_cursor == m_list.end())
	{
		while (m_cursor != m_list.end())
		{
			list::iterator prev = m_cursor++;
			++m_cursor_number;
			if ( prev != m_list.end() && m_cursor != m_list.end() )
			{
				std::iter_swap(m_cursor, prev);
				if ( m_listbox )
					m_listbox->entryChanged(m_cursor_number);
			}
		}
	}
	else
	{
		m_cursor = m_list.end();
		m_cursor_number = m_size;
	}
}

int eListboxServiceContent::setCurrentMarked(bool state)
{
	bool prev = m_current_marked;
	m_current_marked = state;

	if (state != prev && m_listbox)
	{
		m_listbox->entryChanged(m_cursor_number);
		if (!state)
		{
			ePtr<iListableService> lst;
			if (m_service_center->list(m_root, lst))
				eDebug("no list available!");
			else
			{
				ePtr<iMutableServiceList> list;
				if (lst->startEdit(list))
					eDebug("no editable list");
				else
				{
					eServiceReference ref;
					getCurrent(ref);
					if(!ref)
						eDebug("no valid service selected");
					else
					{
						int pos = cursorGet();
						eDebugNoNewLine("move %s to %d ", ref.toString().c_str(), pos);
						if (list->moveService(ref, cursorGet()))
							eDebug("failed");
						else
							eDebug("ok");
					}
				}
			}
		}
	}

	return 0;
}

int eListboxServiceContent::cursorMove(int count)
{
	int prev = m_cursor_number, last = m_cursor_number + count;
	if (count > 0)
	{
		while(count && m_cursor != m_list.end())
		{
			list::iterator prev_it = m_cursor++;
			if ( m_current_marked && m_cursor != m_list.end() && m_saved_cursor == m_list.end() )
			{
				std::iter_swap(prev_it, m_cursor);
				if ( m_listbox && prev != m_cursor_number && last != m_cursor_number )
					m_listbox->entryChanged(m_cursor_number);
			}
			++m_cursor_number;
			--count;
	}
	} else if (count < 0)
	{
		while (count && m_cursor != m_list.begin())
		{
			list::iterator prev_it = m_cursor--;
			if ( m_current_marked && m_cursor != m_list.end() && prev_it != m_list.end() && m_saved_cursor == m_list.end() )
			{
				std::iter_swap(prev_it, m_cursor);
				if ( m_listbox && prev != m_cursor_number && last != m_cursor_number )
					m_listbox->entryChanged(m_cursor_number);
			}
			--m_cursor_number;
			++count;
		}
	}
	return 0;
}

int eListboxServiceContent::cursorValid()
{
	return m_cursor != m_list.end();
}

int eListboxServiceContent::cursorSet(int n)
{
	cursorHome();
	cursorMove(n);
	
	return 0;
}

int eListboxServiceContent::cursorGet()
{
	return m_cursor_number;
}

void eListboxServiceContent::cursorSave()
{
	m_saved_cursor = m_cursor;
	m_saved_cursor_number = m_cursor_number;
}

void eListboxServiceContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
	m_cursor_number = m_saved_cursor_number;
	m_saved_cursor = m_list.end();
}

int eListboxServiceContent::size()
{
	return m_size;
}
	
void eListboxServiceContent::setSize(const eSize &size)
{
	m_itemsize = size;
	setVisualMode(m_visual_mode);
}

void eListboxServiceContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	painter.clip(eRect(offset, m_itemsize));

	if (m_current_marked && selected)
		style.setStyle(painter, eWindowStyle::styleListboxMarked);
	else if (cursorValid() && isMarked(*m_cursor))
		style.setStyle(painter, eWindowStyle::styleListboxMarked);
	else
		style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	painter.clear();
	
	if (cursorValid())
	{
			/* get service information */
		ePtr<iStaticServiceInformation> service_info;
		m_service_center->info(*m_cursor, service_info);
		
		for (int e = 0; e < celElements; ++e)
		{
			if (!m_element_font[e])
				continue;
			painter.setFont(m_element_font[e]);
			
			std::string text = "<n/a>";
			
			switch (e)
			{
			case celServiceName:
			{
				if (service_info)
					service_info->getName(*m_cursor, text);
				break;
			}
			case celServiceNumber:
			{
				char bla[10];
				sprintf(bla, "%d", m_numberoffset + m_cursor_number + 1);
				text = bla;
				break;
			}
			case celServiceInfo:
			{
				text = "now&next";
				break;
			}
			case celIcon:
				continue;
			}
			
			eRect area = m_element_position[e];
			area.moveBy(offset.x(), offset.y());
			
			painter.renderText(area, text);
		}
		
		if (selected)
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
	}
	
	painter.clippop();
}

