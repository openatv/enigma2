/*
Copyright (c) 2023-2025 jbleyel

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.
*/

#include <lib/base/wrappers.h>
#include <lib/base/esimpleconfig.h>
#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/service/elistboxservicecontent.h>
#include <lib/service/service.h>
#include <lib/gdi/font.h>
#include <lib/gdi/epng.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/db.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/idvb.h>
#include <lib/nav/core.h>
#include <lib/python/connections.h>
#include <lib/python/python.h>
#include <ctype.h>

void eListboxPythonServiceContent::addService(const eServiceReference &service, bool beforeCurrent)
{
	if (beforeCurrent && m_size)
		m_service_list.insert(m_service_cursor, service);
	else
		m_service_list.push_back(service);
	if (m_size++)
	{
		++m_cursor;
		if (m_listbox)
			m_listbox->entryAdded(cursorResolve(m_cursor - 1));
	}
	else
	{
		m_service_cursor = m_service_list.begin();
		m_cursor = 0;
		m_listbox->entryAdded(0);
	}
}

void eListboxPythonServiceContent::removeCurrent()
{
	if (m_size && m_listbox)
	{
		if (m_cursor == --m_size)
		{
			m_service_list.erase(m_service_cursor--);
			if (m_size)
			{
				--m_cursor;
				m_listbox->entryRemoved(cursorResolve(m_cursor + 1));
			}
			else
				m_listbox->entryRemoved(cursorResolve(m_cursor));
		}
		else
		{
			m_service_list.erase(m_service_cursor++);
			m_listbox->entryRemoved(cursorResolve(m_cursor));
		}
		// prevent a crash in case we are deleting an marked item while in move mode
		m_current_marked = false;
	}
}

void eListboxPythonServiceContent::FillFinished()
{
	m_size = m_service_list.size();
	cursorHome();

	if (m_listbox)
		m_listbox->entryReset();
}

void eListboxPythonServiceContent::setRoot(const eServiceReference &root, bool justSet)
{
	m_service_list.clear();
	m_service_cursor = m_service_list.end();
	m_root = root;

	if (justSet)
	{
		m_lst = 0;
		return;
	}
	ASSERT(m_service_center);

	if (m_service_center->list(m_root, m_lst))
		eDebug("[eListboxPythonServiceContent] no list available!");
	else if (m_lst->getContent(m_service_list))
		eDebug("[eListboxPythonServiceContent] getContent failed");

	FillFinished();
}

bool eListboxPythonServiceContent::setCurrent(const eServiceReference &ref)
{
	int index = 0;
	for (list::iterator i(m_service_list.begin()); i != m_service_list.end(); ++i, ++index)
	{
		if (*i == ref)
		{
			m_service_cursor = i;
			m_cursor = index;
			if (m_listbox)
			{
				m_listbox->moveSelectionTo(cursorResolve(index));
				return true;
			}
			break;
		}
	}
	return false;
}

void eListboxPythonServiceContent::getCurrent(eServiceReference &ref)
{
	if (cursorValid())
		ref = *m_service_cursor;
	else
		ref = eServiceReference();
}

void eListboxPythonServiceContent::getPrev(eServiceReference &ref)
{
	if (cursorValid())
	{
		list::iterator cursor(m_service_cursor);
		if (cursor == m_service_list.begin())
		{
			cursor = m_service_list.end();
		}
		ref = *(--cursor);
	}
	else
		ref = eServiceReference();
}

void eListboxPythonServiceContent::getNext(eServiceReference &ref)
{
	if (cursorValid())
	{
		list::iterator cursor(m_service_cursor);
		cursor++;
		if (cursor == m_service_list.end())
		{
			cursor = m_service_list.begin();
		}
		ref = *(cursor);
	}
	else
		ref = eServiceReference();
}

PyObject *eListboxPythonServiceContent::getList()
{
	ePyObject result = PyList_New(m_service_list.size());
	int pos=0;
	for (list::iterator it(m_service_list.begin()); it != m_service_list.end(); ++it)
	{
		PyList_SET_ITEM(result, pos++, NEW_eServiceReference(*it));
	}
	return result;
}

int eListboxPythonServiceContent::getNextBeginningWithChar(char c)
{
	//	printf("Char: %c\n", c);
	int index = 0;
	for (list::iterator i(m_service_list.begin()); i != m_service_list.end(); ++i, ++index)
	{
		std::string text;
		ePtr<iStaticServiceInformation> service_info;
		if (m_service_center->info(*i, service_info))
		{
			continue; // failed to find service handler
		}
		service_info->getName(*i, text);
		//		printf("%c\n", text.c_str()[0]);
		int idx = 0;
		int len = text.length();
		while (idx <= len)
		{
			char cc = text[idx++];
			if (isprint(cc))
			{
				if (cc == c)
					return index;
				break;
			}
		}
	}
	return 0;
}

