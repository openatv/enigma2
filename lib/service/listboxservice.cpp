#include <lib/service/listboxservice.h>
#include <lib/service/service.h>
#include <lib/gdi/font.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/pmt.h>
#include <lib/python/connections.h>

void eListboxServiceContent::addService(const eServiceReference &service, bool beforeCurrent)
{
	if (beforeCurrent && m_size)
		m_list.insert(m_cursor, service);
	else
		m_list.push_back(service);
	if (m_size++)
	{
		++m_cursor_number;
		if (m_listbox)
			m_listbox->entryAdded(m_cursor_number-1);
	}
	else
	{
		m_cursor = m_list.begin();
		m_cursor_number=0;
		m_listbox->entryAdded(0);
	}
}

void eListboxServiceContent::removeCurrent()
{
	if (m_size && m_listbox)
	{
		if (m_cursor_number == --m_size)
		{
			m_list.erase(m_cursor--);
			if (m_size)
			{
				--m_cursor_number;
				m_listbox->entryRemoved(m_cursor_number+1);
			}
			else
				m_listbox->entryRemoved(m_cursor_number);
		}
		else
		{
			m_list.erase(m_cursor++);
			m_listbox->entryRemoved(m_cursor_number);
		}
	}
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
	m_cursor = m_list.end();
	m_root = root;

	if (justSet)
	{
		m_lst=0;
		return;
	}
	ASSERT(m_service_center);
	
	if (m_service_center->list(m_root, m_lst))
		eDebug("no list available!");
	else if (m_lst->getContent(m_list))
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

int eListboxServiceContent::getPrevMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_cursor);
	int index = m_cursor_number;
	while (index) // Skip precending markers
	{
		--i;
		--index;
		if (! (i->flags & eServiceReference::isMarker))
			break;
	}
	while (index)
	{
		--i;
		--index;
		if (i->flags & eServiceReference::isMarker)
			break;
	}
	return index;
}

int eListboxServiceContent::getNextMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_cursor);
	int index = m_cursor_number;
	while (index < (m_size-1))
	{
		++i;
		++index;
		if (i->flags & eServiceReference::isMarker)
			break;
	}
	return index;
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
	for (int i=0; i < celElements; ++i)
	{
		m_element_position[i] = eRect();
		m_element_font[i] = 0;
	}

	m_visual_mode = mode;

	if (m_visual_mode == visModeSimple)
	{
		m_element_position[celServiceName] = eRect(ePoint(0, 0), m_itemsize);
		m_element_font[celServiceName] = new gFont("Regular", 23);
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
	if (!m_lst)
		m_service_center->list(m_root, m_lst);
	if (m_lst)
	{
		m_list.sort(iListableServiceCompare(m_lst));
			/* FIXME: is this really required or can we somehow keep the current entry? */
		cursorHome();
		if (m_listbox)
			m_listbox->entryReset();
	}
}

DEFINE_REF(eListboxServiceContent);

eListboxServiceContent::eListboxServiceContent()
	:m_visual_mode(visModeSimple), m_size(0), m_current_marked(false), m_numberoffset(0), m_itemheight(25)
{
	memset(m_color_set, 0, sizeof(m_color_set));
	cursorHome();
	eServiceCenter::getInstance(m_service_center);
}

