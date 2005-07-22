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

DEFINE_REF(eListboxServiceContent);

eListboxServiceContent::eListboxServiceContent()
{
	m_size = 0;
	cursorHome();
	eServiceCenter::getInstance(m_service_center);
}

void eListboxServiceContent::cursorHome()
{
	m_cursor = m_list.begin();
	m_cursor_number = 0;
}

void eListboxServiceContent::cursorEnd()
{
	m_cursor = m_list.end();
	m_cursor_number = m_size;
}

int eListboxServiceContent::cursorMove(int count)
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
}

int eListboxServiceContent::size()
{
	return m_size;
}
	
void eListboxServiceContent::setSize(const eSize &size)
{
	m_itemsize = size;
}

void eListboxServiceContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	ePtr<gFont> fnt = new gFont("Arial", 14);
	painter.clip(eRect(offset, m_itemsize));
	if (cursorValid() && isMarked(*m_cursor))
		style.setStyle(painter, eWindowStyle::styleListboxMarked);
	else
		style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);
	painter.clear();
	
	if (cursorValid())
	{
		painter.setFont(fnt);
		
		ePoint text_offset = offset + (selected ? ePoint(2, 2) : ePoint(1, 1));
		
			/* get name of service */
		ePtr<iStaticServiceInformation> service_info;
		m_service_center->info(*m_cursor, service_info);
		std::string name = "<n/a>";
		
		if (service_info)
			service_info->getName(*m_cursor, name);
		
		painter.renderText(eRect(text_offset, m_itemsize), name);
		
		if (selected)
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
	}
	
	painter.clippop();
}