int eListboxPythonServiceContent::getPrevMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_service_cursor);
	int index = m_cursor;
	// if the search is starting part way through a section return to the start of the current section
	while (index)
	{
		--i;
		--index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}

	// if the search started from part way through the current section return now because this is the previous visible marker
	if (cursorResolve(index) + 1 != cursorResolve(m_cursor))
		return cursorResolve(index);

	// search for visible marker index of previous section
	while (index)
	{
		--i;
		--index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}

	return cursorResolve(index);
}

int eListboxPythonServiceContent::getNextMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_service_cursor);
	int index = m_cursor;
	while (index < (m_size - 1))
	{
		++i;
		++index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}
	return cursorResolve(index);
}

void eListboxPythonServiceContent::initMarked()
{
	m_marked.clear();
}

void eListboxPythonServiceContent::addMarked(const eServiceReference &ref)
{
	m_marked.insert(ref);
	if (m_listbox)
		m_listbox->entryChanged(cursorResolve(lookupService(ref)));
}

void eListboxPythonServiceContent::removeMarked(const eServiceReference &ref)
{
	m_marked.erase(ref);
	if (m_listbox)
		m_listbox->entryChanged(cursorResolve(lookupService(ref)));
}

int eListboxPythonServiceContent::isMarked(const eServiceReference &ref)
{
	return m_marked.find(ref) != m_marked.end();
}

void eListboxPythonServiceContent::markedQueryStart()
{
	m_marked_iterator = m_marked.begin();
}

int eListboxPythonServiceContent::markedQueryNext(eServiceReference &ref)
{
	if (m_marked_iterator == m_marked.end())
		return -1;
	ref = *m_marked_iterator++;
	return 0;
}

int eListboxPythonServiceContent::lookupService(const eServiceReference &ref)
{
	/* shortcut for cursor */
	if (ref == *m_service_cursor)
		return m_cursor;
	/* otherwise, search in the list.. */
	int index = 0;
	for (list::const_iterator i(m_service_list.begin()); i != m_service_list.end(); ++i, ++index);

	/* this is ok even when the index was not found. */
	return index;
}

void eListboxPythonServiceContent::sort()
{
	if (!m_lst)
		m_service_center->list(m_root, m_lst);
	if (m_lst)
	{
		m_service_list.sort(iListableServiceCompare(m_lst));
		/* FIXME: is this really required or can we somehow keep the current entry? */
		cursorHome();
		if (m_listbox)
			m_listbox->entryReset();
	}
}

void eListboxPythonServiceContent::swapServices(list::iterator a, list::iterator b)
{
	std::iter_swap(a, b);
	if(m_numbering_mode !=2 )
	{
		int temp = a->getChannelNum();
		a->setChannelNum(b->getChannelNum());
		b->setChannelNum(temp);
	}
}

bool eListboxPythonServiceContent::isServiceHidden(int flags)
{
	return (flags & eServiceReference::isInvisible) || (m_marked.empty() && m_hide_number_marker && (flags & eServiceReference::isNumberedMarker)) || (m_marked.empty() && m_hide_marker && (flags & eServiceReference::isMarker));
}

void eListboxPythonServiceContent::cursorHome()
{
	if (m_current_marked && m_saved_service_cursor == m_service_list.end())
	{
		if (m_cursor >= m_size)
		{
			m_cursor = m_size - 1;
			--m_service_cursor;
		}
		while (m_cursor)
		{
			swapServices(m_service_cursor--, m_service_cursor);
			--m_cursor;
			if (m_listbox && m_cursor)
				m_listbox->entryChanged(cursorResolve(m_cursor));
		}
	}
	else
	{
		m_service_cursor = m_service_list.begin();
		m_cursor = 0;
		while (m_service_cursor != m_service_list.end())
		{
			if (!isServiceHidden(m_service_cursor->flags))
				break;
			m_service_cursor++;
			m_cursor++;
		}
	}
}

void eListboxPythonServiceContent::cursorEnd()
{
	if (m_current_marked && m_saved_service_cursor == m_service_list.end())
	{
		while (m_service_cursor != m_service_list.end())
		{
			list::iterator prev = m_service_cursor++;
			++m_cursor;
			if (prev != m_service_list.end() && m_service_cursor != m_service_list.end())
			{
				swapServices(m_service_cursor, prev);
				if (m_listbox)
					m_listbox->entryChanged(cursorResolve(m_cursor));
			}
		}
	}
	else
	{
		m_service_cursor = m_service_list.end();
		m_cursor = m_size;
	}
}