void eListboxServiceContent::setColor(int color, gRGB &col)
{
	if ((color >= 0) && (color < colorElements))
	{
		m_color_set[color] = true;
		m_color[color] = col;
	}
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
			if (!m_lst)
				m_service_center->list(m_root, m_lst);
			if (m_lst)
			{
				ePtr<iMutableServiceList> list;
				if (m_lst->startEdit(list))
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
			else
				eDebug("no list available!");
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
	}
	else if (count < 0)
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

int eListboxServiceContent::currentCursorSelectable()
{
	if (cursorValid())
	{
		/* don't allow markers to be selected, unless we're in edit mode (because we want to provide some method to the user to remove a marker) */
		if (m_cursor->flags & eServiceReference::isMarker && m_marked.empty()) return 0;
		return 1;
	}
	return 0;
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
	if (m_visual_mode == visModeSimple)
		setVisualMode(m_visual_mode);
}

void eListboxServiceContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	painter.clip(eRect(offset, m_itemsize));

	int marked = 0;

	if (m_current_marked && selected)
		marked = 2;
	else if (cursorValid() && isMarked(*m_cursor))
	{
		if (selected)
			marked = 2;
		else
			marked = 1;
	}
	else
		style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);

	eListboxStyle *local_style = 0;

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

	if (marked == 1)  // marked
	{
		style.setStyle(painter, eWindowStyle::styleListboxMarked);
		if (m_color_set[markedForeground])
			painter.setForegroundColor(m_color[markedForeground]);
		if (m_color_set[markedBackground])
			painter.setBackgroundColor(m_color[markedBackground]);
	}
	else if (marked == 2) // marked and selected
	{
		style.setStyle(painter, eWindowStyle::styleListboxMarkedAndSelected);
		if (m_color_set[markedForegroundSelected])
			painter.setForegroundColor(m_color[markedForegroundSelected]);
		if (m_color_set[markedBackgroundSelected])
			painter.setBackgroundColor(m_color[markedBackgroundSelected]);
	}
	else if (local_style)
	{
		if (selected)
		{
			/* if we have a local background color set, use that. */
			if (local_style->m_background_color_selected_set)
				painter.setBackgroundColor(local_style->m_background_color_selected);
			/* same for foreground */
			if (local_style->m_foreground_color_selected_set)
				painter.setForegroundColor(local_style->m_foreground_color_selected);
		}
		else
		{
			/* if we have a local background color set, use that. */
			if (local_style->m_background_color_set)
				painter.setBackgroundColor(local_style->m_background_color);
			/* same for foreground */
			if (local_style->m_foreground_color_set)
				painter.setForegroundColor(local_style->m_foreground_color);
		}
	}

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
		if (local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), gPainter::BT_ALPHATEST);
		else if (selected && !local_style->m_selection)
			painter.clear();
	}

	if (cursorValid())
	{
			/* get service information */
		ePtr<iStaticServiceInformation> service_info;
		m_service_center->info(*m_cursor, service_info);
		eServiceReference ref = *m_cursor;
		bool isMarker = ref.flags & eServiceReference::isMarker;
		bool isPlayable = !(ref.flags & eServiceReference::isDirectory || isMarker);
#define PB_BorderWidth 2
#define PB_Height 6
		int paintProgress = 0; /* if non zero draw a progress this size and shorten event string width with it */
		ePtr<eServiceEvent> evt;

		bool serviceAvail = true;

		if (!marked && isPlayable && service_info && m_is_playable_ignore.valid() && !service_info->isPlayable(*m_cursor, m_is_playable_ignore))
		{
			if (m_color_set[serviceNotAvail])
				painter.setForegroundColor(m_color[serviceNotAvail]);
			else
				painter.setForegroundColor(gRGB(0xbbbbbb));
			serviceAvail = false;
		}

		if (selected && local_style && local_style->m_selection)
			painter.blit(local_style->m_selection, offset, eRect(), gPainter::BT_ALPHATEST);

		int xoffset=0;  // used as offset when painting the folder/marker symbol or the serviceevent progress

		for (int e = 0; e != celElements; ++e)
		{
			if (m_element_font[e])
			{
				int flags=gPainter::RT_VALIGN_CENTER;
				int yoffs = 0;
				int xoffs = xoffset;
				eRect &area = m_element_position[e];
				std::string text = "<n/a>";
				xoffset=0;

				switch (e)
				{
				case celServiceNumber:
				{
					if (m_cursor->flags & eServiceReference::isMarker && !(m_cursor->flags & eServiceReference::isNumberedMarker))
						continue;
					if (area.width() <= 0)
						continue; // no point in going on if we won't paint anything

					char bla[10];
					/* how we can do this better? :) */
					int markers_before=0;
					{
						list::iterator tmp=m_cursor;
						while(tmp != m_list.begin())
						{
							--tmp;
							if (tmp->flags & eServiceReference::isMarker && !(tmp->flags & eServiceReference::isNumberedMarker))
								++markers_before;
						}
					}
					sprintf(bla, "%d", m_numberoffset + m_cursor_number + 1 - markers_before);
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
					if ( isPlayable && service_info && !service_info->getEvent(*m_cursor, evt) )
					{
						std::string name = evt->getEventName();
						if (name.empty())
							continue;
						text = evt->getEventName();
						if (serviceAvail)
						{
							if (!selected && m_color_set[eventForeground])
								painter.setForegroundColor(m_color[eventForeground]);
							else if (selected && m_color_set[eventForegroundSelected])
								painter.setForegroundColor(m_color[eventForegroundSelected]);
							else
								painter.setForegroundColor(gRGB(0xe7b53f));
						}
						if (paintProgress)
					    		area.setWidth(area.width() - paintProgress - 2*PB_BorderWidth - 2 ); /* create space for the progress bar */
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
				para->renderString(text.c_str());

				if (e == celServiceName)
				{
					eRect bbox = para->getBoundBox();
					int new_left = area.left() + bbox.width() + 8 + xoffs;
					m_element_position[celServiceInfo].setLeft(new_left);
					m_element_position[celServiceInfo].setTop(area.top());
					m_element_position[celServiceInfo].setWidth(m_itemsize.width() - new_left);
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
			else if (e == celServiceTypePixmap || e == celFolderPixmap || e == celMarkerPixmap)
			{
				int orbpos = m_cursor->getUnsignedData(4) >> 16;
				ePtr<gPixmap> &pixmap =
					(e == celFolderPixmap) ? m_pixmaps[picFolder] :
					(e == celMarkerPixmap) ? m_pixmaps[picMarker] :
					(m_cursor->flags & eServiceReference::isGroup) ? m_pixmaps[picServiceGroup] :
					(orbpos == 0xFFFF) ? m_pixmaps[picDVB_C] :
					(orbpos == 0xEEEE) ? m_pixmaps[picDVB_T] : m_pixmaps[picDVB_S];
				if (pixmap)
				{
					eSize pixmap_size = pixmap->size();
					int p = celServiceInfo;
					if (e == celFolderPixmap)
						p = celServiceName;
					else if (e == celMarkerPixmap)
						p = celServiceNumber;
					eRect area = m_element_position[p];
					int correction = (area.height() - pixmap_size.height()) / 2;

					if (isPlayable)
					{
						if (e != celServiceTypePixmap)
							continue;
						m_element_position[celServiceInfo] = area;
						m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + 8);
						m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - 8);
					}
					else if (m_cursor->flags & eServiceReference::isDirectory)
					{
						if (e != celFolderPixmap)
							continue;
						xoffset = pixmap_size.width() + 8;
					}
					else if (m_cursor->flags & eServiceReference::isMarker)
					{
						if (e != celMarkerPixmap)
							continue;
					}
					else
						eFatal("unknown service type in listboxservice");

					area.moveBy(offset);
					painter.clip(area);
					painter.blit(pixmap, offset+ePoint(area.left(), correction), area, gPainter::BT_ALPHATEST);
					painter.clippop();
				}
			}
			else if (e == celServiceEventProgressbar)
			{
				eRect area = m_element_position[celServiceEventProgressbar];
				if (area.width() > 0 && isPlayable)
				{
					// we schedule it to paint it as last element.. so we dont need to reset fore/background color
					paintProgress = area.width();
					// nopli xoffset = area.width() + 10;
				}
			}
		}
		if (selected && (!local_style || !local_style->m_selection))
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);
		if (paintProgress && evt)
		{
			// show a event progressbar for this service at the right end the screen
			gRGB ProgressbarBorderColor = 0xdfdfdf;
			time_t now = time(0);
			int evt_done = paintProgress * (now - evt->getBeginTime()) / evt->getDuration();
			int pb_xpos = offset.x() + m_itemsize.width() - paintProgress - 2*PB_BorderWidth;
			int pb_ypos = offset.y() + (m_itemsize.height() - PB_Height - 2*PB_BorderWidth) / 2;

			// the progress data...
			eRect tmp = eRect(pb_xpos + PB_BorderWidth,   pb_ypos + PB_BorderWidth,   evt_done,   PB_Height);
			ePtr<gPixmap> &pixmap = m_pixmaps[picServiceEventProgressbar];
			if (pixmap) {
				painter.clip(tmp);
				painter.blit(pixmap, ePoint(pb_xpos + PB_BorderWidth, pb_ypos + PB_BorderWidth), tmp, gPainter::BT_ALPHATEST);
				painter.clippop();
			}
			else {
				if (!selected && m_color_set[serviceEventProgressbarColor])
					painter.setForegroundColor(m_color[serviceEventProgressbarColor]);
				else if (selected && m_color_set[serviceEventProgressbarColorSelected])
					painter.setForegroundColor(m_color[serviceEventProgressbarColorSelected]);
				painter.fill(tmp);
			}

			// the progressbar border
			if (!selected)  {
				if (m_color_set[serviceEventProgressbarBorderColor])
					ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColor];
				else if (m_color_set[eventborderForeground])
					ProgressbarBorderColor = m_color[eventborderForeground];
			}
			else { /* !selected */
				if (m_color_set[serviceEventProgressbarBorderColorSelected])
					ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColorSelected];
				else if (m_color_set[eventborderForegroundSelected])
					ProgressbarBorderColor = m_color[eventborderForegroundSelected];
			}
			painter.setForegroundColor(ProgressbarBorderColor);

			painter.fill(eRect(pb_xpos, pb_ypos,                              paintProgress + 2 * PB_BorderWidth,  PB_BorderWidth));
			painter.fill(eRect(pb_xpos, pb_ypos + PB_BorderWidth + PB_Height, paintProgress + 2 * PB_BorderWidth,  PB_BorderWidth));
			painter.fill(eRect(pb_xpos, pb_ypos + PB_BorderWidth,             PB_BorderWidth,                      PB_Height));
			painter.fill(eRect(pb_xpos + PB_BorderWidth + paintProgress, pb_ypos + PB_BorderWidth, PB_BorderWidth, PB_Height));
		}
		if (false && paintProgress && evt)  // not in pli
		{
			eRect area = m_element_position[celServiceEventProgressbar];
			if (!selected && m_color_set[serviceEventProgressbarBorderColor])
				painter.setForegroundColor(m_color[serviceEventProgressbarBorderColor]);
			else if (selected && m_color_set[serviceEventProgressbarBorderColorSelected])
				painter.setForegroundColor(m_color[serviceEventProgressbarBorderColorSelected]);

			int border = 1;
			int progressH = 6;
			int progressX = area.left() + offset.x();
			int progressW = area.width() - 2 * border;
			int progressT = offset.y() + (m_itemsize.height() - progressH - 2*border) / 2;

			// paint progressbar frame
			painter.fill(eRect(progressX, progressT, area.width(), border));
			painter.fill(eRect(progressX, progressT + border, border, progressH));
			painter.fill(eRect(progressX, progressT + progressH + border, area.width(), border));
			painter.fill(eRect(progressX + area.width() - border, progressT + border, border, progressH));

			// calculate value
			time_t now = time(0);
			int value = progressW * (now - evt->getBeginTime()) / evt->getDuration();

			eRect tmp = eRect(progressX + border, progressT + border, value, progressH);
			ePtr<gPixmap> &pixmap = m_pixmaps[picServiceEventProgressbar];
			if (pixmap)
			{
				area.moveBy(offset);
				painter.clip(area);
				painter.blit(pixmap, ePoint(progressX + border, progressT + border), tmp, gPainter::BT_ALPHATEST);
				painter.clippop();
			}
			else
			{
				if (!selected && m_color_set[serviceEventProgressbarColor])
					painter.setForegroundColor(m_color[serviceEventProgressbarColor]);
				else if (selected && m_color_set[serviceEventProgressbarColorSelected])
					painter.setForegroundColor(m_color[serviceEventProgressbarColorSelected]);
				painter.fill(tmp);
			}
		}
	}
	painter.clippop();
}

void eListboxServiceContent::setIgnoreService( const eServiceReference &service )
{
	m_is_playable_ignore=service;
	if (m_listbox && m_listbox->isVisible())
		m_listbox->invalidate();
}

void eListboxServiceContent::setItemHeight(int height)
{
	m_itemheight = height;
	if (m_listbox)
		m_listbox->setItemHeight(height);
}
