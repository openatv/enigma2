#include <lib/service/listboxservice.h>
#include <lib/service/service.h>
#include <lib/gdi/font.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/pmt.h>
#include <lib/python/connections.h>

void eListboxServiceContent::addService(const eServiceReference &service)
{
	m_list.push_back(service);
}

void eListboxServiceContent::FillFinished()
{
	m_size = m_list.size();
	cursorHome();

	if (m_listbox)
		m_listbox->entryReset();
}

void eListboxServiceContent::setRoot(const eServiceReference &root, bool justSet)
{
	m_list.clear();
	m_root = root;

	if (justSet)
		return;
	assert(m_service_center);
	
	ePtr<iListableService> lst;
	if (m_service_center->list(m_root, lst))
		eDebug("no list available!");
	else
		if (lst->getContent(m_list))
			eDebug("getContent failed");

	FillFinished();
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
	if (m_listbox)
		m_listbox->moveSelectionTo(index);
}

void eListboxServiceContent::getCurrent(eServiceReference &ref)
{
	if (cursorValid())
		ref = *m_cursor;
	else
		ref = eServiceReference();
}

int eListboxServiceContent::getNextBeginningWithChar(char c)
{
//	printf("Char: %c\n", c);
	int index=0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i, ++index)
	{
		std::string text;
		ePtr<iStaticServiceInformation> service_info;
		m_service_center->info(*i, service_info);
		service_info->getName(*i, text);
//		printf("%c\n", text.c_str()[0]);
		int idx=0;
		int len=text.length();
		while ( idx <= len )
		{
			char cc = text[idx++];
			if ( cc >= 33 && cc < 127)
			{
				if (cc == c)
					return index;
				break;
			}
		}
	}
	return 0;
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
		m_element_font[celServiceName] = new gFont("Regular", 23);
		m_element_position[celServiceNumber] = eRect();
		m_element_font[celServiceNumber] = 0;
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

void eListboxServiceContent::setPixmap(int type, ePtr<gPixmap> &pic)
{
	if ((type >=0) && (type < picElements))
		m_pixmaps[type] = pic;
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
		if (m_cursor_number >= m_size)
		{
			m_cursor_number = m_size-1;
			--m_cursor;
		}
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
		style.setStyle(painter, selected ? eWindowStyle::styleListboxMarkedAndSelected : eWindowStyle::styleListboxMarked);
	else
		style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	painter.clear();
	
	if (cursorValid())
	{
			/* get service information */
		ePtr<iStaticServiceInformation> service_info;
		m_service_center->info(*m_cursor, service_info);

		if (m_is_playable_ignore.valid() && service_info && !service_info->isPlayable(*m_cursor, m_is_playable_ignore))
			painter.setForegroundColor(gRGB(0xbbbbbb));

		int xoffset=0;  // used as offset when painting the folder symbol

		for (int e = 0; e < celElements; ++e)
		{
			if (m_element_font[e])
			{
				int flags=gPainter::RT_VALIGN_CENTER,
					yoffs = 0,
					xoffs = xoffset;
				eRect &area = m_element_position[e];
				std::string text = "<n/a>";
				xoffset=0;

				switch (e)
				{
				case celServiceNumber:
				{
					char bla[10];
					sprintf(bla, "%d", m_numberoffset + m_cursor_number + 1);
					text = bla;
					flags|=gPainter::RT_HALIGN_RIGHT;
					break;
				}
				case celServiceName:
				{
					if (service_info)
						service_info->getName(*m_cursor, text);
					break;
				}
				case celServiceInfo:
				{
					ePtr<eServiceEvent> evt;
					if ( !service_info->getEvent(*m_cursor, evt) )
					{
						std::string name = evt->getEventName();
						if (!name.length())
							continue;
						text = '(' + evt->getEventName() + ')';
					}
					else
						continue;
					break;
				}
				}

				eRect tmp = area;
				tmp.setWidth(tmp.width()-xoffs);

				eTextPara *para = new eTextPara(tmp);
				para->setFont(m_element_font[e]);
				para->renderString(text);

				if (e == celServiceName)
				{
					eRect bbox = para->getBoundBox();
					int name_width = bbox.width()+8;
					m_element_position[celServiceInfo].setLeft(area.left()+name_width);
					m_element_position[celServiceInfo].setTop(area.top());
					m_element_position[celServiceInfo].setWidth(area.width()-name_width);
					m_element_position[celServiceInfo].setHeight(area.height());
				}

				if (flags & gPainter::RT_HALIGN_RIGHT)
					para->realign(eTextPara::dirRight);
				else if (flags & gPainter::RT_HALIGN_CENTER)
					para->realign(eTextPara::dirCenter);
				else if (flags & gPainter::RT_HALIGN_BLOCK)
					para->realign(eTextPara::dirBlock);

				if (flags & gPainter::RT_VALIGN_CENTER)
				{
					eRect bbox = para->getBoundBox();
					int vcentered_top = (area.height() - bbox.height()) / 2;
					yoffs = vcentered_top - bbox.top();
				}

				painter.renderPara(para, offset+ePoint(xoffs, yoffs));
			}
			else if (e == celServiceTypePixmap || e == celFolderPixmap)
			{
				int orbpos = m_cursor->getUnsignedData(4) >> 16;
				ePtr<gPixmap> &pixmap =
					(e == celFolderPixmap) ? m_pixmaps[picFolder] :
					(orbpos == 0xFFFF) ? m_pixmaps[picDVB_C] :
					(orbpos == 0xEEEE) ? m_pixmaps[picDVB_T] : m_pixmaps[picDVB_S];
				if (pixmap)
				{
					eSize pixmap_size = pixmap->size();
					eRect area = m_element_position[e == celFolderPixmap ? celServiceName : celServiceInfo];
					int correction = (area.height() - pixmap_size.height()) / 2;

					if (m_cursor->flags & eServiceReference::flagDirectory)
					{
						if (e != celFolderPixmap)
							continue;
						xoffset = pixmap_size.width() + 8;
					}
					else
					{
						if (e != celServiceTypePixmap)
							continue;
						m_element_position[celServiceInfo] = area;
						m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + 8);
						m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - 8);
					}

					area.moveBy(offset);
					painter.clip(area);
					painter.blit(pixmap, offset+ePoint(area.left(), correction), area, gPainter::BT_ALPHATEST);
					painter.clippop();
				}
			}
		}
		
		if (selected)
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
	}
	
	painter.clippop();
}

void eListboxServiceContent::setIgnoreService( const eServiceReference &service )
{
	m_is_playable_ignore=service;
}