int eListboxPythonServiceContent::setCurrentMarked(bool state)
{
	bool prev = m_current_marked;
	m_current_marked = state;

	if (state != prev && m_listbox)
	{
		m_listbox->entryChanged(cursorResolve(m_cursor));
		if (!state)
		{
			if (!m_lst)
				m_service_center->list(m_root, m_lst);
			if (m_lst)
			{
				ePtr<iMutableServiceList> list;
				if (m_lst->startEdit(list))
					eDebug("[eListboxPythonServiceContent] no editable list");
				else
				{
					eServiceReference ref;
					getCurrent(ref);
					if (!ref)
						eDebug("[eListboxPythonServiceContent] no valid service selected");
					else
					{
						int pos = cursorGet();
						eDebugNoNewLineStart("[eListboxPythonServiceContent] move %s to %d ", ref.toString().c_str(), pos);
						if (list->moveService(ref, cursorGet()))
							eDebugNoNewLine("failed\n");
						else
							eDebugNoNewLine("ok\n");
					}
				}
			}
			else
				eDebug("[eListboxPythonServiceContent] no list available!");
		}
	}

	return 0;
}

bool eListboxPythonServiceContent::isCurrentMarked()
{
	return m_current_marked;
}
int eListboxPythonServiceContent::cursorMove(int count)
{
	int prev = m_cursor, last = m_cursor + count;
	if (count > 0)
	{
		while (count && m_service_cursor != m_service_list.end())
		{
			list::iterator prev_it = m_service_cursor++;
			if (m_current_marked && m_service_cursor != m_service_list.end() && m_saved_service_cursor == m_service_list.end())
			{
				swapServices(prev_it, m_service_cursor);
				if (m_listbox && prev != m_cursor && last != m_cursor)
					m_listbox->entryChanged(cursorResolve(m_cursor));
			}
			++m_cursor;
			if (!isServiceHidden(m_service_cursor->flags))
				--count;
		}
	}
	else if (count < 0)
	{
		while (count && m_service_cursor != m_service_list.begin())
		{
			list::iterator prev_it = m_service_cursor--;
			if (m_current_marked && m_service_cursor != m_service_list.end() && prev_it != m_service_list.end() && m_saved_service_cursor == m_service_list.end())
			{
				swapServices(prev_it, m_service_cursor);
				if (m_listbox && prev != m_cursor && last != m_cursor)
					m_listbox->entryChanged(cursorResolve(m_cursor));
			}
			--m_cursor;
			if (!isServiceHidden(m_service_cursor->flags))
				++count;
		}
		while (m_service_cursor != m_service_list.end())
		{
			if (!isServiceHidden(m_service_cursor->flags))
				break;
			m_service_cursor++;
			m_cursor++;
		}
	}
	return 0;
}

int eListboxPythonServiceContent::cursorValid()
{
	return m_service_cursor != m_service_list.end();
}

int eListboxPythonServiceContent::cursorSet(int n)
{
	cursorHome();
	cursorMove(n);
	return 0;
}

int eListboxPythonServiceContent::cursorResolve(int cursor_position)
{
	int m_stripped_cursor = 0;
	int count = 0;
	for (list::iterator i(m_service_list.begin()); i != m_service_list.end(); ++i)
	{
		if (count == cursor_position)
			break;

		count++;

		if (isServiceHidden(i->flags))
			continue;
		m_stripped_cursor++;
	}

	return m_stripped_cursor;
}

int eListboxPythonServiceContent::cursorGet()
{
	return cursorResolve(m_cursor);
}

int eListboxPythonServiceContent::currentCursorSelectable()
{
	if (cursorValid())
	{
		/* don't allow markers to be selected, unless we're in edit mode (because we want to provide some method to the user to remove a marker) */
		if (m_service_cursor->flags & eServiceReference::isMarker && m_marked.empty())
			return 0;
		else
			return 1;
	}
	return 0;
}

void eListboxPythonServiceContent::cursorSave()
{
	m_saved_service_cursor = m_service_cursor;
	m_saved_cursor = m_cursor;
}

void eListboxPythonServiceContent::cursorRestore()
{
	m_service_cursor = m_saved_service_cursor;
	m_cursor = m_saved_cursor;
	m_saved_service_cursor = m_service_list.end();
}

int eListboxPythonServiceContent::size()
{
	int size = 0;
	for (list::iterator i(m_service_list.begin()); i != m_service_list.end(); ++i)
	{
		if (isServiceHidden(i->flags))
			continue;
		size++;
	}

	return size;
}

