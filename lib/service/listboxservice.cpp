#include <lib/service/listboxservice.h>
#include <lib/service/service.h>

void eListboxServiceContent::setRoot(const eServiceReference &root)
{
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
}

void eListboxServiceContent::getCurrent(eServiceReference &ref)
{
	if (cursorValid())
		ref = *m_cursor;
	else
		ref = eServiceReference();
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

