#include <lib/components/listboxepg.h>
#include <lib/dvb/epgcache.h>
#include <lib/service/service.h>

void eListboxEPGContent::setRoot(const eServiceReference &root)
{
	eEPGCache *epg=eEPGCache::getInstance();
	if ( epg )
	{
		m_list.clear();
		m_root = root;

		epg->Lock();
		if (!epg->startTimeQuery(root))
		{
			ePtr<eServiceEvent> ptr;
			while( !epg->getNextTimeEntry(ptr) )
				m_list.push_back(ptr);
		}
		else
			eDebug("startTimeQuery failed %s", root.toString().c_str());
		epg->Unlock();

		m_size = m_list.size();
		cursorHome();

		if (m_listbox)
			m_listbox->entryReset();
	}
}

RESULT eListboxEPGContent::getCurrent(ePtr<eServiceEvent> &evt)
{
	if (cursorValid())
	{
		evt = *m_cursor;
		return 0;
	}
	else
		evt = 0;
	return -1;
}

void eListboxEPGContent::setElementPosition(int element, eRect where)
{
	if ((element >= 0) && (element < celElements))
		m_element_position[element] = where;
}

void eListboxEPGContent::setElementFont(int element, gFont *font)
{
	if ((element >= 0) && (element < celElements))
		m_element_font[element] = font;
}

void eListboxEPGContent::sort()
{
#if 0
	ePtr<iListableService> lst;
	if (!m_service_center->list(m_root, lst))
	{
		m_list.sort(iListableServiceCompare(lst));
			/* FIXME: is this really required or can we somehow keep the current entry? */
		cursorHome();
		if (m_listbox)
			m_listbox->entryReset();
	}
#endif
}

DEFINE_REF(eListboxEPGContent);

eListboxEPGContent::eListboxEPGContent()
	:m_size(0)
{
	cursorHome();
}

void eListboxEPGContent::cursorHome()
{
	m_cursor = m_list.begin();
	m_cursor_number = 0;
}

void eListboxEPGContent::cursorEnd()
{
	m_cursor = m_list.end();
	m_cursor_number = m_size;
}

int eListboxEPGContent::cursorMove(int count)
{
	list::iterator old = m_cursor;

	if (count > 0)
	{
		while(count && (m_cursor != m_list.end()))
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

int eListboxEPGContent::cursorValid()
{
	return m_cursor != m_list.end();
}

int eListboxEPGContent::cursorSet(int n)
{
	cursorHome();
	cursorMove(n);

	return 0;
}

int eListboxEPGContent::cursorGet()
{
	return m_cursor_number;
}

void eListboxEPGContent::cursorSave()
{
	m_saved_cursor = m_cursor;
	m_saved_cursor_number = m_cursor_number;
}

void eListboxEPGContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
	m_cursor_number = m_saved_cursor_number;
	m_saved_cursor = m_list.end();
}

int eListboxEPGContent::size()
{
	return m_size;
}

void eListboxEPGContent::setSize(const eSize &size)
{
	m_itemsize = size;
	eSize s = m_itemsize;
	s.setWidth(size.width()/20*5);
	m_element_position[celBeginTime] = eRect(ePoint(0, 0), s);
	m_element_font[celBeginTime] = new gFont("Arial", 22);
	s.setWidth(size.width()/20*15);
	m_element_position[celTitle] = eRect(ePoint(size.width()/20*5, 0), s);
	m_element_font[celTitle] = new gFont("Arial", 22);
}

void eListboxEPGContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	painter.clip(eRect(offset, m_itemsize));
	style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	painter.clear();

	if (cursorValid())
	{
		for (int e = 0; e < celElements; ++e)
		{
			if (!m_element_font[e])
				continue;

			painter.setFont(m_element_font[e]);

			std::string text = "<n/a>";

			switch (e)
			{
			case celBeginTime:
			{
				text=(*m_cursor)->getBeginTimeString();
				break;
			}
			case celTitle:
			{
				text = (*m_cursor)->m_event_name;
				break;
			}
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