RESULT SwigFromPython(ePtr<gPixmap> &res, PyObject *obj);

DEFINE_REF(eListboxPythonServiceContent);

eListboxPythonServiceContent::eListboxPythonServiceContent()
	: m_size(0), m_current_marked(false), m_hide_number_marker(false), m_hide_marker(false), m_record_indicator_mode(0)
{
	m_numbering_mode = eSimpleConfig::getInt("config.usage.numberMode", 0);
	cursorHome();
	eServiceCenter::getInstance(m_service_center);
	m_servicelist = true;
}

inline bool compareServices(const eServiceReference &src, const eServiceReference &trg)
{
	return (src.toString() == trg.alternativeurl);
}

bool eListboxPythonServiceContent::checkServiceIsRecorded(eServiceReference ref, pNavigation::RecordType type)
{

	const bool isGroup = ref.flags & eServiceReference::isGroup;

	eBouquet *bouquet = nullptr;
	if (isGroup)
	{
		static ePtr<eDVBResourceManager> res = nullptr;
		if (!res)
			eDVBResourceManager::getInstance(res);
		if (res)
		{
			ePtr<iDVBChannelList> db;
			res->getChannelList(db);
			if (db)
				db->getBouquet(ref, bouquet);
		}
		if (!bouquet)
			return false;
	}

	std::vector<eServiceReference> recordedServices;
	eNavigation::getInstance()->getRecordingsServicesOnly(recordedServices, type);

	if (!recordedServices.empty())
	{
		if (isGroup)
		{
			for (const auto &service : bouquet->m_services)
			{
				for (const auto &recordedService : recordedServices)
				{
					if (service == recordedService || compareServices(service, recordedService))
						return true;
				}
			}
		}
		else
		{
			for (const auto &recordedService : recordedServices)
			{
				if (ref == recordedService || compareServices(ref, recordedService))
					return true;
			}
		}
	}

	if (type & pNavigation::isStreaming)
	{
		const auto &streamServices = eNavigation::getInstance()->getStreamServiceList();
		if (!streamServices.empty())
		{
			const std::string refString = ref.toString();

			if (isGroup)
			{
				for (const auto &service : bouquet->m_services)
				{
					if (std::find(streamServices.begin(), streamServices.end(),service.toString()) != streamServices.end())
						return true;
				}
			}
			else
			{
				if (std::find(streamServices.begin(), streamServices.end(),refString) != streamServices.end())
					return true;
			}
		}
	}
	return false;
}

bool eListboxPythonServiceContent::getIsMarked(int selected)
{
	return ((m_current_marked && selected) || (cursorValid() && isMarked(*m_service_cursor)));
}

void eListboxPythonServiceContent::setBuildArgs(int selected)
{
	eServiceReference &ref = *m_service_cursor;
	bool isSelected = selected > 0;
	bool isFolder = ref.flags & eServiceReference::isDirectory;
	bool isMarker = ref.flags & eServiceReference::isMarker;
	bool isPlayable = !(isFolder || isMarker);
	bool isRecorded = m_record_indicator_mode && isPlayable && checkServiceIsRecorded(ref, pNavigation::RecordType(pNavigation::isRealRecording | pNavigation::isUnknownRecording));
	bool isStreamed = m_record_indicator_mode && isPlayable && checkServiceIsRecorded(ref, pNavigation::isStreaming);
	bool isPseudoRecorded = m_record_indicator_mode && isPlayable && checkServiceIsRecorded(ref, pNavigation::isPseudoRecording);
	bool marked = ((m_current_marked && isSelected) || (cursorValid() && isMarked(*m_service_cursor)));
	bool isinBouquet = ref.flags & eDVBService::dxIntIsinBouquet;

	// status bitmask
	// 1 selected
	// 2 marked
	// 4 isMarker
	// 8 isPlayable
	// 16 isRecorded
	// 32 isStreamed
	// 64 isPseudoRecorded
	// 128 isFolder
	// 256 isinBouquet

	int status = (isSelected << 0) + (marked << 1) + (isMarker << 2) + (isPlayable << 3) + (isRecorded << 4) + (isStreamed << 5) + (isPseudoRecorded << 6) + (isFolder << 7) + (isinBouquet << 8);

	m_pArgs = PyTuple_New(2);
	PyTuple_SET_ITEM(m_pArgs, 0, NEW_eServiceReference(ref));
	PyTuple_SET_ITEM(m_pArgs, 1, PyInt_FromLong(status));
}

void eListboxPythonServiceContent::refresh()
{
	if (m_listbox)
		m_listbox->moveSelection(m_listbox->refresh);
}
